# GitHub API Integration Guide

## 📋 Tổng Quan

Hệ thống này sử dụng GitHub API để quản lý dữ liệu keys trực tiếp trong kho lưu trữ. Khi khách hàng thanh toán:

1. ✅ Gửi key qua email
2. ✅ Xóa key khỏi `data/keys/key[period].txt`
3. ✅ Lưu key vào `data/keys/key_solved.txt`

**Tất cả các bước này được thực hiện qua GitHub API** mà không cần sửa local files!

---

## 🔑 Bước 1: Tạo GitHub Personal Access Token

### Trên GitHub:
1. Vào [https://github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Cấu hình:
   - **Token name:** `vip-key-api`
   - **Expiration:** No expiration (hoặc 90 days)
   - **Scopes:** ✅ `repo` (full control of private repositories)

4. Click **"Generate token"**
5. **Copy token** và lưu ngay lập tức (chỉ hiển thị 1 lần!)

Token format: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## 🚀 Bước 2: Cấu Hình Environment Variables

### Local (.env file):
```bash
GITHUB_TOKEN=ghp_your_token_here
GITHUB_OWNER=abcxyznd
GITHUB_REPO=keys
SENDGRID_API_KEY=SG.your_key_here
FROM_EMAIL=your-email@gmail.com
```

### Trên Fly.io:
```bash
fly secrets set GITHUB_TOKEN=ghp_your_token_here
fly secrets set GITHUB_OWNER=abcxyznd
fly secrets set GITHUB_REPO=keys
```

### Kiểm tra:
```bash
fly secrets list
```

---

## ✅ Bước 3: Kiểm Tra GitHub API Connection

Chạy script test:

```bash
python -c "from github_helper import get_github_manager; mgr = get_github_manager(); print(f'Connected: {mgr.use_github}')"
```

Output kỳ vọng:
```
[GITHUB] ✅ GitHub API enabled: abcxyznd/keys
Connected: True
```

---

## 📊 Cách Nó Hoạt Động

### Flow thanh toán (Automatic):
```
Thanh toán thành công
    ↓
Gửi email với key
    ↓
Email gửi thành công?
    ├─ Có → Gọi GitHub API
    │       ├─ Xóa key từ data/keys/key[period].txt
    │       └─ Thêm key vào data/keys/key_solved.txt
    │
    └─ Không → Trả lỗi, không update data
```

### Logs:
```
[GITHUB] 🔄 Starting delete_key_and_save_solved for key: 666Cheat-day-TRUsAZVRNvdyL9ov
[GITHUB] ✅ Removed key from data/keys/key1d.txt
[GITHUB] ✅ Saved key to data/keys/key_solved.txt
[DELETE_KEY] ✅ GitHub API update successful
```

---

## 🛠️ Manual Updates (Nếu cần)

### Thêm key mới:
```python
from github_helper import get_github_manager

mgr = get_github_manager()
mgr.add_key('1d', 'NEW-KEY-XXXXXX')
```

### Liệt kê keys:
```python
mgr.list_keys('1d')  # Returns: ['key1', 'key2', ...]
```

### Xóa key thủ công:
```python
mgr.delete_key_and_save_solved('OLD-KEY-XXXXXX')
```

---

## ⚙️ Fallback (Khi GitHub API không available)

Nếu `GITHUB_TOKEN` không được set:
- Hệ thống sẽ **tự động fallback** sang local file operations
- Mọi thứ vẫn hoạt động bình thường (lưu local thay vì GitHub)
- Log: `[GITHUB] ⚠️  GitHub API disabled (missing GITHUB_TOKEN...)`

---

## 🔐 Bảo Mật

- ✅ **Token được lưu trong environment variable**, không hardcode
- ✅ **Chỉ có quyền `repo`** (không thể xóa repo, chỉ edit files)
- ✅ **Token có thể revoke** bất cứ lúc nào trên GitHub
- ✅ **Logs ghi lại mọi update** (commit message)

---

## 📝 Ví Dụ Logs trên GitHub

Mỗi lần key được gửi, GitHub sẽ có commits như:

```
Remove key via API
Add solved key via API
```

Xem tại: `github.com/abcxyznd/keys/commits`

---

## ❌ Troubleshooting

### "GitHub API disabled"
```
❌ Thiếu GITHUB_TOKEN hoặc GITHUB_OWNER/GITHUB_REPO
✅ Set environment variables rồi restart app
```

### "Failed to update file: 401"
```
❌ Token không hợp lệ hoặc hết hạn
✅ Tạo token mới và update environment variable
```

### "Failed to update file: 404"
```
❌ Repo không tồn tại hoặc GITHUB_OWNER sai
✅ Kiểm tra https://github.com/abcxyznd/keys
```

### "Timeout"
```
❌ Kết nối GitHub bị chậm
✅ Bình thường là tạm thời, hệ thống sẽ retry
```

---

## 📞 Support

Nếu cần help:
1. Kiểm tra logs: `fly logs`
2. Kiểm tra environment: `fly secrets list`
3. Test token: `curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user`
