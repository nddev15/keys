import os
import json
import requests
from datetime import datetime
from telebot import TeleBot, types
from telebot.util import extract_arguments

# =================== Bot Configuration ===================
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = "7454505306"
COUPON_FILE = os.path.join("data", "coupon", "coupons.json")

# Initialize bot
bot = TeleBot(TG_BOT_TOKEN)
user_states = {}  # Store user states for multi-step commands

# =================== Utils ===================
def is_admin(chat_id):
    """Check if user is admin"""
    return str(chat_id) == str(TG_CHAT_ID)

def send_telegram(message):
    """Send message to telegram admin chat"""
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": "HTML"}
        r = requests.post(url, data=payload)
        return r.status_code == 200
    except Exception as e:
        print(f"[TG ERROR] {e}")
        return False

# =================== Coupon Functions ===================
def load_coupons():
    """Load all coupons from JSON file"""
    if not os.path.exists(COUPON_FILE):
        return {}
    try:
        with open(COUPON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[COUPON ERROR] Failed to load coupons: {e}")
        return {}

def save_coupons(coupons):
    """Save coupons to JSON file"""
    try:
        os.makedirs(os.path.dirname(COUPON_FILE), exist_ok=True)
        with open(COUPON_FILE, "w", encoding="utf-8") as f:
            json.dump(coupons, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[COUPON ERROR] Failed to save coupons: {e}")
        return False

def get_coupon(code):
    """Get coupon by code"""
    coupons = load_coupons()
    return coupons.get(code.upper())

def is_coupon_valid(code, period_code):
    """Check if coupon is valid and can be used for this period"""
    coupon = get_coupon(code)
    if not coupon:
        return False, "Mã giảm giá không tồn tại"
    
    # Check expiration
    if coupon.get("expires_at"):
        expires = datetime.strptime(coupon["expires_at"], "%Y-%m-%d")
        if datetime.now() > expires:
            return False, "Mã giảm giá đã hết hạn"
    
    # Check uses left
    if coupon.get("uses_left", 0) <= 0:
        return False, "Mã giảm giá đã hết lượt sử dụng"
    
    # Check if applicable for this type
    types = coupon.get("types", [])
    if types and period_code not in types:
        return False, f"Mã này không áp dụng cho loại {period_code}"
    
    return True, ""

def use_coupon(code):
    """Decrement uses_left and save, move to used if exhausted"""
    coupons = load_coupons()
    code_upper = code.upper()
    
    if code_upper in coupons:
        coupons[code_upper]["uses_left"] = coupons[code_upper].get("uses_left", 1) - 1
        
        # Check if coupon is exhausted
        uses_left = coupons[code_upper]["uses_left"]
        expires_at = coupons[code_upper].get("expires_at")
        
        if uses_left <= 0 or (expires_at and datetime.now() > datetime.strptime(expires_at, "%Y-%m-%d")):
            # Move to used.json
            move_coupon_to_used(code_upper, coupons[code_upper])
            # Remove from active coupons
            del coupons[code_upper]
        
        save_coupons(coupons)
        return True
    return False

def move_coupon_to_used(code, coupon_data):
    """Move expired/exhausted coupon to used.json"""
    used_file = os.path.join("data", "coupon", "used.json")
    
    try:
        os.makedirs(os.path.dirname(used_file), exist_ok=True)
        
        # Load existing used coupons
        if os.path.exists(used_file):
            try:
                with open(used_file, "r", encoding="utf-8") as f:
                    used_coupons = json.load(f)
            except:
                used_coupons = {}
        else:
            used_coupons = {}
        
        # Add coupon to used
        if not isinstance(used_coupons, dict):
            used_coupons = {}
        
        coupon_data["moved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        used_coupons[code] = coupon_data
        
        # Save used coupons
        with open(used_file, "w", encoding="utf-8") as f:
            json.dump(used_coupons, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"[MOVE COUPON ERROR] Failed to move coupon to used: {e}")
        return False

# =================== Shortened URL Functions ===================
def save_shortened_url(service, original_url, shortened_url):
    """Save shortened URL to the corresponding JSON file"""
    if service == "tinyurl":
        file_path = os.path.join("data", "shortenurl", "tinyurl.json")
    elif service == "isgd":
        file_path = os.path.join("data", "shortenurl", "isgd.json")
    else:
        return False
    
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Load existing data
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except:
                data = {}
        else:
            data = {}
        
        # Add new shortened URL entry
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(data, dict):
            # Store as dict with timestamp
            entry_key = f"{len(data) + 1}"
            data[entry_key] = {
                "original_url": original_url,
                "shortened_url": shortened_url,
                "created_at": timestamp
            }
        else:
            data = {}
            data["1"] = {
                "original_url": original_url,
                "shortened_url": shortened_url,
                "created_at": timestamp
            }
        
        # Save data
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"[SAVE URL ERROR] Failed to save shortened URL: {e}")
        return False

def load_shortened_urls(service):
    """Load all shortened URLs from the corresponding JSON file"""
    if service == "tinyurl":
        file_path = os.path.join("data", "shortenurl", "tinyurl.json")
    elif service == "isgd":
        file_path = os.path.join("data", "shortenurl", "isgd.json")
    else:
        return {}
    
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        return {}
    except Exception as e:
        print(f"[LOAD URL ERROR] Failed to load shortened URLs: {e}")
        return {}

def check_alias_exists(alias):
    """Check if alias already exists in tinyurl.json"""
    try:
        file_path = os.path.join("data", "shortenurl", "tinyurl.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for entry in data.values():
                        if isinstance(entry, dict):
                            shortened_url = entry.get("shortened_url", "")
                            # Check if alias is in the shortened URL
                            if f"/{alias}" in shortened_url or shortened_url.endswith(alias):
                                return True
        return False
    except Exception as e:
        print(f"[CHECK ALIAS ERROR] {e}")
        return False

# =================== Key Functions ===================
def get_all_unsold_keys():
    """Get all unsold keys from all key files"""
    keys_dict = {}
    key_files = {
        "key1d.txt": "1 Ngày",
        "key7d.txt": "1 Tuần",
        "key30d.txt": "1 Tháng",
        "key90d.txt": "1 Mùa"
    }
    
    for filename, label in key_files.items():
        file_path = os.path.join("data", "keys", filename)
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                if lines:
                    keys_dict[label] = lines
            except Exception as e:
                print(f"[KEY ERROR] Failed to read {filename}: {e}")
    
    return keys_dict

def get_keys_by_type(period_label):
    """Get keys for a specific type"""
    type_map = {
        "1 Ngày": "key1d.txt",
        "1 Tuần": "key7d.txt",
        "1 Tháng": "key30d.txt",
        "1 Mùa": "key90d.txt"
    }
    
    filename = type_map.get(period_label)
    if not filename:
        return []
    
    file_path = os.path.join("data", "keys", filename)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            return lines
        except Exception as e:
            print(f"[KEY ERROR] Failed to read {filename}: {e}")
    
    return []

def format_keys_by_period(period_label, page=0, max_per_page=20):
    """Format keys for specific period with pagination"""
    keys = get_keys_by_type(period_label)
    total_keys = len(keys)
    total_pages = (total_keys + max_per_page - 1) // max_per_page
    
    if total_keys == 0:
        return "❌ Không có key nào cho loại này!", 0
    
    if page >= total_pages:
        page = total_pages - 1
    
    start = page * max_per_page
    end = start + max_per_page
    page_keys = keys[start:end]
    
    message = f"🔑 <b>Key {period_label}</b>\n\n"
    for i, key in enumerate(page_keys, 1):
        message += f"{i}. {key}\n"
    
    message += f"\n📄 Trang {page + 1}/{total_pages}"
    
    return message, total_pages

def format_keys_message(keys_dict, page=0, max_per_page=20):
    """Format keys for display with pagination"""
    all_keys = []
    for period, keys in keys_dict.items():
        for key in keys:
            all_keys.append(f"{period} - {key}")
    
    total_keys = len(all_keys)
    total_pages = (total_keys + max_per_page - 1) // max_per_page
    
    if total_keys == 0:
        return "❌ Không có key nào chưa bán!", 0
    
    if page >= total_pages:
        page = total_pages - 1
    
    start = page * max_per_page
    end = start + max_per_page
    page_keys = all_keys[start:end]
    
    message = f"📋 <b>Danh sách key chưa bán</b>\n\n"
    for i, key_info in enumerate(page_keys, 1):
        message += f"{i}. {key_info}\n"
    
    message += f"\n📄 Trang {page + 1}/{total_pages}"
    
    return message, total_pages

def save_new_coupon(message, chat_id):
    """Save the new coupon"""
    if chat_id not in user_states:
        return
    
    state = user_states[chat_id]
    code = state.get("code")
    discount = state.get("discount")
    uses = state.get("uses")
    expires = state.get("expires")
    types = state.get("types", [])
    
    if not all([code, discount, uses, types]):
        bot.send_message(chat_id, "❌ Dữ liệu không đầy đủ!")
        return
    
    coupons = load_coupons()
    coupons[code] = {
        "discount": discount,
        "uses": uses,
        "uses_left": uses,
        "expires_at": expires,
        "types": types
    }
    
    if save_coupons(coupons):
        msg = f"✅ Đã thêm mã giảm giá:\n\n"
        msg += f"<b>{code}</b>\n"
        msg += f"• Giảm: {discount}%\n"
        msg += f"• Lượt: {uses}\n"
        msg += f"• Hết hạn: {expires or 'Không giới hạn'}\n"
        msg += f"• Áp dụng: {', '.join(types)}"
        
        bot.send_message(chat_id, msg, parse_mode="HTML")
        
        del user_states[chat_id]
        
        # Notify admin
        tg_msg = f"➕ <b>Thêm mã giảm giá</b>\nMã: {code}\nGiảm: {discount}%"
        send_telegram(tg_msg)
    else:
        bot.send_message(chat_id, "❌ Lỗi lưu mã giảm giá!")

# =================== Telegram Bot Handlers ===================

@bot.message_handler(commands=['start'])
def start(message):
    """Start command"""
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add("/xemkey", "/themkey", "/xoakey")
    markup.add("/themcoupon", "/xoacoupon", "/couponhienco")
    markup.add("/rutgonlink", "/showshortenurl")
    bot.send_message(message.chat.id, 
                    "👋 Chào mừng!\n\n"
                    "<b>📋 Key Management:</b>\n"
                    "/xemkey - Xem key chưa bán\n"
                    "/themkey - Thêm key mới\n"
                    "/xoakey - Xóa key\n\n"
                    "<b>🎟️ Coupon Management:</b>\n"
                    "/themcoupon - Thêm mã giảm giá\n"
                    "/xoacoupon - Xóa mã giảm giá\n"
                    "/couponhienco - Xem mã giảm giá hiện có\n\n"
                    "<b>🔗 Tools:</b>\n"
                    "/rutgonlink - Rút gọn link (TinyURL/is.gd)\n"
                    "/showshortenurl - Xem tất cả link rút gọn\n",
                    reply_markup=markup, parse_mode="HTML")

# =================== KEY MANAGEMENT ===================

@bot.message_handler(commands=['xemkey'])
def xem_key(message):
    """View unsold keys"""
    chat_id = message.chat.id
    
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("1 Ngày (1d)", callback_data="view_keys_1 Ngày"),
        types.InlineKeyboardButton("1 Tuần (7d)", callback_data="view_keys_1 Tuần"),
        types.InlineKeyboardButton("1 Tháng (30d)", callback_data="view_keys_1 Tháng"),
        types.InlineKeyboardButton("1 Mùa (90d)", callback_data="view_keys_1 Mùa")
    )
    
    bot.send_message(chat_id, "🔑 <b>Chọn loại key:</b>", reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_keys_"))
def view_keys_callback(call):
    """Show keys for selected period"""
    try:
        period_label = call.data.replace("view_keys_", "")
        
        chat_id = call.message.chat.id
        msg_text, total_pages = format_keys_by_period(period_label, page=0)
        
        markup = types.InlineKeyboardMarkup()
        if total_pages > 1:
            markup.add(
                types.InlineKeyboardButton("➡️ Trang kế tiếp", callback_data=f"key_next_{period_label}_1")
            )
        
        markup.add(types.InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_key_types"))
        
        bot.edit_message_text(msg_text, chat_id, call.message.message_id, 
                             reply_markup=markup, parse_mode="HTML")
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"[CALLBACK ERROR] {e}")
        bot.answer_callback_query(call.id, "❌ Lỗi!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("key_next_"))
def key_next_callback(call):
    """Next page for keys"""
    try:
        # Format: key_next_1 Ngày_1
        parts = call.data.replace("key_next_", "").rsplit("_", 1)
        period_label = parts[0]
        page = int(parts[-1])
        
        chat_id = call.message.chat.id
        msg_text, total_pages = format_keys_by_period(period_label, page=page)
        
        markup = types.InlineKeyboardMarkup()
        nav_row = []
        if page > 0:
            nav_row.append(types.InlineKeyboardButton("⬅️ Trang trước", callback_data=f"key_prev_{period_label}_{page-1}"))
        if page < total_pages - 1:
            nav_row.append(types.InlineKeyboardButton("➡️ Trang kế tiếp", callback_data=f"key_next_{period_label}_{page+1}"))
        
        if nav_row:
            markup.row(*nav_row)
        
        markup.add(types.InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_key_types"))
        
        bot.edit_message_text(msg_text, chat_id, call.message.message_id, 
                             reply_markup=markup, parse_mode="HTML")
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"[CALLBACK ERROR] {e}")
        bot.answer_callback_query(call.id, "❌ Lỗi!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("key_prev_"))
def key_prev_callback(call):
    """Previous page for keys"""
    try:
        # Format: key_prev_1 Ngày_1
        parts = call.data.replace("key_prev_", "").rsplit("_", 1)
        period_label = parts[0]
        page = int(parts[-1])
        
        chat_id = call.message.chat.id
        msg_text, total_pages = format_keys_by_period(period_label, page=page)
        
        markup = types.InlineKeyboardMarkup()
        nav_row = []
        if page > 0:
            nav_row.append(types.InlineKeyboardButton("⬅️ Trang trước", callback_data=f"key_prev_{period_label}_{page-1}"))
        if page < total_pages - 1:
            nav_row.append(types.InlineKeyboardButton("➡️ Trang kế tiếp", callback_data=f"key_next_{period_label}_{page+1}"))
        
        if nav_row:
            markup.row(*nav_row)
        
        markup.add(types.InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_key_types"))
        
        bot.edit_message_text(msg_text, chat_id, call.message.message_id, 
                             reply_markup=markup, parse_mode="HTML")
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"[CALLBACK ERROR] {e}")
        bot.answer_callback_query(call.id, "❌ Lỗi!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_key_types")
def back_to_key_types(call):
    """Back to key type selection"""
    try:
        chat_id = call.message.chat.id
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("1 Ngày (1d)", callback_data="view_keys_1 Ngày"),
            types.InlineKeyboardButton("1 Tuần (7d)", callback_data="view_keys_1 Tuần"),
            types.InlineKeyboardButton("1 Tháng (30d)", callback_data="view_keys_1 Tháng"),
            types.InlineKeyboardButton("1 Mùa (90d)", callback_data="view_keys_1 Mùa")
        )
        
        bot.edit_message_text("🔑 <b>Chọn loại key:</b>", chat_id, call.message.message_id, 
                             reply_markup=markup, parse_mode="HTML")
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"[CALLBACK ERROR] {e}")
        bot.answer_callback_query(call.id, "❌ Lỗi!", show_alert=True)

@bot.message_handler(commands=['themkey'])
def them_key(message):
    """Start adding new key"""
    chat_id = message.chat.id
    
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    user_states[chat_id] = {"step": "waiting_period"}
    
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add("1 Ngày (1d)", "1 Tuần (7d)", "1 Tháng (30d)", "1 Mùa (90d)")
    
    bot.send_message(chat_id, "🔐 Chọn loại key:", reply_markup=markup)

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("step") == "waiting_period")
def process_period(message):
    """Process selected period"""
    chat_id = message.chat.id
    text = message.text
    
    period_map = {
        "1 Ngày (1d)": "1d",
        "1 Tuần (7d)": "7d",
        "1 Tháng (30d)": "30d",
        "1 Mùa (90d)": "90d"
    }
    
    if text not in period_map:
        bot.send_message(chat_id, "❌ Lựa chọn không hợp lệ. Vui lòng chọn lại!")
        return
    
    user_states[chat_id]["period"] = period_map[text]
    user_states[chat_id]["step"] = "waiting_keys"
    
    markup = types.ReplyKeyboardRemove()
    bot.send_message(chat_id, 
                    f"📝 Gửi các key (mỗi dòng một key):\n\nLoại: {text}",
                    reply_markup=markup)

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("step") == "waiting_keys")
def process_keys(message):
    """Process and save keys"""
    chat_id = message.chat.id
    period = user_states[chat_id]["period"]
    keys_text = message.text.strip()
    
    if not keys_text:
        bot.send_message(chat_id, "❌ Bạn phải nhập ít nhất một key!")
        return
    
    keys = [k.strip() for k in keys_text.split("\n") if k.strip()]
    
    file_path = os.path.join("data", "keys", f"key{period}.txt")
    
    try:
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "a", encoding="utf-8") as f:
            for key in keys:
                f.write(key + "\n")
        
        del user_states[chat_id]
        
        success_msg = f"✅ Đã thêm {len(keys)} key\n\n"
        for key in keys:
            success_msg += f"• {key}\n"
        
        bot.send_message(chat_id, success_msg)
        
        # Notify admin
        tg_msg = f"➕ <b>Thêm key mới</b>\nLoại: {period}\nSố lượng: {len(keys)}"
        send_telegram(tg_msg)
        
    except Exception as e:
        print(f"[KEY ERROR] {e}")
        bot.send_message(chat_id, f"❌ Lỗi lưu key: {e}")
        del user_states[chat_id]

@bot.message_handler(commands=['xoakey'])
def xoa_key(message):
    """Start deleting key"""
    chat_id = message.chat.id
    
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    user_states[chat_id] = {"step": "waiting_delete_period"}
    
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add("1 Ngày (1d)", "1 Tuần (7d)", "1 Tháng (30d)", "1 Mùa (90d)")
    
    bot.send_message(chat_id, "🔐 Chọn loại key để xóa:", reply_markup=markup)

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("step") == "waiting_delete_period")
def process_delete_period(message):
    """Process period for deletion"""
    chat_id = message.chat.id
    text = message.text
    
    period_map = {
        "1 Ngày (1d)": "1d",
        "1 Tuần (7d)": "7d",
        "1 Tháng (30d)": "30d",
        "1 Mùa (90d)": "90d"
    }
    
    if text not in period_map:
        bot.send_message(chat_id, "❌ Lựa chọn không hợp lệ. Vui lòng chọn lại!")
        return
    
    period = period_map[text]
    file_path = os.path.join("data", "keys", f"key{period}.txt")
    
    if not os.path.exists(file_path):
        del user_states[chat_id]
        bot.send_message(chat_id, "❌ File key không tồn tại!")
        return
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        if not lines:
            del user_states[chat_id]
            bot.send_message(chat_id, "❌ Không có key để xóa!")
            return
        
        user_states[chat_id]["period"] = period
        user_states[chat_id]["keys"] = lines
        user_states[chat_id]["step"] = "waiting_delete_key"
        
        markup = types.ReplyKeyboardRemove()
        keys_list = "\n".join([f"{i+1}. {k}" for i, k in enumerate(lines[:10])])
        msg = f"📋 Chọn key để xóa (danh sách 10 key đầu):\n\n{keys_list}"
        
        if len(lines) > 10:
            msg += f"\n\n... và {len(lines) - 10} key khác"
        
        msg += "\n\nGửi key bạn muốn xóa:"
        
        bot.send_message(chat_id, msg, reply_markup=markup)
        
    except Exception as e:
        print(f"[KEY ERROR] {e}")
        bot.send_message(chat_id, f"❌ Lỗi: {e}")
        del user_states[chat_id]

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("step") == "waiting_delete_key")
def process_delete_key(message):
    """Delete the specified key"""
    chat_id = message.chat.id
    key_to_delete = message.text.strip()
    period = user_states[chat_id]["period"]
    keys = user_states[chat_id]["keys"]
    
    if key_to_delete not in keys:
        bot.send_message(chat_id, "❌ Key không tìm thấy!")
        return
    
    file_path = os.path.join("data", "keys", f"key{period}.txt")
    
    try:
        keys.remove(key_to_delete)
        
        with open(file_path, "w", encoding="utf-8") as f:
            for key in keys:
                f.write(key + "\n")
        
        del user_states[chat_id]
        
        bot.send_message(chat_id, f"✅ Đã xóa key:\n{key_to_delete}")
        
        # Notify admin
        tg_msg = f"➖ <b>Xóa key</b>\nLoại: {period}\nKey: {key_to_delete}"
        send_telegram(tg_msg)
        
    except Exception as e:
        print(f"[KEY ERROR] {e}")
        bot.send_message(chat_id, f"❌ Lỗi xóa key: {e}")
        del user_states[chat_id]

# =================== COUPON MANAGEMENT ===================

@bot.message_handler(commands=['couponhienco'])
def coupon_hien_co(message):
    """View all available coupons"""
    chat_id = message.chat.id
    
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    coupons = load_coupons()
    
    if not coupons:
        bot.send_message(chat_id, "❌ Không có mã giảm giá nào!")
        return
    
    msg = "🎟️ <b>Danh sách mã giảm giá</b>\n\n"
    for code, data in coupons.items():
        discount = data.get("discount", 0)
        uses_left = data.get("uses_left", 0)
        expires = data.get("expires_at", "Không giới hạn")
        types = ", ".join(data.get("types", ["Tất cả"]))
        
        msg += f"<b>{code}</b>\n"
        msg += f"  • Giảm: {discount}%\n"
        msg += f"  • Lượt còn lại: {uses_left}\n"
        msg += f"  • Hết hạn: {expires}\n"
        msg += f"  • Áp dụng: {types}\n\n"
    
    bot.send_message(chat_id, msg, parse_mode="HTML")

@bot.message_handler(commands=['themcoupon'])
def them_coupon(message):
    """Start adding new coupon"""
    chat_id = message.chat.id
    
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    user_states[chat_id] = {"step": "waiting_coupon_code"}
    
    bot.send_message(chat_id, "🎟️ Nhập mã giảm giá (VD: COUPON001):")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("step") == "waiting_coupon_code")
def process_coupon_code(message):
    """Process coupon code"""
    chat_id = message.chat.id
    code = message.text.strip().upper()
    
    if not code:
        bot.send_message(chat_id, "❌ Mã không được để trống!")
        return
    
    coupons = load_coupons()
    if code in coupons:
        bot.send_message(chat_id, f"❌ Mã {code} đã tồn tại!")
        return
    
    user_states[chat_id]["code"] = code
    user_states[chat_id]["step"] = "waiting_coupon_discount"
    
    bot.send_message(chat_id, f"📊 Nhập % giảm giá (VD: 10):")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("step") == "waiting_coupon_discount")
def process_coupon_discount(message):
    """Process discount percentage"""
    chat_id = message.chat.id
    
    try:
        discount = int(message.text.strip())
        if discount <= 0 or discount > 100:
            bot.send_message(chat_id, "❌ Giảm giá phải từ 1-100%!")
            return
    except ValueError:
        bot.send_message(chat_id, "❌ Nhập số nguyên!")
        return
    
    user_states[chat_id]["discount"] = discount
    user_states[chat_id]["step"] = "waiting_coupon_uses"
    
    bot.send_message(chat_id, "📈 Nhập số lượt sử dụng (VD: 10):")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("step") == "waiting_coupon_uses")
def process_coupon_uses(message):
    """Process number of uses"""
    chat_id = message.chat.id
    
    try:
        uses = int(message.text.strip())
        if uses <= 0:
            bot.send_message(chat_id, "❌ Số lượt phải > 0!")
            return
    except ValueError:
        bot.send_message(chat_id, "❌ Nhập số nguyên!")
        return
    
    user_states[chat_id]["uses"] = uses
    user_states[chat_id]["step"] = "waiting_coupon_expires"
    
    bot.send_message(chat_id, "📅 Nhập ngày hết hạn (YYYY-MM-DD) hoặc 'không' nếu không giới hạn:")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("step") == "waiting_coupon_expires")
def process_coupon_expires(message):
    """Process expiration date"""
    chat_id = message.chat.id
    expires_text = message.text.strip().lower()
    
    if expires_text == "không":
        expires = None
    else:
        try:
            datetime.strptime(expires_text, "%Y-%m-%d")
            expires = expires_text
        except ValueError:
            bot.send_message(chat_id, "❌ Định dạng sai! Dùng YYYY-MM-DD hoặc 'không'")
            return
    
    user_states[chat_id]["expires"] = expires
    user_states[chat_id]["step"] = "waiting_coupon_types"
    
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add("1 Ngày (1d)", "1 Tuần (7d)", "1 Tháng (30d)", "1 Mùa (90d)", "Tất cả")
    
    bot.send_message(chat_id, "🎯 Chọn loại hàng áp dụng (chọn nhiều hoặc 'Tất cả'):", reply_markup=markup)
    
    user_states[chat_id]["selected_types"] = []

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("step") == "waiting_coupon_types")
def process_coupon_types(message):
    """Process applicable types"""
    chat_id = message.chat.id
    text = message.text.strip()
    
    type_map = {
        "1 Ngày (1d)": "1d",
        "1 Tuần (7d)": "7d",
        "1 Tháng (30d)": "30d",
        "1 Mùa (90d)": "90d",
        "Tất cả": "all"
    }
    
    if text not in type_map:
        bot.send_message(chat_id, "❌ Lựa chọn không hợp lệ!")
        return
    
    selected = user_states[chat_id].get("selected_types", [])
    
    if text == "Tất cả":
        user_states[chat_id]["types"] = ["1d", "7d", "30d", "90d"]
        save_new_coupon(message, chat_id)
    else:
        period_code = type_map[text]
        if period_code not in selected:
            selected.append(period_code)
        
        user_states[chat_id]["selected_types"] = selected
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Hoàn thành", callback_data="coupon_done"))
        
        msg = f"Đã chọn: {', '.join(selected)}\n\nChọn thêm hoặc nhấn ✅ Hoàn thành:"
        bot.send_message(chat_id, msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "coupon_done")
def coupon_done_callback(call):
    """Finish coupon type selection"""
    chat_id = call.message.chat.id
    selected_types = user_states.get(chat_id, {}).get("selected_types", [])
    
    if not selected_types:
        bot.answer_callback_query(call.id, "❌ Chọn ít nhất 1 loại!", show_alert=True)
        return
    
    user_states[chat_id]["types"] = selected_types
    bot.edit_message_text("✅ Hoàn thành lựa chọn", chat_id, call.message.message_id)
    save_new_coupon(call.message, chat_id)
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['xoacoupon'])
def xoa_coupon(message):
    """Start deleting coupon"""
    chat_id = message.chat.id
    
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    coupons = load_coupons()
    
    if not coupons:
        bot.send_message(chat_id, "❌ Không có mã giảm giá để xóa!")
        return
    
    user_states[chat_id] = {"step": "waiting_coupon_delete"}
    
    msg = "🎟️ Chọn mã để xóa:\n\n"
    for code in list(coupons.keys())[:10]:
        msg += f"• {code}\n"
    
    if len(coupons) > 10:
        msg += f"\n... và {len(coupons) - 10} mã khác"
    
    msg += "\n\nNhập mã cần xóa:"
    bot.send_message(chat_id, msg)

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("step") == "waiting_coupon_delete")
def process_coupon_delete(message):
    """Delete coupon"""
    chat_id = message.chat.id
    code = message.text.strip().upper()
    
    coupons = load_coupons()
    
    if code not in coupons:
        bot.send_message(chat_id, "❌ Mã giảm giá không tồn tại!")
        return
    
    del coupons[code]
    
    if save_coupons(coupons):
        bot.send_message(chat_id, f"✅ Đã xóa mã: {code}")
        del user_states[chat_id]
        
        # Notify admin
        tg_msg = f"➖ <b>Xóa mã giảm giá</b>\nMã: {code}"
        send_telegram(tg_msg)
    else:
        bot.send_message(chat_id, "❌ Lỗi xóa mã!")

# =================== LINK SHORTENER ===================

@bot.message_handler(commands=['rutgonlink'])
def rut_gon_link(message):
    """Shorten link using tinyurl or is.gd API"""
    chat_id = message.chat.id
    # Ask user to choose service
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("TinyURL", callback_data="choose_service_tinyurl"),
        types.InlineKeyboardButton("is.gd", callback_data="choose_service_isgd")
    )
    bot.send_message(chat_id, "🔗 <b>Chọn dịch vụ rút gọn link:</b>", reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("choose_service_"))
def choose_service(call):
    """Handle service selection"""
    chat_id = call.message.chat.id
    service = call.data.replace("choose_service_", "")
    user_states[chat_id] = {"step": "waiting_link_to_shorten", "service": service}
    
    if service == "tinyurl":
        # Ask if user wants custom alias for tinyurl
        markup = types.ReplyKeyboardMarkup(row_width=2)
        markup.add("Có (có alias)", "Không (không alias)")
        bot.send_message(chat_id, "🔗 Bạn có muốn tùy chọn alias cho TinyURL không?", reply_markup=markup)
        user_states[chat_id]["step"] = "waiting_alias_choice"
    else:
        bot.send_message(chat_id, "🔗 Nhập link cần rút gọn:")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("step") == "waiting_alias_choice")
def process_alias_choice(message):
    """Handle alias choice for TinyURL"""
    chat_id = message.chat.id
    choice = message.text.strip()
    
    if choice == "Có (có alias)":
        user_states[chat_id]["step"] = "waiting_link_to_shorten"
        user_states[chat_id]["use_alias"] = True
        bot.send_message(chat_id, "🔗 Nhập link cần rút gọn:", reply_markup=types.ReplyKeyboardRemove())
    elif choice == "Không (không alias)":
        user_states[chat_id]["step"] = "waiting_link_to_shorten"
        user_states[chat_id]["use_alias"] = False
        bot.send_message(chat_id, "🔗 Nhập link cần rút gọn:", reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(chat_id, "❌ Vui lòng chọn Có hoặc Không!")

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("step") == "waiting_link_to_shorten")
def process_shorten_link(message):
    """Process link shortening"""
    chat_id = message.chat.id
    url = message.text.strip()
    service = user_states.get(chat_id, {}).get("service", "tinyurl")
    use_alias = user_states.get(chat_id, {}).get("use_alias", False)
    
    # Validate URL
    if not (url.startswith('http://') or url.startswith('https://')):
        bot.send_message(chat_id, "❌ Link không hợp lệ! Vui lòng nhập link bắt đầu bằng http:// hoặc https://")
        return
    
    try:
        shortened_url = ""
        alias = None
        
        if service == "tinyurl":
            if use_alias:
                # Ask for alias
                user_states[chat_id]["step"] = "waiting_tinyurl_alias"
                user_states[chat_id]["original_url"] = url
                bot.send_message(chat_id, "✏️ Nhập alias mong muốn (ví dụ: mylink. Bỏ trống để tự động):", reply_markup=types.ReplyKeyboardRemove())
                return
            else:
                # Use tinyurl API without alias
                api_url = f"https://tinyurl.com/api-create.php?url={url}"
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    result = response.text.strip()
                    # Check if response contains error
                    if "error" not in result.lower() and result.startswith("https://"):
                        shortened_url = result
                    else:
                        bot.send_message(chat_id, "❌ Lỗi rút gọn link! Vui lòng thử lại.")
                        if chat_id in user_states:
                            del user_states[chat_id]
                        return
                else:
                    bot.send_message(chat_id, "❌ Lỗi rút gọn link! Vui lòng thử lại.")
                    if chat_id in user_states:
                        del user_states[chat_id]
                    return
        elif service == "isgd":
            # Use is.gd API
            api_url = f"https://is.gd/create.php?format=json&url={url}"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "shorturl" in data:
                    shortened_url = data["shorturl"]
                else:
                    bot.send_message(chat_id, f"❌ Lỗi: {data.get('error', 'Không thể rút gọn link')}")
                    if chat_id in user_states:
                        del user_states[chat_id]
                    return
            else:
                bot.send_message(chat_id, "❌ Lỗi rút gọn link! Vui lòng thử lại.")
                if chat_id in user_states:
                    del user_states[chat_id]
                return
        
        if shortened_url:
            # Save to corresponding JSON file
            save_shortened_url(service, url, shortened_url)
            
            bot.send_message(
                chat_id,
                f"✅ <b>Rút gọn thành công!</b>\n\n"
                f"<b>Dịch vụ:</b> {service.upper()}\n\n"
                f"<b>Link gốc:</b>\n{url}\n\n"
                f"<b>Link rút gọn:</b>\n<code>{shortened_url}</code>\n\n"
                f"Bấm vào link rút gọn để sao chép!",
                parse_mode="HTML"
            )
            if chat_id in user_states:
                del user_states[chat_id]
        else:
            bot.send_message(chat_id, "❌ Không thể tạo link rút gọn! Vui lòng thử lại.")
            if chat_id in user_states:
                del user_states[chat_id]
    except Exception as e:
        print(f"[SHORTEN LINK ERROR] {e}")
        bot.send_message(chat_id, f"❌ Lỗi: {str(e)}")
        if chat_id in user_states:
            del user_states[chat_id]
    finally:
        if chat_id in user_states:
            del user_states[chat_id]

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("step") == "waiting_tinyurl_alias")
def process_tinyurl_alias(message):
    """Process TinyURL alias input"""
    chat_id = message.chat.id
    alias = message.text.strip()
    url = user_states.get(chat_id, {}).get("original_url")
    
    if not url:
        bot.send_message(chat_id, "❌ Lỗi! Không tìm thấy link gốc.", reply_markup=types.ReplyKeyboardRemove())
        if chat_id in user_states:
            del user_states[chat_id]
        return
    
    try:
        shortened_url = ""
        
        if alias:
            # Check if alias already exists
            if check_alias_exists(alias):
                bot.send_message(
                    chat_id,
                    f"❌ Alias '{alias}' đã được sử dụng!\n\nVui lòng nhập alias khác hoặc để trống để tạo link tự động:"
                )
                user_states[chat_id]["step"] = "waiting_tinyurl_alias"
                return
            
            # Try with custom alias
            api_url = f"https://tinyurl.com/api-create.php?url={url}&alias={alias}"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                result = response.text.strip()
                # Check if it's an error or success
                if "error" not in result.lower():
                    shortened_url = result
                else:
                    bot.send_message(
                        chat_id,
                        f"❌ Alias '{alias}' không thể sử dụng (đã tồn tại trên TinyURL)!\n\nVui lòng nhập alias khác hoặc để trống để tạo link tự động:"
                    )
                    user_states[chat_id]["step"] = "waiting_tinyurl_alias"
                    return
            else:
                bot.send_message(chat_id, "❌ Lỗi rút gọn link! Vui lòng thử lại.")
                if chat_id in user_states:
                    del user_states[chat_id]
                return
        else:
            # No alias, create without one
            api_url = f"https://tinyurl.com/api-create.php?url={url}"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                shortened_url = response.text.strip()
            else:
                bot.send_message(chat_id, "❌ Lỗi rút gọn link! Vui lòng thử lại.")
                if chat_id in user_states:
                    del user_states[chat_id]
                return
        
        if shortened_url:
            # Save to corresponding JSON file
            save_shortened_url("tinyurl", url, shortened_url)
            
            alias_info = f"<b>Alias:</b> {alias}\n" if alias else "<b>Alias:</b> Tự động\n"
            bot.send_message(
                chat_id,
                f"✅ <b>Rút gọn thành công!</b>\n\n"
                f"<b>Dịch vụ:</b> TINYURL\n\n"
                f"{alias_info}\n"
                f"<b>Link gốc:</b>\n{url}\n\n"
                f"<b>Link rút gọn:</b>\n<code>{shortened_url}</code>\n\n"
                f"Bấm vào link rút gọn để sao chép!",
                parse_mode="HTML",
                reply_markup=types.ReplyKeyboardRemove()
            )
            if chat_id in user_states:
                del user_states[chat_id]
    except Exception as e:
        print(f"[TINYURL ALIAS ERROR] {e}")
        bot.send_message(chat_id, f"❌ Lỗi: {str(e)}", reply_markup=types.ReplyKeyboardRemove())
        if chat_id in user_states:
            del user_states[chat_id]

@bot.message_handler(commands=['showshortenurl'])
def show_shortened_urls(message):
    """Show all shortened URLs"""
    chat_id = message.chat.id
    
    # Create inline keyboard with service options
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📌 TinyURL", callback_data="show_urls_tinyurl"),
        types.InlineKeyboardButton("📌 is.gd", callback_data="show_urls_isgd")
    )
    
    bot.send_message(chat_id, "🔗 <b>Chọn dịch vụ để xem link rút gọn:</b>", reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("show_urls_"))
def show_urls_callback(call):
    """Display shortened URLs for selected service"""
    chat_id = call.message.chat.id
    service = call.data.replace("show_urls_", "")
    
    # Load data from corresponding file
    urls_data = load_shortened_urls(service)
    
    if not urls_data:
        bot.send_message(chat_id, f"📭 Không có link nào từ dịch vụ {service.upper()}")
        return
    
    # Build message with all URLs
    message = f"🔗 <b>Link rút gọn từ {service.upper()}:</b>\n\n"
    
    for key, entry in urls_data.items():
        if isinstance(entry, dict):
            original = entry.get("original_url", "N/A")
            shortened = entry.get("shortened_url", "N/A")
            created_at = entry.get("created_at", "N/A")
            
            message += f"<b>Gốc:</b> {original}\n"
            message += f"<b>Rút gọn:</b> <code>{shortened}</code>\n"
            message += f"<b>Lúc:</b> {created_at}\n"
            message += "─" * 40 + "\n"
    
    bot.send_message(chat_id, message, parse_mode="HTML")

# =================== Bot Polling ===================

def start_bot():
    """Start bot polling in a separate thread"""
    print("[BOT] Starting Telegram bot polling...")
    bot.infinity_polling()

if __name__ == "__main__":
    start_bot()
