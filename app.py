import os
import sqlite3
import string
import random
from flask import Flask, request, jsonify, render_template
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import threading

# Import bot-related functions from bot.py
from bot import bot, send_telegram, load_coupons, save_coupons, get_coupon, is_coupon_valid, use_coupon, start_bot

# =================== Cấu hình ===================
app = Flask(__name__)

DB_FILE = "orders.db"

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "")

MB_API_URL = "https://thueapibank.vn/historyapimbbankv2/07bf677194ae4972714f01a3abf58c5f"

# Tạo folder data/keys nếu chưa tồn tại
os.makedirs("data/keys", exist_ok=True)

# =================== DB ===================
def create_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT UNIQUE,
            email TEXT,
            key TEXT,
            verification_code TEXT,
            promo_code TEXT,
            paid INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            discount INTEGER,
            uses_left INTEGER,
            expires_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def insert_order(uid, verification_code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO orders (uid, verification_code) VALUES (?, ?)", (uid, verification_code))
    conn.commit()
    conn.close()

def mark_paid(uid):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE orders SET paid=1 WHERE uid=?", (uid,))
    conn.commit()
    conn.close()

def get_order(uid):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE uid=?", (uid,))
    row = c.fetchone()
    conn.close()
    return row

def set_email_key(uid, email, key, promo_code=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE orders SET email=?, key=?, promo_code=? WHERE uid=?",
              (email, key, promo_code, uid))
    conn.commit()
    conn.close()

def get_promo(code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM promo_codes WHERE code=?", (code.upper(),))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    if row[3] and datetime.now() > datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S"):
        return None
    if row[2] == 0:
        return None
    return {"code": row[0], "discount": row[1], "uses_left": row[2], "expires_at": row[3]}

def decrement_promo(code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE promo_codes SET uses_left=uses_left-1 WHERE code=?", (code.upper(),))
    conn.commit()
    conn.close()

# =================== Utils ===================
def get_key_file_path(period_code):
    """Get correct key file path"""
    base_period = period_code.replace("_v2", "")
    file_path = os.path.join("data", "keys", f"key{base_period}.txt")
    return file_path

def get_solved_file_path():
    """Get correct solved file path"""
    file_path = os.path.join("data", "keys", "key_solved.txt")
    return file_path

def generate_uid(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_verification_code(length=5):
    # Loại bỏ O (nhầm với 0), I (nhầm với 1), l (nhầm với 1)
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # Không có O, I; không có 0, 1
    return ''.join(random.choices(chars, k=length))

def count_keys(period_code):
    """Count remaining keys for a given period code"""
    file_path = get_key_file_path(period_code)
    
    if not os.path.exists(file_path):
        return 0
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        return len(lines)
    except Exception as e:
        print(f"[KEY ERROR] Failed to count keys in {file_path}: {e}")
        return 0

def get_key_from_file(period_code):
    # Handle v1 and v2 variants
    file_path = get_key_file_path(period_code)
    
    print(f"[KEY DEBUG] Checking file: {file_path}")
    if not os.path.exists(file_path):
        print(f"[KEY ERROR] File not found: {file_path}")
        return None
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        print(f"[KEY DEBUG] Lines in file: {len(lines)}")
        if not lines:
            print("[KEY ERROR] No lines in file")
            return None
        
        key = lines[0].strip()
        print(f"[KEY DEBUG] Key to send: {key}")
        return key
    except Exception as e:
        print(f"[KEY ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
        return None

def delete_key_from_file(period_code):
    """Xóa key đầu tiên từ file và lưu vào key_solved.txt"""
    file_path = get_key_file_path(period_code)
    solved_file = get_solved_file_path()
    
    try:
        print(f"[DELETE_KEY] Path: {file_path}, exists: {os.path.exists(file_path)}")
        
        if not os.path.exists(file_path):
            print(f"[DELETE_KEY] ❌ File not found: {file_path}")
            return False
            
        # Đọc file
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if not lines:
            print(f"[DELETE_KEY] ❌ File empty: {file_path}")
            return False
        
        key = lines[0].strip()
        print(f"[DELETE_KEY] Found key: {key}")
        
        # Tạo thư mục nếu chưa tồn tại
        solved_dir = os.path.dirname(solved_file)
        os.makedirs(solved_dir, exist_ok=True)
        
        # Lưu key vào key_solved.txt
        with open(solved_file, "a", encoding="utf-8") as f:
            f.write(key + "\n")
            f.flush()  # Đảm bảo ghi xong
        print(f"[DELETE_KEY] ✅ Added to {solved_file}")
        
        # Xóa dòng đầu từ file gốc - WRITE NGAY (không close rồi mới write)
        remaining_lines = lines[1:]
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(remaining_lines)
            f.flush()  # Đảm bảo ghi xong trước khi close
        print(f"[DELETE_KEY] ✅ Removed from {file_path}, lines left: {len(remaining_lines)}")
        
        return True
    except Exception as e:
        print(f"[DELETE_KEY] ❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_key(period):
    period_map_reverse = {"1 day": "1d", "7 day": "7d", "30 day": "30d", "90 day": "90d"}
    period_code = period_map_reverse.get(period, "30d")
    return get_key_from_file(period_code)

def send_key(email, key, uid, period="30 day"):
    """
    Gửi email qua SendGrid API và trả về (ok: bool, err_msg: str)
    """
    try:
        print(f"[EMAIL START] Gửi email cho: {email}, key: {key}, uid: {uid}, period: {period}")
        
        # tìm template an toàn theo path file này
        base_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(base_dir, "templates", "gmail.html")

        if not os.path.exists(template_path):
            err = f"Template not found: {template_path}"
            print(f"[EMAIL ERROR ❌] {err}")
            return False, err

        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # phòng trường hợp key là None
        key_for_email = key if key is not None else "N/A"
        
        # Map period để hiển thị
        period_display_map = {
            "1 day": "1 Ngày",
            "7 day": "1 Tuần", 
            "30 day": "1 Tháng",
            "90 day": "1 Mùa"
        }
        period_display = period_display_map.get(period, period)

        # format và build message
        try:
            html_content = html_content.format(
                uid=uid, 
                key=key_for_email,
                period=period_display,
                link="https://tinyurl.com/2a999ad7"
            ).replace("\r", "")
        except Exception as e:
            print(f"[EMAIL ERROR ❌] Template format error: {e}")
            return False, f"Template format error: {e}"

        # Tạo message SendGrid
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=email,
            subject="🔑 Key & Mã đơn hàng của bạn đã sẵn sàng!",
            html_content=html_content
        )
        
        print(f"[EMAIL DEBUG] Message created successfully")
        print(f"[EMAIL DEBUG] FROM: {FROM_EMAIL}")
        print(f"[EMAIL DEBUG] TO: {email}")
        print(f"[EMAIL DEBUG] PERIOD: {period_display}")
        print(f"[EMAIL DEBUG] SUBJECT: 🔑 Key & Mã đơn hàng của bạn đã sẵn sàng!")
        print(f"[EMAIL DEBUG] SendGrid API Key length: {len(SENDGRID_API_KEY) if SENDGRID_API_KEY else 0}")

        # Gửi qua SendGrid
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        print(f"[EMAIL DEBUG] SendGridAPIClient initialized")
        
        response = sg.send(message)
        
        print(f"[EMAIL DEBUG] Response status code: {response.status_code}")
        print(f"[EMAIL DEBUG] Response body: {response.body}")

        if response.status_code == 202:
            print(f"[EMAIL SENT ✅] To: {email} (UID: {uid}, Key: {key}, Period: {period_display})")
            return True, ""
        else:
            err = f"SendGrid error: {response.status_code} - {response.body}"
            print(f"[EMAIL ERROR ❌] {err}")
            return False, err

    except Exception as e:
        # in lỗi chi tiết để debug
        print(f"[EMAIL ERROR ❌] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Lỗi gửi email: {e}"

# =================== Flask Routes ===================
@app.route("/")
def index():
    uid = generate_uid()
    code = generate_verification_code()
    insert_order(uid, code)
    durations = [
        {"category": "v1", "label": "1 Ngày", "value": "1d", "amount": 25000, "key_count": count_keys("1d")},
        {"category": "v1", "label": "1 Tuần", "value": "7d", "amount": 70000, "key_count": count_keys("7d")},
        {"category": "v1", "label": "1 Tháng", "value": "30d", "amount": 250000, "key_count": count_keys("30d")},
        {"category": "v1", "label": "1 Mùa", "value": "90d", "amount": 600000, "key_count": count_keys("90d")},
    ]
    return render_template("index.html", uid=uid, code=code, durations=durations)

@app.route("/check_coupon", methods=["POST"])
def check_coupon():
    """Check if coupon is valid and return its details"""
    data = request.json
    coupon_code = data.get("coupon_code", "").upper()
    period = data.get("period", "30d")
    
    if not coupon_code:
        return jsonify({"status": "error", "message": "Mã giảm giá không được để trống"}), 400
    
    is_valid, err_msg = is_coupon_valid(coupon_code, period)
    
    if is_valid:
        coupon = get_coupon(coupon_code)
        return jsonify({
            "status": "ok",
            "coupon": {
                "code": coupon_code,
                "discount": coupon.get("discount", 0),
                "uses_left": coupon.get("uses_left", 0),
                "expires_at": coupon.get("expires_at", "Không giới hạn"),
                "types": coupon.get("types", [])
            }
        })
    else:
        return jsonify({
            "status": "error",
            "message": err_msg or "Mã giảm giá không hợp lệ"
        }), 400

@app.route("/check_mb_payment", methods=["POST"])
def check_mb_payment():
    data = request.json
    uid = data.get("uid")
    email = data.get("email")
    period_code = data.get("period", "30d")
    amount = int(data.get("amount", 10000))
    promo_code = data.get("promo_code", "").upper()

    if not uid or not email:
        return jsonify({"status": "error", "message": "Thiếu thông tin!"}), 400

    period_map = {"1d": "1 day", "7d": "7 day", "30d": "30 day", "90d": "90 day"}
    period = period_map.get(period_code, "30 day")

    order = get_order(uid)
    if not order:
        return jsonify({"status": "error", "message": "Đơn hàng không tồn tại"}), 404
    if order[6] == 1:
        return jsonify({"status": "ok", "message": "Đã thanh toán trước đó"}), 200

    code_order = order[4]

    # --- FIXED API CALL ---
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json, text/plain, */*",
            "Connection": "keep-alive"
        })
        resp = session.get(MB_API_URL, timeout=15)
        resp.raise_for_status()
        transactions = resp.json().get("transactions", [])
    except Exception as e:
        return jsonify({"status": "error", "message": f"Lỗi đọc API MB: {e}"}), 500
    # --- END FIXED API CALL ---

    now = datetime.now()
    found_tx = None
    code_upper = code_order.upper()
    
    for tx in transactions:
        # Chỉ kiểm tra giao dịch incoming (nhanh nhất)
        if tx.get("type") != "IN":
            continue

        # Kiểm tra amount (nhanh, không cần parse)
        try:
            # Amount có thể là string với dấu phân cách: "1,000" hoặc "1.000"
            amount_str = tx.get("amount", "0").replace(",", "").replace(".", "")
            credit = int(amount_str)
        except:
            continue
        
        if credit != amount:
            continue
            
        # Kiểm tra code trong description (nhanh)
        desc = tx.get("description", "").upper()
        if code_upper not in desc:
            continue

        # Parse time chỉ khi cần thiết (mất nhiều thời gian)
        try:
            tx_time = datetime.strptime(tx["transactionDate"], "%d/%m/%Y %H:%M:%S")
        except:
            continue

        # Kiểm tra time (bỏ giao dịch cũ hơn 24h)
        time_diff = now - tx_time
        if time_diff >= timedelta(hours=24):
            continue
        
        found_tx = tx
        break

    if not found_tx:
        return jsonify({
            "status": "error",
            "message": f"⏳ Giao dịch với mã '{code_order}' chưa tìm thấy. Hãy đợi trong khoảng 20 - 30s rồi ấn lại vào nút 'Nhận Key' ✅"
        }), 400

    # Chuẩn bị base_period cho việc kiểm tra coupon
    base_period = period_code.replace("_v2", "")
    
    discount_percent = 0
    coupon_used_flag = False
    is_new_coupon_system = False  # Đánh dấu coupon là từ system cũ hay mới
    if promo_code:
        # First try new coupon system
        # Extract base period for coupon validation (remove _v2 suffix)
        is_valid, err_msg = is_coupon_valid(promo_code, base_period)
        if is_valid:
            coupon = get_coupon(promo_code)
            discount_percent = coupon["discount"]
            coupon_used_flag = True  # Đánh dấu để dùng coupon sau khi email gửi thành công
            is_new_coupon_system = True  # Đánh dấu là new system
        else:
            # If coupon system fails, try old promo system
            promo = get_promo(promo_code)
            if promo:
                discount_percent = promo["discount"]
                coupon_used_flag = True  # Đánh dấu để dùng promo sau khi email gửi thành công
                is_new_coupon_system = False  # Đánh dấu là old system
            else:
                return jsonify({
                    "status": "error",
                    "message": "Mã giảm giá không hợp lệ hoặc hết hạn"
                }), 400

    final_amount = round(amount * (100 - discount_percent) / 100)

    key = generate_key(period)
    if not key:
        return jsonify({
            "status": "error",
            "message": "Không tạo được key từ server!"
        }), 500

    # Gửi email TRƯỚC, chỉ lưu + mark paid nếu email gửi thành công
    ok, err = send_key(email, key, uid, period)
    if not ok:
        # không lưu, không mark paid, trả lỗi rõ cho client
        print(f"[FLOW] Email gửi thất bại, dừng xử lý. Err: {err}")
        return jsonify({"status": "error", "message": f"Không gửi được email: {err}"}), 500

    # nếu tới đây thì email đã gửi thành công -> lưu key, mark paid
    set_email_key(uid, email, key, promo_code)
    mark_paid(uid)
    
    # Xóa key từ file và lưu vào key_solved.txt sau khi email gửi thành công
    period_code_map_reverse = {"1 day": "1d", "7 day": "7d", "30 day": "30d", "90 day": "90d"}
    period_code = period_code_map_reverse.get(period, "30d")
    print(f"[FLOW] Deleting key for period: {period_code}")
    delete_key_from_file(period_code)
    
    # Cập nhật số lượt dùng coupon sau khi email gửi thành công
    if coupon_used_flag:
        if is_new_coupon_system:
            # Đây là coupon system mới
            use_coupon(promo_code)
        else:
            # Đây là old promo system từ database
            decrement_promo(promo_code)

    tg_msg = (
        f"🎉 <b>Đơn hàng mới!</b>\n"
        f"UID: {uid}\nEmail: {email}\nKey: {key}\n"
        f"Mã giảm giá: {promo_code or 'Không'}\nGiảm: {discount_percent}%\n"
        f"Số tiền: {final_amount}đ\n"
        f"Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )
    send_telegram(tg_msg)

    return jsonify({
        "status": "ok",
        "message": f"✅ Đã gửi key {key} ({period}) về {email}.",
        "data": {
            "key": key,
            "period": period,
            "original_amount": amount,
            "discount_percent": discount_percent,
            "final_amount": final_amount,
            "promo_code": promo_code
        }
    })

# =================== Main ===================
if __name__ == "__main__":
    create_db()
    
    # Start bot polling in a separate thread
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get('PORT', 5550))
    app.run(host="0.0.0.0", port=port)
