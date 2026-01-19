import requests
import os
import time
import threading
from datetime import datetime

GITHUB_RAW_URL = "https://raw.githubusercontent.com/abcxyznd/keys/main"
SYNC_INTERVAL = 300  # 5 phút (300 giây)

def sync_keys_from_github():
    """Đồng bộ file keys từ GitHub về server"""
    key_files = {
        'key1d.txt': 'data/keys/key1d.txt',
        'key7d.txt': 'data/keys/key7d.txt',
        'key30d.txt': 'data/keys/key30d.txt',
        'key90d.txt': 'data/keys/key90d.txt',
        'key_solved.txt': 'data/keys/key_solved.txt'
    }
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🔄 [{timestamp}] Đang đồng bộ keys từ GitHub...")
    
    success_count = 0
    for filename, filepath in key_files.items():
        try:
            url = f"{GITHUB_RAW_URL}/data/keys/{filename}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                # Tạo thư mục nếu chưa có
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                # Ghi file
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                print(f"✅ Đã sync: {filename}")
                success_count += 1
            else:
                print(f"⚠️  Không tìm thấy: {filename} (HTTP {response.status_code})")
                
        except Exception as e:
            print(f"❌ Lỗi sync {filename}: {e}")
    
    print(f"✅ Hoàn tất đồng bộ keys ({success_count}/{len(key_files)} files)")
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
