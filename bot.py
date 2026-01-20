import os
import json
import requests
import base64
from datetime import datetime
from telebot import TeleBot, types
from telebot.util import extract_arguments

# =================== GitHub API Helper ===================
class GitHubDataManager:
    """Manage key and solved key data via GitHub API"""
    
    def __init__(self):
        self.token = os.environ.get('GITHUB_TOKEN', '')
        self.owner = os.environ.get('GITHUB_OWNER', 'abcxyznd')
        self.repo = os.environ.get('GITHUB_REPO', 'keys')
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
                f'Add {period} key via bot command'
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

    def delete_key(self, period, key_to_delete):
        """Delete a specific key from a period file"""
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
            
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            if key_to_delete not in lines:
                print(f"[GITHUB] ℹ️  Key not found in {file_path}")
                return False
            
            # Remove the key
            new_lines = [line for line in lines if line != key_to_delete]
            new_content = '\n'.join(new_lines)
            if new_lines:
                new_content += '\n'
            
            return self._write_file_content(
                file_path,
                new_content,
                f'Remove key via bot command'
            )
        except Exception as e:
            print(f"[GITHUB] ❌ Exception deleting key: {e}")
            return False


# Global instance
github_manager = None

def get_github_manager():
    """Get or create GitHub manager instance"""
    global github_manager
    if github_manager is None:
        github_manager = GitHubDataManager()
    return github_manager

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
    """Save coupons to JSON file and GitHub API"""
    try:
        os.makedirs(os.path.dirname(COUPON_FILE), exist_ok=True)
        with open(COUPON_FILE, "w", encoding="utf-8") as f:
            json.dump(coupons, f, indent=2, ensure_ascii=False)
        
        # Update GitHub if available
        github_mgr = get_github_manager()
        if github_mgr.use_github:
            content = json.dumps(coupons, indent=2, ensure_ascii=False)
            github_mgr._write_file_content(
                'data/coupon/coupons.json',
                content,
                'Update coupons via bot command'
            )
        
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
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔑 Xem Key", callback_data="menu_xemkey"),
        types.InlineKeyboardButton("➕ Thêm Key", callback_data="menu_themkey")
    )
    markup.add(
        types.InlineKeyboardButton("❌ Xóa Key", callback_data="menu_xoakey"),
        types.InlineKeyboardButton("🔄 Đồng bộ", callback_data="menu_syncdata")
    )
    markup.add(
        types.InlineKeyboardButton("🎟️ Thêm Coupon", callback_data="menu_themcoupon"),
        types.InlineKeyboardButton("🗑️ Xóa Coupon", callback_data="menu_xoacoupon")
    )
    markup.add(
        types.InlineKeyboardButton("📋 Coupon hiện có", callback_data="menu_couponhienco"),
        types.InlineKeyboardButton("💰 Xem giá", callback_data="menu_xemgia")
    )
    markup.add(
        types.InlineKeyboardButton("✏️ Chỉnh giá", callback_data="menu_chinhgia"),
        types.InlineKeyboardButton("🔗 Rút gọn link", callback_data="menu_rutgonlink")
    )
    markup.add(
        types.InlineKeyboardButton("📎 Xem link rút gọn", callback_data="menu_showshortenurl")
    )
    bot.send_message(message.chat.id, 
                    "👋 <b>Chào mừng đến với Bot Quản Lý!</b>\n\n"
                    "Chọn chức năng bạn muốn sử dụng:",
                    reply_markup=markup, parse_mode="HTML")

# =================== CALLBACK HANDLERS ===================

@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def handle_menu_callback(call):
    """Handle main menu callbacks"""
    chat_id = call.message.chat.id
    
    if call.data == "menu_xemkey":
        xem_key(call.message)
    elif call.data == "menu_themkey":
        them_key(call.message)
    elif call.data == "menu_xoakey":
        xoa_key(call.message)
    elif call.data == "menu_syncdata":
        sync_data_command(call.message)
    elif call.data == "menu_themcoupon":
        them_coupon(call.message)
    elif call.data == "menu_xoacoupon":
        xoa_coupon(call.message)
    elif call.data == "menu_couponhienco":
        coupon_hien_co(call.message)
    elif call.data == "menu_xemgia":
        xem_gia(call.message)
    elif call.data == "menu_chinhgia":
        chinh_gia(call.message)
    elif call.data == "menu_rutgonlink":
        rut_gon_link(call.message)
    elif call.data == "menu_showshortenurl":
        show_shortened_urls(call.message)
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("viewkey_"))
def handle_viewkey_callback(call):
    """Handle view key callbacks"""
    chat_id = call.message.chat.id
    
    period_map = {
        "viewkey_1d": "1 Ngày",
        "viewkey_7d": "1 Tuần",
        "viewkey_30d": "1 Tháng",
        "viewkey_90d": "1 Mùa"
    }
    
    period_label = period_map.get(call.data)
    if period_label:
        msg_text, total_pages = format_keys_by_period(period_label, page=0)
        
        markup = types.InlineKeyboardMarkup()
        if total_pages > 1:
            markup.add(types.InlineKeyboardButton("➡️ Trang kế tiếp", callback_data=f"keypage_{period_label}_1"))
        markup.add(types.InlineKeyboardButton("🔙 Quay lại", callback_data="menu_xemkey"))
        
        user_states[chat_id] = {"step": "viewing_keys", "period_label": period_label, "page": 0, "total_pages": total_pages}
        bot.edit_message_text(msg_text, chat_id, call.message.id, reply_markup=markup, parse_mode="HTML")
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("keypage_"))
def handle_keypage_callback(call):
    """Handle key pagination"""
    chat_id = call.message.chat.id
    parts = call.data.split("_")
    period_label = parts[1]
    page = int(parts[2])
    
    msg_text, total_pages = format_keys_by_period(period_label, page=page)
    
    markup = types.InlineKeyboardMarkup()
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ Trang trước", callback_data=f"keypage_{period_label}_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("➡️ Trang kế tiếp", callback_data=f"keypage_{period_label}_{page+1}"))
    
    if nav_buttons:
        markup.row(*nav_buttons)
    markup.add(types.InlineKeyboardButton("🔙 Quay lại", callback_data="menu_xemkey"))
    
    user_states[chat_id].update({"page": page, "total_pages": total_pages})
    bot.edit_message_text(msg_text, chat_id, call.message.id, reply_markup=markup, parse_mode="HTML")
    bot.answer_callback_query(call.id)

# =================== KEY MANAGEMENT ===================

@bot.message_handler(commands=['xemkey'])
def xem_key(message):
    """View unsold keys"""
    chat_id = message.chat.id
    
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    # Get key counts
    count_1d = len(get_keys_by_type("1 Ngày"))
    count_7d = len(get_keys_by_type("1 Tuần"))
    count_30d = len(get_keys_by_type("1 Tháng"))
    count_90d = len(get_keys_by_type("1 Mùa"))
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(f"1 Ngày ({count_1d})", callback_data="viewkey_1d"),
        types.InlineKeyboardButton(f"1 Tuần ({count_7d})", callback_data="viewkey_7d")
    )
    markup.add(
        types.InlineKeyboardButton(f"1 Tháng ({count_30d})", callback_data="viewkey_30d"),
        types.InlineKeyboardButton(f"1 Mùa ({count_90d})", callback_data="viewkey_90d")
    )
    
    bot.send_message(chat_id, "🔑 <b>Chọn loại key:</b>", reply_markup=markup, parse_mode="HTML")
    user_states[chat_id] = {"step": "waiting_view_key_type"}

# Removed old ReplyKeyboard handlers - now using InlineKeyboard

@bot.callback_query_handler(func=lambda call: call.data.startswith("addkey_"))
def handle_addkey_callback(call):
    """Handle add key period selection"""
    chat_id = call.message.chat.id
    
    period_map = {
        "addkey_1d": "1d",
        "addkey_7d": "7d",
        "addkey_30d": "30d",
        "addkey_90d": "90d"
    }
    
    period = period_map.get(call.data)
    if period:
        period_label_map = {
            "1d": "1 Ngày (1d)",
            "7d": "1 Tuần (7d)",
            "30d": "1 Tháng (30d)",
            "90d": "1 Mùa (90d)"
        }
        
        user_states[chat_id] = {"step": "waiting_keys", "period": period}
        bot.edit_message_text(
            f"📝 Gửi các key (mỗi dòng một key):\n\nLoại: {period_label_map[period]}",
            chat_id,
            call.message.id
        )
    
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['themkey'])
def them_key(message):
    """Start adding new key"""
    chat_id = message.chat.id
    
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    user_states[chat_id] = {"step": "waiting_period"}
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("1 Ngày (1d)", callback_data="addkey_1d"),
        types.InlineKeyboardButton("1 Tuần (7d)", callback_data="addkey_7d")
    )
    markup.add(
        types.InlineKeyboardButton("1 Tháng (30d)", callback_data="addkey_30d"),
        types.InlineKeyboardButton("1 Mùa (90d)", callback_data="addkey_90d")
    )
    
    bot.send_message(chat_id, "🔐 Chọn loại key:", reply_markup=markup)

# Removed - now using inline keyboard callback

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
        
        # Update GitHub first (if available)
        github_mgr = get_github_manager()
        if github_mgr.use_github:
            for key in keys:
                success = github_mgr.add_key(period, key)
                if not success:
                    print(f"[BOT] Warning: Failed to add key to GitHub: {key}")
        
        # Always update local file as fallback
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

@bot.callback_query_handler(func=lambda call: call.data.startswith("delkey_"))
def handle_delkey_period_callback(call):
    """Handle delete key period selection"""
    chat_id = call.message.chat.id
    
    period_map = {
        "delkey_1d": "1d",
        "delkey_7d": "7d",
        "delkey_30d": "30d",
        "delkey_90d": "90d"
    }
    
    period = period_map.get(call.data)
    if not period:
        bot.answer_callback_query(call.id, "❌ Lựa chọn không hợp lệ!")
        return
    
    try:
        # Try to get keys from GitHub first
        github_mgr = get_github_manager()
        lines = []
        
        if github_mgr.use_github:
            print(f"[BOT] Fetching keys from GitHub for period: {period}")
            lines = github_mgr.list_keys(period)
            print(f"[BOT] Got {len(lines)} keys from GitHub")
        
        # Fallback to local file if GitHub is not available or returns empty
        if not lines:
            file_path = os.path.join("data", "keys", f"key{period}.txt")
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                print(f"[BOT] Got {len(lines)} keys from local file")
        
        if not lines:
            bot.edit_message_text("❌ Không có key để xóa!", chat_id, call.message.id)
            bot.answer_callback_query(call.id)
            return
        
        user_states[chat_id] = {"step": "waiting_delete_key", "period": period, "keys": lines}
        
        # Tạo inline keyboard với danh sách keys (tối đa 10 keys)
        markup = types.InlineKeyboardMarkup(row_width=1)
        display_keys = lines[:10]
        for i, key in enumerate(display_keys):
            markup.add(types.InlineKeyboardButton(key, callback_data=f"confirmdelkey_{i}"))
        markup.add(types.InlineKeyboardButton("❌ Hủy", callback_data="menu_xoakey"))
        
        msg = f"📋 Chọn key để xóa:\n\n"
        msg += f"Tổng số key: {len(lines)}\n"
        
        if len(lines) > 10:
            msg += f"(Hiển thị 10/{len(lines)} key đầu tiên)"
        
        bot.edit_message_text(msg, chat_id, call.message.id, reply_markup=markup)
        
    except Exception as e:
        print(f"[KEY ERROR] {e}")
        bot.edit_message_text(f"❌ Lỗi: {e}", chat_id, call.message.id)
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirmdelkey_"))
def handle_confirm_delkey_callback(call):
    """Handle key deletion confirmation"""
    chat_id = call.message.chat.id
    key_index = int(call.data.split("_")[1])
    
    if chat_id not in user_states or "keys" not in user_states[chat_id]:
        bot.answer_callback_query(call.id, "❌ Phiên đã hết hạn!")
        return
    
    period = user_states[chat_id]["period"]
    keys = user_states[chat_id]["keys"]
    
    if key_index >= len(keys):
        bot.answer_callback_query(call.id, "❌ Key không tìm thấy!")
        return
    
    key_to_delete = keys[key_index]
    file_path = os.path.join("data", "keys", f"key{period}.txt")
    
    try:
        # Update GitHub first (if available)
        github_mgr = get_github_manager()
        if github_mgr.use_github:
            success = github_mgr.delete_key(period, key_to_delete)
            if not success:
                print(f"[BOT] Warning: Failed to delete key from GitHub")
        
        # Always update local file
        keys.remove(key_to_delete)
        
        with open(file_path, "w", encoding="utf-8") as f:
            for key in keys:
                f.write(key + "\n")
        
        del user_states[chat_id]
        
        bot.edit_message_text(f"✅ Đã xóa key:\n{key_to_delete}", chat_id, call.message.id)
        
        # Notify admin
        tg_msg = f"➖ <b>Xóa key</b>\nLoại: {period}\nKey: {key_to_delete}"
        send_telegram(tg_msg)
        
    except Exception as e:
        print(f"[KEY ERROR] {e}")
        bot.edit_message_text(f"❌ Lỗi xóa key: {e}", chat_id, call.message.id)
        del user_states[chat_id]
    
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['xoakey'])
def xoa_key(message):
    """Start deleting key"""
    chat_id = message.chat.id
    
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    user_states[chat_id] = {"step": "waiting_delete_period"}
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("1 Ngày (1d)", callback_data="delkey_1d"),
        types.InlineKeyboardButton("1 Tuần (7d)", callback_data="delkey_7d")
    )
    markup.add(
        types.InlineKeyboardButton("1 Tháng (30d)", callback_data="delkey_30d"),
        types.InlineKeyboardButton("1 Mùa (90d)", callback_data="delkey_90d")
    )
    
    bot.send_message(chat_id, "🔐 Chọn loại key để xóa:", reply_markup=markup)

# Removed - now using inline keyboard callbacks

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
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("1 Ngày (1d)", callback_data="coupontype_1d"),
        types.InlineKeyboardButton("1 Tuần (7d)", callback_data="coupontype_7d")
    )
    markup.add(
        types.InlineKeyboardButton("1 Tháng (30d)", callback_data="coupontype_30d"),
        types.InlineKeyboardButton("1 Mùa (90d)", callback_data="coupontype_90d")
    )
    markup.add(types.InlineKeyboardButton("📦 Tất cả", callback_data="coupontype_all"))
    
    bot.send_message(chat_id, "🎯 Chọn loại hàng áp dụng:", reply_markup=markup)
    
    user_states[chat_id]["selected_types"] = []
    user_states[chat_id]["coupon_msg_id"] = None

@bot.callback_query_handler(func=lambda call: call.data.startswith("coupontype_"))
def handle_coupon_type_callback(call):
    """Handle coupon type selection"""
    chat_id = call.message.chat.id
    
    if chat_id not in user_states:
        bot.answer_callback_query(call.id, "❌ Phiên đã hết hạn!")
        return
    
    type_map = {
        "coupontype_1d": "1d",
        "coupontype_7d": "7d",
        "coupontype_30d": "30d",
        "coupontype_90d": "90d",
        "coupontype_all": "all"
    }
    
    period_code = type_map.get(call.data)
    
    if period_code == "all":
        user_states[chat_id]["types"] = ["1d", "7d", "30d", "90d"]
        bot.edit_message_text("✅ Đã chọn: Tất cả", chat_id, call.message.id)
        save_new_coupon_inline(chat_id)
    else:
        selected = user_states[chat_id].get("selected_types", [])
        if period_code not in selected:
            selected.append(period_code)
        
        user_states[chat_id]["selected_types"] = selected
        
        # Update keyboard
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("1 Ngày (1d)" + (" ✓" if "1d" in selected else ""), callback_data="coupontype_1d"),
            types.InlineKeyboardButton("1 Tuần (7d)" + (" ✓" if "7d" in selected else ""), callback_data="coupontype_7d")
        )
        markup.add(
            types.InlineKeyboardButton("1 Tháng (30d)" + (" ✓" if "30d" in selected else ""), callback_data="coupontype_30d"),
            types.InlineKeyboardButton("1 Mùa (90d)" + (" ✓" if "90d" in selected else ""), callback_data="coupontype_90d")
        )
        markup.add(
            types.InlineKeyboardButton("📦 Tất cả", callback_data="coupontype_all"),
            types.InlineKeyboardButton("✅ Hoàn thành", callback_data="coupontype_done")
        )
        
        msg = f"🎯 Đã chọn: {', '.join(selected)}\n\nChọn thêm hoặc nhấn ✅ Hoàn thành"
        bot.edit_message_text(msg, chat_id, call.message.id, reply_markup=markup)
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "coupontype_done")
def handle_coupon_done_callback(call):
    """Finish coupon type selection"""
    chat_id = call.message.chat.id
    
    if chat_id not in user_states:
        bot.answer_callback_query(call.id, "❌ Phiên đã hết hạn!")
        return
    
    selected_types = user_states.get(chat_id, {}).get("selected_types", [])
    
    if not selected_types:
        bot.answer_callback_query(call.id, "❌ Chọn ít nhất 1 loại!")
        return
    
    user_states[chat_id]["types"] = selected_types
    bot.edit_message_text("✅ Hoàn thành lựa chọn", chat_id, call.message.id)
    save_new_coupon_inline(chat_id)
    bot.answer_callback_query(call.id)

def save_new_coupon_inline(chat_id):
    """Save the new coupon (for inline keyboard)"""
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

# Removed old ReplyKeyboard handlers for coupon types
# Removed - now using inline keyboard callback

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

@bot.callback_query_handler(func=lambda call: call.data.startswith("shorten_"))
def handle_shorten_service_callback(call):
    """Handle link shortener service selection"""
    chat_id = call.message.chat.id
    
    service_map = {
        "shorten_tinyurl": "tinyurl",
        "shorten_isgd": "isgd"
    }
    
    service = service_map.get(call.data)
    if not service:
        bot.answer_callback_query(call.id, "❌ Lựa chọn không hợp lệ!")
        return
    
    user_states[chat_id] = {"step": "waiting_link_to_shorten", "service": service}
    
    if service == "tinyurl":
        # Ask if user wants custom alias for tinyurl
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Có", callback_data="alias_yes"),
            types.InlineKeyboardButton("❌ Không", callback_data="alias_no")
        )
        bot.edit_message_text("🔗 Bạn có muốn tùy chọn alias cho TinyURL không?", chat_id, call.message.id, reply_markup=markup)
        user_states[chat_id]["step"] = "waiting_alias_choice"
    else:
        bot.edit_message_text("🔗 Nhập link cần rút gọn:", chat_id, call.message.id)
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("alias_"))
def handle_alias_choice_callback(call):
    """Handle alias choice"""
    chat_id = call.message.chat.id
    
    if call.data == "alias_yes":
        user_states[chat_id]["step"] = "waiting_link_to_shorten"
        user_states[chat_id]["use_alias"] = True
        bot.edit_message_text("🔗 Nhập link cần rút gọn:", chat_id, call.message.id)
    else:
        user_states[chat_id]["step"] = "waiting_link_to_shorten"
        user_states[chat_id]["use_alias"] = False
        bot.edit_message_text("🔗 Nhập link cần rút gọn:", chat_id, call.message.id)
    
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['rutgonlink'])
def rut_gon_link(message):
    """Shorten link using tinyurl or is.gd API"""
    chat_id = message.chat.id
    # Ask user to choose service
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🔗 TinyURL", callback_data="shorten_tinyurl"),
        types.InlineKeyboardButton("🔗 is.gd", callback_data="shorten_isgd")
    )
    bot.send_message(chat_id, "🔗 <b>Chọn dịch vụ rút gọn link:</b>", reply_markup=markup, parse_mode="HTML")
    user_states[chat_id] = {"step": "waiting_service_choice"}

# Removed - now using inline keyboard callbacks

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

@bot.callback_query_handler(func=lambda call: call.data.startswith("showurl_"))
def handle_show_url_callback(call):
    """Display shortened URLs for selected service"""
    chat_id = call.message.chat.id
    
    service_map = {
        "showurl_tinyurl": "tinyurl",
        "showurl_isgd": "isgd"
    }
    
    service = service_map.get(call.data)
    if not service:
        bot.answer_callback_query(call.id, "❌ Lựa chọn không hợp lệ!")
        return
    
    # Load data from corresponding file
    urls_data = load_shortened_urls(service)
    
    if not urls_data:
        bot.edit_message_text(f"📭 Không có link nào từ dịch vụ {service.upper()}", chat_id, call.message.id)
        bot.answer_callback_query(call.id)
        return
    
    # Build message with all URLs
    msg = f"🔗 <b>Link rút gọn từ {service.upper()}:</b>\n\n"
    
    for key, entry in urls_data.items():
        if isinstance(entry, dict):
            original = entry.get("original_url", "N/A")
            shortened = entry.get("shortened_url", "N/A")
            created_at = entry.get("created_at", "N/A")
            
            msg += f"<b>Gốc:</b> {original}\n"
            msg += f"<b>Rút gọn:</b> <code>{shortened}</code>\n"
            msg += f"<b>Lúc:</b> {created_at}\n"
            msg += "─" * 40 + "\n"
    
    bot.edit_message_text(msg, chat_id, call.message.id, parse_mode="HTML")
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['showshortenurl'])
def show_shortened_urls(message):
    """Show all shortened URLs"""
    chat_id = message.chat.id
    
    # Create inline keyboard with service options
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📌 TinyURL", callback_data="showurl_tinyurl"),
        types.InlineKeyboardButton("📌 is.gd", callback_data="showurl_isgd")
    )
    
    bot.send_message(chat_id, "🔗 <b>Chọn dịch vụ để xem link rút gọn:</b>", reply_markup=markup, parse_mode="HTML")

# =================== PRICES MANAGEMENT ===================

def load_prices():
    """Load prices from JSON file"""
    price_file = os.path.join("data", "prices", "prices.json")
    
    # Default prices if file doesn't exist
    default_prices = {
        "1d": {"label": "1 Ngày", "amount": 25000, "currency": "VND"},
        "7d": {"label": "1 Tuần", "amount": 70000, "currency": "VND"},
        "30d": {"label": "1 Tháng", "amount": 250000, "currency": "VND"},
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

@bot.message_handler(commands=['xemgia'])
def xem_gia(message):
    """View current prices"""
    chat_id = message.chat.id
    
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    prices = load_prices()
    
    msg = "💰 <b>Bảng giá hiện tại:</b>\n\n"
    for period_code, data in prices.items():
        label = data.get("label", period_code)
        amount = data.get("amount", 0)
        currency = data.get("currency", "VND")
        msg += f"<b>{label} ({period_code}):</b> {amount:,} {currency}\n"
    
    bot.send_message(chat_id, msg, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("editprice_"))
def handle_edit_price_callback(call):
    """Handle price editing period selection"""
    chat_id = call.message.chat.id
    
    period_map = {
        "editprice_1d": "1d",
        "editprice_7d": "7d",
        "editprice_30d": "30d",
        "editprice_90d": "90d"
    }
    
    period_code = period_map.get(call.data)
    if not period_code:
        bot.answer_callback_query(call.id, "❌ Lựa chọn không hợp lệ!")
        return
    
    period_label_map = {
        "1d": "1 Ngày (1d)",
        "7d": "1 Tuần (7d)",
        "30d": "1 Tháng (30d)",
        "90d": "1 Mùa (90d)"
    }
    
    prices = load_prices()
    current_price = prices.get(period_code, {}).get("amount", 0)
    
    user_states[chat_id] = {
        "step": "waiting_new_price",
        "period_code": period_code,
        "period_label": period_label_map[period_code]
    }
    
    bot.edit_message_text(
        f"📝 Nhập giá mới cho {period_label_map[period_code]}:\n\nGiá hiện tại: {current_price:,} VND",
        chat_id,
        call.message.id
    )
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['chinhgia'])
def chinh_gia(message):
    """Start editing price"""
    chat_id = message.chat.id
    
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    user_states[chat_id] = {"step": "waiting_price_period"}
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("1 Ngày (1d)", callback_data="editprice_1d"),
        types.InlineKeyboardButton("1 Tuần (7d)", callback_data="editprice_7d")
    )
    markup.add(
        types.InlineKeyboardButton("1 Tháng (30d)", callback_data="editprice_30d"),
        types.InlineKeyboardButton("1 Mùa (90d)", callback_data="editprice_90d")
    )
    
    bot.send_message(chat_id, "💰 Chọn loại key để chỉnh giá:", reply_markup=markup)

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get("step") == "waiting_new_price")
def process_new_price(message):
    """Process and save new price"""
    chat_id = message.chat.id
    price_text = message.text.strip().replace(",", "").replace(".", "")
    
    try:
        new_price = int(price_text)
        
        if new_price <= 0:
            bot.send_message(chat_id, "❌ Giá phải lớn hơn 0!")
            return
        
        period_code = user_states[chat_id]["period_code"]
        period_label = user_states[chat_id]["period_label"]
        
        # Load and update prices
        prices = load_prices()
        old_price = prices.get(period_code, {}).get("amount", 0)
        
        if period_code in prices:
            prices[period_code]["amount"] = new_price
        else:
            prices[period_code] = {
                "label": period_label.split(" (")[0],
                "amount": new_price,
                "currency": "VND"
            }
        
        # Save prices
        if save_prices(prices):
            del user_states[chat_id]
            
            msg = f"✅ Đã cập nhật giá:\n\n"
            msg += f"<b>{period_label}</b>\n"
            msg += f"Giá cũ: {old_price:,} VND\n"
            msg += f"Giá mới: {new_price:,} VND"
            
            bot.send_message(chat_id, msg, parse_mode="HTML")
            
            # Notify admin
            tg_msg = f"💰 <b>Cập nhật giá</b>\n{period_label}\n{old_price:,} VND → {new_price:,} VND"
            send_telegram(tg_msg)
        else:
            bot.send_message(chat_id, "❌ Lỗi lưu giá!")
            
    except ValueError:
        bot.send_message(chat_id, "❌ Giá không hợp lệ! Vui lòng nhập số.")
    except Exception as e:
        print(f"[PRICE ERROR] {e}")
        bot.send_message(chat_id, f"❌ Lỗi: {e}")
        if chat_id in user_states:
            del user_states[chat_id]

# =================== SYNC DATA FROM GITHUB ===================

def sync_data_by_type(data_type):
    """Sync specific data type from GitHub"""
    GITHUB_RAW_URL = "https://raw.githubusercontent.com/abcxyznd/keys/main"
    
    # Define files for each data type
    data_files = {
        "keys": {
            'data/keys/key1d.txt': 'data/keys/key1d.txt',
            'data/keys/key7d.txt': 'data/keys/key7d.txt',
            'data/keys/key30d.txt': 'data/keys/key30d.txt',
            'data/keys/key90d.txt': 'data/keys/key90d.txt',
            'data/keys/key_solved.txt': 'data/keys/key_solved.txt',
        },
        "coupon": {
            'data/coupon/coupons.json': 'data/coupon/coupons.json',
        },
        "prices": {
            'data/prices/prices.json': 'data/prices/prices.json',
        },
        "links": {
            'data/links/download.json': 'data/links/download.json',
        },
        "all": {}
    }
    
    # If all, merge all data types
    if data_type == "all":
        files_to_sync = {}
        for dtype in ["keys", "coupon", "prices", "links", "shortenurl"]:
            files_to_sync.update(data_files[dtype])
    else:
        files_to_sync = data_files.get(data_type, {})
    
    if not files_to_sync:
        return False, "Loại data không hợp lệ"
    
    success_count = 0
    failed_files = []
    
    for github_path, local_path in files_to_sync.items():
        try:
            url = f"{GITHUB_RAW_URL}/{github_path}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                # Create directory if not exists
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                # Write file
                with open(local_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                success_count += 1
            else:
                failed_files.append(os.path.basename(local_path))
                
        except Exception as e:
            failed_files.append(os.path.basename(local_path))
            print(f"[SYNC ERROR] {os.path.basename(local_path)}: {e}")
    
    return True, f"Đồng bộ {success_count}/{len(files_to_sync)} files"

@bot.callback_query_handler(func=lambda call: call.data.startswith("sync_"))
def handle_sync_callback(call):
    """Process data sync selection"""
    chat_id = call.message.chat.id
    
    # Map button data to data type
    data_type_map = {
        "sync_keys": "keys",
        "sync_coupon": "coupon",
        "sync_prices": "prices",
        "sync_links": "links",
        "sync_shortenurl": "shortenurl",
        "sync_all": "all"
    }
    
    data_type = data_type_map.get(call.data)
    
    if not data_type:
        bot.answer_callback_query(call.id, "❌ Lựa chọn không hợp lệ!")
        return
    
    try:
        bot.edit_message_text(
            f"🔄 Đang đồng bộ từ GitHub...",
            chat_id,
            call.message.id
        )
        
        success, message_text = sync_data_by_type(data_type)
        
        if success:
            # Get updated info based on data type
            extra_info = ""
            if data_type in ["keys", "all"]:
                count_1d = len(get_keys_by_type("1 Ngày"))
                count_7d = len(get_keys_by_type("1 Tuần"))
                count_30d = len(get_keys_by_type("1 Tháng"))
                count_90d = len(get_keys_by_type("1 Mùa"))
                extra_info += (
                    f"\n\n📊 <b>Key hiện có:</b>\n"
                    f"• 1 Ngày: {count_1d}\n"
                    f"• 1 Tuần: {count_7d}\n"
                    f"• 1 Tháng: {count_30d}\n"
                    f"• 1 Mùa: {count_90d}"
                )
            
            if data_type in ["coupon", "all"]:
                coupons = load_coupons()
                extra_info += f"\n\n🎟️ <b>Coupon:</b> {len(coupons)} mã"
            
            if data_type in ["prices", "all"]:
                extra_info += "\n\n💰 <b>Prices:</b> Đã cập nhật bảng giá"
            
            msg = f"✅ <b>Đồng bộ hoàn tất!</b>\n\n{message_text}{extra_info}"
            bot.edit_message_text(msg, chat_id, call.message.id, parse_mode="HTML")
        else:
            bot.edit_message_text(f"❌ {message_text}", chat_id, call.message.id)
        
    except Exception as e:
        print(f"[SYNC ERROR] {e}")
        bot.edit_message_text(f"❌ Lỗi đồng bộ: {e}", chat_id, call.message.id)
    
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['syncdata'])
def sync_data_command(message):
    """Sync data from GitHub repository with selection options"""
    chat_id = message.chat.id
    
    if not is_admin(chat_id):
        bot.send_message(chat_id, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    # Show data type selection
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔑 Keys", callback_data="sync_keys"),
        types.InlineKeyboardButton("🎟️ Coupon", callback_data="sync_coupon")
    )
    markup.add(
        types.InlineKeyboardButton("💰 Prices", callback_data="sync_prices"),
        types.InlineKeyboardButton("🔗 Links", callback_data="sync_links")
    )
    markup.add(
        types.InlineKeyboardButton("📎 Shorten URL", callback_data="sync_shortenurl")
    )
    markup.add(
        types.InlineKeyboardButton("📦 Tất cả", callback_data="sync_all")
    )
    
    bot.send_message(
        chat_id,
        "📂 <b>Chọn loại data cần đồng bộ từ GitHub:</b>",
        reply_markup=markup,
        parse_mode="HTML"
    )

# =================== Bot Polling ===================

def start_bot():
    """Start bot polling in a separate thread"""
    print("[BOT] Starting Telegram bot polling...")
    bot.infinity_polling()

if __name__ == "__main__":
    start_bot()
