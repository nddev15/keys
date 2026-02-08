import requests
import os
import time
import threading
from datetime import datetime

GITHUB_RAW_URL = "https://raw.githubusercontent.com/nddev15/keys/main"
SYNC_INTERVAL = 300  # 5 phút (300 giây)

def sync_keys_from_github():
    """Đồng bộ file keys và prices từ GitHub về server"""
    # Files cần sync
    files_to_sync = {
        # Keys
        'data/keys/key1d.txt': 'data/keys/key1d.txt',
        'data/keys/key7d.txt': 'data/keys/key7d.txt',
        'data/keys/key30d.txt': 'data/keys/key30d.txt',
        'data/keys/key90d.txt': 'data/keys/key90d.txt',
        'data/keys/keys_solved.json': 'data/keys/keys_solved.json',
        # Prices
        'data/prices/prices.json': 'data/prices/prices.json',
        # Coupons
        'data/coupon/coupons.json': 'data/coupon/coupons.json',
        # Admins
        'data/admin/admin.json': 'data/admin/admin.json',
        # Users
        'data/users/users.json': 'data/users/users.json',
    }
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🔄 [{timestamp}] Đang đồng bộ data từ GitHub...")
    
    success_count = 0
    for github_path, local_path in files_to_sync.items():
        try:
            url = f"{GITHUB_RAW_URL}/{github_path}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                # Tạo thư mục nếu chưa có
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                # Ghi file
                with open(local_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                filename = os.path.basename(local_path)
                print(f"✅ Đã sync: {filename}")
                success_count += 1
            else:
                filename = os.path.basename(local_path)
                print(f"⚠️  Không tìm thấy: {filename} (HTTP {response.status_code})")
                
        except Exception as e:
            filename = os.path.basename(local_path)
            print(f"❌ Lỗi sync {filename}: {e}")
    
    print(f"✅ Hoàn tất đồng bộ ({success_count}/{len(files_to_sync)} files)")
    return success_count > 0

def auto_sync_loop():
    """Tự động sync keys theo định kỳ"""
    print(f"[AUTO-SYNC] Started - sync every {SYNC_INTERVAL}s ({SYNC_INTERVAL//60} minutes)")
    
    while True:
        try:
            time.sleep(SYNC_INTERVAL)
            sync_keys_from_github()
        except Exception as e:
            print(f"[AUTO-SYNC ERROR] {e}")

def start_auto_sync():
    """Khởi động auto-sync trong background thread"""
    sync_thread = threading.Thread(target=auto_sync_loop, daemon=True)
    sync_thread.start()
    print("[AUTO-SYNC] Background thread started")

if __name__ == "__main__":
    sync_keys_from_github()
