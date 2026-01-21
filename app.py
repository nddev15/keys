import os
import sqlite3
import string
import random
import json
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import threading
from threading import Lock
import base64
import secrets

# Import bot-related functions from bot.py
from bot import bot, send_telegram, load_coupons, save_coupons, get_coupon, is_coupon_valid, use_coupon, start_bot

# =================== GitHub API Helper ===================
class GitHubDataManager:
    """Manage key and solved key data via GitHub API"""
    
    def __init__(self):
        self.token = os.environ.get('GITHUB_TOKEN', '')
        self.owner = os.environ.get('GITHUB_OWNER', '')
        self.repo = os.environ.get('GITHUB_REPO', '')
        self.api_base = 'https://api.github.com'
        self.use_github = bool(self.token and self.owner and self.repo)
        
        if self.use_github:
            print(f"[GITHUB] ✅ GitHub API enabled: {self.owner}/{self.repo}")
        else:
            print("[GITHUB] ⚠️  GitHub API disabled (missing GITHUB_TOKEN, GITHUB_OWNER, or GITHUB_REPO)")
        
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
        }

    def _get_file_sha(self, file_path):
        """Get file SHA for update operations"""
        if not self.use_github:
            return None
        
        try:
            url = f'{self.api_base}/repos/{self.owner}/{self.repo}/contents/{file_path}'
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json().get('sha')
            elif response.status_code == 404:
                return None
            else:
                print(f"[GITHUB] Error getting file SHA: {response.status_code}")
                return None
        except Exception as e:
            print(f"[GITHUB] Exception getting file SHA: {e}")
            return None

    def _read_file_content(self, file_path):
        """Read file content from GitHub"""
        if not self.use_github:
            return None
        
        try:
            url = f'{self.api_base}/repos/{self.owner}/{self.repo}/contents/{file_path}'
            response = requests.get(
                url,
                headers={**self.headers, 'Accept': 'application/vnd.github.v3.raw'},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                return ""
            else:
                print(f"[GITHUB] Error reading file: {response.status_code}")
                return None
        except Exception as e:
            print(f"[GITHUB] Exception reading file: {e}")
            return None

    def _write_file_content(self, file_path, content, commit_message):
        """Write/update file content to GitHub"""
        if not self.use_github:
            return False
        
        try:
            url = f'{self.api_base}/repos/{self.owner}/{self.repo}/contents/{file_path}'
            
            sha = self._get_file_sha(file_path)
            
            content_b64 = base64.b64encode(
                content.encode('utf-8') if isinstance(content, str) else content
            ).decode('utf-8')
            
            payload = {
                'message': commit_message,
                'content': content_b64,
            }
            
            if sha:
                payload['sha'] = sha
            
            response = requests.put(url, headers=self.headers, json=payload, timeout=10)
            
            if response.status_code in [200, 201]:
                print(f"[GITHUB] ✅ Updated {file_path}")
                return True
            else:
                print(f"[GITHUB] ❌ Failed to update {file_path}: {response.status_code}")
                print(f"[GITHUB] Response: {response.text}")
                return False
        except Exception as e:
            print(f"[GITHUB] ❌ Exception updating file: {e}")
            return False

    def delete_key_and_save_solved(self, key_to_delete, email=None):
        """Delete key from data/keys/*.txt and save to data/keys/key_solved.txt"""
        if not self.use_github:
            return False
        
        print(f"[GITHUB] 🔄 Starting delete_key_and_save_solved for key: {key_to_delete}")
        
        key_files = [
            'data/keys/key1d.txt',
            'data/keys/key7d.txt',
            'data/keys/key30d.txt',
            'data/keys/key90d.txt',
        ]
        
        removed_from = []
        
        for file_path in key_files:
            try:
                content = self._read_file_content(file_path)
                
                if content is None:
                    print(f"[GITHUB] ⚠️  Could not read {file_path}")
                    continue
                
                if not content:
                    print(f"[GITHUB] ℹ️  {file_path} is empty")
                    continue
                
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                
                if key_to_delete not in lines:
                    print(f"[GITHUB] ℹ️  Key not found in {file_path}")
                    continue
                
                new_lines = [line for line in lines if line != key_to_delete]
                new_content = '\n'.join(new_lines)
                if new_lines:
                    new_content += '\n'
                
                if self._write_file_content(
                    file_path,
                    new_content,
                    f'Remove key via API'
                ):
                    removed_from.append(file_path)
                    print(f"[GITHUB] ✅ Removed key from {file_path}")
                else:
                    print(f"[GITHUB] ⚠️  Failed to update {file_path}")
                    
            except Exception as e:
                print(f"[GITHUB] ⚠️  Exception processing {file_path}: {e}")
        
        try:
            solved_file_path = 'data/keys/key_solved.txt'
            current_content = self._read_file_content(solved_file_path)
            
            if current_content is None:
                print(f"[GITHUB] ⚠️  Could not read {solved_file_path}")
                current_content = ""
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            email_part = f" | {email}" if email else ""
            new_entry = f"{key_to_delete} | {timestamp}{email_part}\n"
            
            new_content = (current_content + new_entry) if current_content else new_entry
            
            if self._write_file_content(
                solved_file_path,
                new_content,
                f'Add solved key via API'
            ):
                print(f"[GITHUB] ✅ Saved key to {solved_file_path}")
            else:
                print(f"[GITHUB] ⚠️  Failed to update {solved_file_path}")
                
        except Exception as e:
            print(f"[GITHUB] ⚠️  Exception saving to solved file: {e}")
        
        if removed_from:
            print(f"[GITHUB] ✅ Successfully processed key across {len(removed_from)} file(s)")
            return True
        else:
            print(f"[GITHUB] ⚠️  Key was not found in any file (but saved to solved file)")
            return True

    def add_key(self, period, key_value):
        """Add new key to appropriate file"""
        if not self.use_github:
            return False
        
        file_map = {
            '1d': 'data/keys/key1d.txt',
            '7d': 'data/keys/key7d.txt',
            '30d': 'data/keys/key30d.txt',
            '90d': 'data/keys/key90d.txt',
        }
        
        if period not in file_map:
            print(f"[GITHUB] ❌ Invalid period: {period}")
            return False
        
        try:
            file_path = file_map[period]
            content = self._read_file_content(file_path)
            
            if content is None:
                print(f"[GITHUB] ⚠️  Could not read {file_path}")
                return False
            
            new_content = (content + key_value + '\n') if content else (key_value + '\n')
            
            return self._write_file_content(
                file_path,
                new_content,
                f'Add {period} key via API'
            )
        except Exception as e:
            print(f"[GITHUB] ❌ Exception adding key: {e}")
            return False

    def list_keys(self, period):
        """List all keys for a period"""
        if not self.use_github:
            return []
        
        file_map = {
            '1d': 'data/keys/key1d.txt',
            '7d': 'data/keys/key7d.txt',
            '30d': 'data/keys/key30d.txt',
            '90d': 'data/keys/key90d.txt',
        }
        
        if period not in file_map:
            return []
        
        try:
            content = self._read_file_content(file_map[period])
            if content:
                return [line.strip() for line in content.split('\n') if line.strip()]
            return []
        except Exception as e:
            print(f"[GITHUB] ❌ Exception listing keys: {e}")
            return []


# Global instance
github_manager = None

def get_github_manager():
    """Get or create GitHub manager instance"""
    global github_manager
    if github_manager is None:
        github_manager = GitHubDataManager()
    return github_manager

# =================== Cấu hình ===================
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

DB_FILE = "orders.db"
AUTH_FILE = "data/dashboard/auth.json"

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "")

MB_API_URL = "https://thueapibank.vn/historyapimbbankv2/07bf677194ae4972714f01a3abf58c5f"

# Tạo folder data/keys nếu chưa tồn tại
os.makedirs("data/keys", exist_ok=True)

def initialize_key_files():
    """Initialize key files from image build if persistent volume is empty"""
    key_files = {
        "key1d": "data/keys/key1d.txt",
        "key7d": "data/keys/key7d.txt",
        "key30d": "data/keys/key30d.txt",
        "key90d": "data/keys/key90d.txt",
    }
    
    # Check if key files are empty (persistent volume issue)
    all_empty = all(
        not os.path.exists(path) or os.path.getsize(path) == 0 
        for path in key_files.values()
    )
    
    if all_empty:
        print("[INIT] Key files are empty. Attempting to restore from build image...")
        # Copy from image's original location if available
        for key_type, dest_path in key_files.items():
            source_path = f"/app/initial_data/{key_type}.txt"
            if os.path.exists(source_path):
                try:
                    with open(source_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    with open(dest_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"[INIT] Restored {key_type} from image")
                except Exception as e:
                    print(f"[INIT] Failed to restore {key_type}: {e}")
    
    # Check and restore prices.json if empty or missing
    prices_file = "data/prices/prices.json"
    if not os.path.exists(prices_file) or os.path.getsize(prices_file) == 0:
        print("[INIT] prices.json is empty or missing. Attempting to restore from build image...")
        source_path = "/app/initial_data/prices.json"
        if os.path.exists(source_path):
            try:
                with open(source_path, "r", encoding="utf-8") as f:
                    content = f.read()
                os.makedirs(os.path.dirname(prices_file), exist_ok=True)
                with open(prices_file, "w", encoding="utf-8") as f:
                    f.write(content)
                print("[INIT] Restored prices.json from image")
            except Exception as e:
                print(f"[INIT] Failed to restore prices.json: {e}")

# Lock for file operations to prevent race conditions
file_locks = {}
lock_manager = Lock()

def get_file_lock(file_path):
    """Lấy lock cho một file (thread-safe)"""
    with lock_manager:
        if file_path not in file_locks:
            file_locks[file_path] = Lock()
        return file_locks[file_path]

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
    c.execute('''
        CREATE TABLE IF NOT EXISTS key_delivery_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT,
            email TEXT,
            key TEXT,
            period TEXT,
            status TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

def log_key_delivery(uid, email, key, period, status="sent"):
    """Ghi lại lần gửi key để tracking"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO key_delivery_log (uid, email, key, period, status)
        VALUES (?, ?, ?, ?, ?)
    """, (uid, email, key, period, status))
    conn.commit()
    conn.close()
    print(f"[TRACKING] Logged delivery: UID={uid}, Email={email}, Key={key}, Period={period}, Status={status}")

# =================== Prices Management ===================
def load_prices():
    """Load prices from JSON file"""
    price_file = os.path.join("data", "prices", "prices.json")
    
    # Default prices if file doesn't exist
    default_prices = {
        "1d": {"label": "1 Ngày", "amount": 25000, "currency": "VND"},
        "7d": {"label": "1 Tuần", "amount": 70000, "currency": "VND"},
        "30d": {"label": "1 Tháng", "amount": 300000, "currency": "VND"},
        "90d": {"label": "1 Mùa", "amount": 600000, "currency": "VND"}
    }
    
    try:
        if os.path.exists(price_file):
            with open(price_file, "r", encoding="utf-8") as f:
                prices = json.load(f)
                return prices if prices else default_prices
        return default_prices
    except Exception as e:
        print(f"[PRICES ERROR] Failed to load prices: {e}")
        return default_prices

def save_prices(prices):
    """Save prices to JSON file"""
    price_file = os.path.join("data", "prices", "prices.json")
    
    try:
        os.makedirs(os.path.dirname(price_file), exist_ok=True)
        with open(price_file, "w", encoding="utf-8") as f:
            json.dump(prices, f, indent=4, ensure_ascii=False)
        print(f"[PRICES] Saved prices to {price_file}")
        return True
    except Exception as e:
        print(f"[PRICES ERROR] Failed to save prices: {e}")
        return False

def get_price(period_code):
    """Get price for a specific period"""
    prices = load_prices()
    return prices.get(period_code, {}).get("amount", 0)

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
    
    # Dùng lock để đảm bảo đọc file đúng
    file_lock = get_file_lock(file_path)
    
    with file_lock:
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
    
    # Dùng lock để tránh đọc file khi file đang được ghi
    file_lock = get_file_lock(file_path)
    
    with file_lock:
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

def delete_key_from_file(key_to_delete, email=None):
    """
    Xóa key cụ thể từ TẤT CẢ file key và lưu vào key_solved.txt
    
    Dùng GitHub API nếu có GITHUB_TOKEN, nếu không dùng local files
    """
    if not key_to_delete:
        print(f"[DELETE_KEY] ❌ No key provided")
        return False
    
    key_to_delete = key_to_delete.strip()  # Ensure stripped
    print(f"[DELETE_KEY] ✅ START: Processing key: [{key_to_delete}]")
    
    # Try GitHub API first (if available)
    github_mgr = get_github_manager()
    if github_mgr.use_github:
        print("[DELETE_KEY] 🔄 Using GitHub API to update data...")
        success = github_mgr.delete_key_and_save_solved(key_to_delete, email)
        if success:
            print("[DELETE_KEY] ✅ GitHub API update successful")
            return True
        else:
            print("[DELETE_KEY] ⚠️  GitHub API update failed, continuing with local files...")
    
    # Fallback: Local file operations
    print("[DELETE_KEY] 📁 Using local file operations...")
    
    solved_file = get_solved_file_path()
    keys_dir = os.path.join("data", "keys")
    key_files = ["key1d.txt", "key7d.txt", "key30d.txt", "key90d.txt"]
    
    removed_from = []
    key_found = False
    
    try:
        # Step 1: Xóa key từ TẤT CẢ các file
        for key_file in key_files:
            full_path = os.path.join(keys_dir, key_file)
            
            if not os.path.exists(full_path):
                print(f"[DELETE_KEY] ℹ️  File not found: {full_path}")
                continue
            
            try:
                # Đọc file
                with open(full_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                print(f"[DELETE_KEY] Read {len(lines)} lines from {full_path}")
                
                # Tìm key (so sánh sau strip)
                found_indices = []
                for i, line in enumerate(lines):
                    if line.strip() == key_to_delete:
                        found_indices.append(i)
                
                if found_indices:
                    print(f"[DELETE_KEY] Found at line(s): {found_indices}")
                    key_found = True
                    
                    # Xóa những lines có key
                    new_lines = [line for i, line in enumerate(lines) if i not in found_indices]
                    
                    # Ghi file lại
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.writelines(new_lines)
                        f.flush()
                        os.fsync(f.fileno())
                    
                    print(f"[DELETE_KEY] ✅ Removed {len(found_indices)} occurrence(s) from {key_file}")
                    removed_from.append(key_file)
                else:
                    print(f"[DELETE_KEY] ℹ️  Key not found in {full_path}")
                    
            except Exception as e:
                print(f"[DELETE_KEY] ❌ Error processing {full_path}: {e}")
        
        # Step 2: Luôn lưu key vào key_solved.txt
        print(f"[DELETE_KEY] 💾 Saving key to {solved_file}...")
        solved_dir = os.path.dirname(solved_file)
        os.makedirs(solved_dir, exist_ok=True)
        
        try:
            with open(solved_file, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                email_part = f" | {email}" if email else ""
                f.write(f"{key_to_delete} | {timestamp}{email_part}\n")
                f.flush()
                os.fsync(f.fileno())
            print(f"[DELETE_KEY] ✅ Successfully saved to {solved_file}")
        except Exception as e:
            print(f"[DELETE_KEY] ❌ Failed to save to {solved_file}: {e}")
            return False
        
        # Summary
        if removed_from:
            print(f"[DELETE_KEY] ✅ COMPLETED: Removed from {removed_from} and saved to solved file")
        elif key_found:
            print(f"[DELETE_KEY] ✅ COMPLETED: Found and saved to solved file")
        else:
            print(f"[DELETE_KEY] ⚠️  Key not found in any file but saved to solved file anyway")
        
        return True
        
    except Exception as e:
        print(f"[DELETE_KEY] ❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False
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
        # tìm template an toàn theo path file này
        base_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(base_dir, "templates", "gmail.html")

        if not os.path.exists(template_path):
            err = f"Template not found: {template_path}"
            print(f"[EMAIL ERROR] {err}")
            return False, err

        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        key_for_email = key if key is not None else "N/A"
        
        # Map period để hiển thị
        period_display_map = {
            "1 day": "1 Ngày",
            "7 day": "1 Tuần", 
            "30 day": "1 Tháng",
            "90 day": "1 Mùa"
        }
        period_display = period_display_map.get(period, period)

        # Replace template variables instead of using .format() to avoid issues with CSS braces
        try:
            html_content = html_content.replace("{{uid}}", uid)
            html_content = html_content.replace("{{key}}", key_for_email)
            html_content = html_content.replace("{{period}}", period_display)
            html_content = html_content.replace("{{link}}", "https://install.muakey.cloud/?auto=1&version=v1&pwd=666CHEATV1-ABC")
            html_content = html_content.replace("\r", "")
        except Exception as e:
            print(f"[EMAIL ERROR] Template replacement error: {e}")
            return False, f"Template replacement error: {e}"

        # Gửi qua SendGrid
        try:
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            message = Mail(
                from_email=FROM_EMAIL,
                to_emails=email,
                subject="🔑 Key & Mã đơn hàng của bạn đã sẵn sàng!",
                html_content=html_content
            )
            response = sg.send(message)

            if response.status_code == 202:
                print(f"[EMAIL SENT] {email} ({uid})")
                return True, ""
            else:
                err = f"SendGrid error: {response.status_code}"
                print(f"[EMAIL ERROR] {err}")
                return False, err
        except Exception as sg_err:
            print(f"[EMAIL ERROR] SendGrid: {sg_err}")
            return False, str(sg_err)

    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False, f"Lỗi gửi email: {e}"

# =================== Admin Dashboard Functions ===================
# OTP storage: {email: {'code': '123456', 'expires': datetime, 'attempts': 0}}
otp_storage = {}
OTP_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 5

def load_auth_config():
    """Load authorized emails from auth.json"""
    try:
        os.makedirs(os.path.dirname(AUTH_FILE), exist_ok=True)
        if not os.path.exists(AUTH_FILE):
            default_config = {"authorized_emails": [], "sessions": {}}
            with open(AUTH_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2)
            return default_config
        
        with open(AUTH_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[AUTH] Error loading auth config: {e}")
        return {"authorized_emails": [], "sessions": {}}

def is_email_authorized(email):
    """Check if email is in authorized list"""
    config = load_auth_config()
    return email.lower() in [e.lower() for e in config.get("authorized_emails", [])]

def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

def send_otp_email(email, otp):
    """Send OTP to email"""
    try:
        if not SENDGRID_API_KEY or not FROM_EMAIL:
            print("[OTP] SendGrid not configured")
            return False, "Email service not configured"
        
        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=email,
            subject='Mã xác thực Admin Dashboard',
            html_content=f'''
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #333;">Mã xác thực đăng nhập</h2>
                <p>Mã OTP của bạn là:</p>
                <div style="background: #f0f0f0; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 5px; margin: 20px 0;">
                    {otp}
                </div>
                <p style="color: #666;">Mã này sẽ hết hiệu lực sau {OTP_EXPIRY_MINUTES} phút.</p>
                <p style="color: #666; font-size: 12px;">Nếu bạn không yêu cầu mã này, vui lòng bỏ qua email này.</p>
            </div>
            '''
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        if response.status_code in [200, 201, 202]:
            return True, "OTP sent successfully"
        else:
            return False, f"Failed to send OTP: {response.status_code}"
            
    except Exception as e:
        print(f"[OTP EMAIL ERROR] {e}")
        return False, str(e)

def verify_otp(email, otp_code):
    """Verify OTP code"""
    if email not in otp_storage:
        return False, "OTP not found or expired"
    
    stored = otp_storage[email]
    
    # Check expiry
    if datetime.now() > stored['expires']:
        del otp_storage[email]
        return False, "OTP expired"
    
    # Check attempts
    if stored['attempts'] >= MAX_OTP_ATTEMPTS:
        del otp_storage[email]
        return False, "Too many failed attempts"
    
    # Verify code
    if stored['code'] != otp_code:
        otp_storage[email]['attempts'] += 1
        return False, "Invalid OTP"
    
    # Success - remove OTP
    del otp_storage[email]
    return True, "OTP verified"

def require_admin_auth(f):
    """Decorator to require admin authentication"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_email' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def get_all_dashboard_data():
    """Get all data for dashboard"""
    try:
        data = {
            'keys': {
                '1d': {'count': count_keys('1d'), 'list': get_keys_by_type('1d')[:10]},
                '7d': {'count': count_keys('7d'), 'list': get_keys_by_type('7d')[:10]},
                '30d': {'count': count_keys('30d'), 'list': get_keys_by_type('30d')[:10]},
                '90d': {'count': count_keys('90d'), 'list': get_keys_by_type('90d')[:10]},
            },
            'prices': load_prices(),
            'coupons': load_coupons(),
            'orders': get_recent_orders(20),
            'stats': {
                'total_keys': sum(count_keys(t) for t in ['1d', '7d', '30d', '90d']),
                'total_orders': get_total_orders(),
                'total_coupons': len(load_coupons()),
            }
        }
        return data
    except Exception as e:
        print(f"[DASHBOARD DATA ERROR] {e}")
        return {}

def get_recent_orders(limit=20):
    """Get recent orders from database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT uid, code, email, status, created_at 
            FROM orders 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,))
        orders = cursor.fetchall()
        conn.close()
        
        return [
            {
                'uid': o[0],
                'code': o[1],
                'email': o[2],
                'status': o[3],
                'created_at': o[4]
            }
            for o in orders
        ]
    except Exception as e:
        print(f"[GET ORDERS ERROR] {e}")
        return []

def get_total_orders():
    """Get total number of orders"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM orders")
        total = cursor.fetchone()[0]
        conn.close()
        return total
    except:
        return 0

# =================== Flask Routes ===================
@app.route("/")
def index():
    uid = generate_uid()
    code = generate_verification_code()
    insert_order(uid, code)
    
    # Load prices from JSON file
    prices = load_prices()
    
    durations = [
        {"category": "v1", "label": prices["1d"]["label"], "value": "1d", "amount": prices["1d"]["amount"], "key_count": count_keys("1d")},
        {"category": "v1", "label": prices["7d"]["label"], "value": "7d", "amount": prices["7d"]["amount"], "key_count": count_keys("7d")},
        {"category": "v1", "label": prices["30d"]["label"], "value": "30d", "amount": prices["30d"]["amount"], "key_count": count_keys("30d")},
        {"category": "v1", "label": prices["90d"]["label"], "value": "90d", "amount": prices["90d"]["amount"], "key_count": count_keys("90d")},
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
        print(f"[ORDER ERROR] Order not found: uid={uid}")
        return jsonify({"status": "error", "message": "Không tìm thấy đơn hàng! Hãy đợi trong giây lát và ấn lại vào nút 'Nhận Key'"}), 404
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
    
    # Log delivery ngay sau khi email gửi thành công
    log_key_delivery(uid, email, key, period, "sent")
    
    # Xóa key từ file và lưu vào key_solved.txt sau khi email gửi thành công
    print(f"[FLOW] Email sent successfully. Now deleting key...")
    print(f"[FLOW] Key to delete: {key}")
    success = delete_key_from_file(key, email)  # Truyền key và email vào hàm
    if success:
        print(f"[FLOW] ✅ Key deleted and moved to key_solved.txt")
    else:
        print(f"[FLOW] ⚠️ Warning: Failed to delete key, but email already sent")
    
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

# =================== API Status Endpoint ===================
@app.route("/api/mbbank/status", methods=["GET"])
def mbbank_api_status():
    """Check MBBank API status"""
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json, text/plain, */*",
            "Connection": "keep-alive"
        })
        
        start_time = datetime.now()
        resp = session.get(MB_API_URL, timeout=10)
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        if resp.status_code == 200:
            data = resp.json()
            transactions = data.get("transactions", [])
            
            return jsonify({
                "status": "ok",
                "online": True,
                "response_time_ms": round(response_time, 2),
                "transaction_count": len(transactions),
                "timestamp": datetime.now().isoformat(),
                "message": "API hoạt động bình thường"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "online": False,
                "response_time_ms": round(response_time, 2),
                "http_status": resp.status_code,
                "timestamp": datetime.now().isoformat(),
                "message": f"API trả về mã lỗi {resp.status_code}"
            }), 200
            
    except requests.exceptions.Timeout:
        return jsonify({
            "status": "error",
            "online": False,
            "timestamp": datetime.now().isoformat(),
            "message": "API timeout (không phản hồi trong 10s)"
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "online": False,
            "timestamp": datetime.now().isoformat(),
            "message": f"Lỗi kết nối: {str(e)}"
        }), 200

# =================== Debug Endpoints ===================
@app.route("/debug/key-status", methods=["GET"])
def debug_key_status():
    """Debug endpoint: Kiểm tra status của key files và delivery log"""
    keys_dir = os.path.join("data", "keys")
    key_files = ["key1d.txt", "key7d.txt", "key30d.txt", "key90d.txt", "key_solved.txt"]
    
    file_status = {}
    total_keys = 0
    for key_file in key_files:
        full_path = os.path.join(keys_dir, key_file)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            file_status[key_file] = {
                "exists": True,
                "line_count": len(lines),
                "sample": lines[:3] if lines else []  # First 3 lines
            }
            if key_file != "key_solved.txt":
                total_keys += len(lines)
        else:
            file_status[key_file] = {"exists": False}
    
    # Get delivery log
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT uid, email, key, period, sent_at 
        FROM key_delivery_log 
        ORDER BY sent_at DESC 
        LIMIT 20
    """)
    recent_deliveries = []
    for row in c.fetchall():
        recent_deliveries.append({
            "uid": row[0],
            "email": row[1],
            "key": row[2],
            "period": row[3],
            "sent_at": row[4]
        })
    conn.close()
    
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file_status": file_status,
        "total_active_keys": total_keys,
        "recent_deliveries": recent_deliveries
    })

@app.route("/debug/check-key/<key>", methods=["GET"])
def debug_check_key(key):
    """Debug endpoint: Kiểm tra một key cụ thể xem nó ở file nào"""
    keys_dir = os.path.join("data", "keys")
    key_files = ["key1d.txt", "key7d.txt", "key30d.txt", "key90d.txt"]
    
    found_in = []
    for key_file in key_files:
        full_path = os.path.join(keys_dir, key_file)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            if key in lines:
                found_in.append(key_file)
    
    # Check delivery log
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT uid, email, period, sent_at 
        FROM key_delivery_log 
        WHERE key = ?
    """, (key,))
    delivery_info = c.fetchone()
    conn.close()
    
    return jsonify({
        "status": "ok",
        "key": key,
        "found_in_files": found_in if found_in else "NOT FOUND",
        "delivery_log": {
            "uid": delivery_info[0],
            "email": delivery_info[1],
            "period": delivery_info[2],
            "sent_at": delivery_info[3]
        } if delivery_info else None
    })

# =================== Admin Dashboard Routes ===================
@app.route("/admin/login")
def admin_login():
    """Admin login page"""
    if 'admin_email' in session:
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

@app.route("/admin/send-otp", methods=["POST"])
def admin_send_otp():
    """Send OTP to email"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'success': False, 'message': 'Email không được để trống'})
        
        # Check if email is authorized
        if not is_email_authorized(email):
            return jsonify({'success': False, 'message': 'Email không có quyền truy cập'})
        
        # Generate OTP
        otp = generate_otp()
        otp_storage[email] = {
            'code': otp,
            'expires': datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES),
            'attempts': 0
        }
        
        # Send OTP
        success, message = send_otp_email(email, otp)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Mã OTP đã được gửi đến {email}',
                'expires_in': OTP_EXPIRY_MINUTES
            })
        else:
            return jsonify({'success': False, 'message': f'Lỗi gửi email: {message}'})
            
    except Exception as e:
        print(f"[SEND OTP ERROR] {e}")
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})

@app.route("/admin/verify-otp", methods=["POST"])
def admin_verify_otp():
    """Verify OTP and login"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        otp = data.get('otp', '').strip()
        remember_me = data.get('remember_me', False)
        
        if not email or not otp:
            return jsonify({'success': False, 'message': 'Email và OTP không được để trống'})
        
        # Verify OTP
        success, message = verify_otp(email, otp)
        
        if success:
            # Create session
            session['admin_email'] = email
            session.permanent = True
            
            # Set session lifetime based on remember_me
            if remember_me:
                # 60 days
                app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=60)
            else:
                # 24 hours (default)
                app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
            
            return jsonify({
                'success': True,
                'message': 'Đăng nhập thành công',
                'redirect': url_for('admin_dashboard')
            })
        else:
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        print(f"[VERIFY OTP ERROR] {e}")
        return jsonify({'success': False, 'message': f'Lỗi: {str(e)}'})

@app.route("/admin/dashboard")
@require_admin_auth
def admin_dashboard():
    """Admin dashboard page"""
    data = get_all_dashboard_data()
    return render_template('admin_dashboard.html', 
                         data=data, 
                         admin_email=session.get('admin_email'))

@app.route("/admin/logout")
def admin_logout():
    """Logout admin"""
    session.pop('admin_email', None)
    return redirect(url_for('admin_login'))

@app.route("/admin/api/keys/<period>", methods=["GET"])
@require_admin_auth
def admin_api_get_keys(period):
    """Get all keys for a period"""
    try:
        keys = get_keys_by_type(period)
        return jsonify({
            'success': True,
            'period': period,
            'count': len(keys),
            'keys': keys
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route("/admin/api/keys/<period>", methods=["POST"])
@require_admin_auth
def admin_api_add_key(period):
    """Add new key"""
    try:
        data = request.get_json()
        key = data.get('key', '').strip()
        
        if not key:
            return jsonify({'success': False, 'message': 'Key không được để trống'})
        
        # Add key to file
        period_map = {'1d': 'key1d.txt', '7d': 'key7d.txt', '30d': 'key30d.txt', '90d': 'key90d.txt'}
        if period not in period_map:
            return jsonify({'success': False, 'message': 'Period không hợp lệ'})
        
        file_path = os.path.join('data/keys', period_map[period])
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(f"{key}\n")
        
        return jsonify({
            'success': True,
            'message': 'Đã thêm key thành công',
            'count': count_keys(period)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route("/admin/api/keys/<period>/<key>", methods=["DELETE"])
@require_admin_auth
def admin_api_delete_key(period, key):
    """Delete key"""
    try:
        success = delete_key(key, session.get('admin_email', ''))
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Đã xóa key thành công',
                'count': count_keys(period)
            })
        else:
            return jsonify({'success': False, 'message': 'Không tìm thấy key'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route("/admin/api/prices", methods=["GET", "POST"])
@require_admin_auth
def admin_api_prices():
    """Get or update prices"""
    try:
        if request.method == "GET":
            prices = load_prices()
            return jsonify({'success': True, 'prices': prices})
        else:
            data = request.get_json()
            prices = data.get('prices', {})
            
            # Save prices
            prices_file = 'data/prices/prices.json'
            os.makedirs(os.path.dirname(prices_file), exist_ok=True)
            with open(prices_file, 'w', encoding='utf-8') as f:
                json.dump(prices, f, indent=2, ensure_ascii=False)
            
            return jsonify({'success': True, 'message': 'Đã cập nhật giá thành công'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route("/admin/api/coupons", methods=["GET"])
@require_admin_auth
def admin_api_get_coupons():
    """Get all coupons"""
    try:
        coupons = load_coupons()
        return jsonify({'success': True, 'coupons': coupons})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route("/admin/api/stats", methods=["GET"])
@require_admin_auth
def admin_api_stats():
    """Get dashboard statistics"""
    try:
        stats = {
            'total_keys': sum(count_keys(t) for t in ['1d', '7d', '30d', '90d']),
            'keys_by_type': {
                '1d': count_keys('1d'),
                '7d': count_keys('7d'),
                '30d': count_keys('30d'),
                '90d': count_keys('90d'),
            },
            'total_orders': get_total_orders(),
            'total_coupons': len(load_coupons()),
            'recent_orders': get_recent_orders(10)
        }
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route("/admin/api/mbbank-status", methods=["GET"])
@require_admin_auth
def admin_api_mbbank_status():
    """Check MB Bank API status for admin dashboard"""
    try:
        # Sử dụng route existing để check status
        from flask import Flask
        with app.test_client() as client:
            response = client.get('/api/mbbank/status')
            data = response.get_json()
            
        if data and data.get('status') == 'active':
            return jsonify({
                'success': True,
                'status': 'online',
                'message': 'MB Bank API is running normally'
            })
        else:
            return jsonify({
                'success': False,
                'status': 'offline',
                'message': 'MB Bank API is not responding'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'error',
            'message': f'Error checking API: {str(e)}'
        })

# =================== Main ===================
if __name__ == "__main__":
    create_db()
    initialize_key_files()
    
    # Sync keys from GitHub on startup
    try:
        from sync_keys import sync_keys_from_github, start_auto_sync
        sync_keys_from_github()
        # Start auto-sync in background
        start_auto_sync()
    except Exception as e:
        print(f"[STARTUP] Warning: Failed to sync keys from GitHub: {e}")
    
    # Start bot polling in a separate thread
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get('PORT', 5550))
    app.run(host="0.0.0.0", port=port)
