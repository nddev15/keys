"""
GitHub File Editor - Cập nhật file trực tiếp qua GitHub API (Python)

Cách sử dụng:
1. Tạo Personal Access Token tại https://github.com/settings/tokens
2. Set environment variables hoặc điền trực tiếp
3. Chạy: python github_api_updater.py
"""

import os
import json
import base64
import requests
from pathlib import Path

class GitHubFileEditor:
    def __init__(self):
        self.token = os.getenv('GITHUB_TOKEN', 'your_github_token_here')
        self.owner = os.getenv('GITHUB_OWNER', 'abcxyznd')
        self.repo = os.getenv('GITHUB_REPO', 'keys')
        self.api_base = 'https://api.github.com'
        
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
        }

    def get_file(self, file_path):
        """Lấy nội dung file từ GitHub"""
        try:
            url = f'{self.api_base}/repos/{self.owner}/{self.repo}/contents/{file_path}'
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                raise Exception(f'Không tìm thấy file: {response.text}')
            
            data = response.json()
            content = base64.b64decode(data['content']).decode('utf-8')
            
            print(f'📄 Nội dung {file_path}:')
            print(content)
            return {
                'content': content,
                'sha': data['sha'],
                'data': data
            }
        except Exception as e:
            print(f'❌ Lỗi: {str(e)}')
            raise

    def update_file(self, file_path, new_content, commit_message='Update file via API'):
        """Cập nhật file trên GitHub"""
        try:
            url = f'{self.api_base}/repos/{self.owner}/{self.repo}/contents/{file_path}'
            
            # Bước 1: Lấy SHA của file hiện tại
            file_info = self.get_file(file_path)
            sha = file_info['sha']
            
            # Bước 2: Cập nhật file
            content_base64 = base64.b64encode(
                new_content.encode('utf-8') if isinstance(new_content, str) 
                else json.dumps(new_content, indent=2).encode('utf-8')
            ).decode('utf-8')
            
            payload = {
                'message': commit_message,
                'content': content_base64,
                'sha': sha,
            }
            
            response = requests.put(url, headers=self.headers, json=payload)
            
            if response.status_code not in [200, 201]:
                raise Exception(f'Lỗi cập nhật: {response.text}')
            
            result = response.json()
            print(f'✅ Cập nhật thành công!')
            print(f'📌 Commit: {result["commit"]["html_url"]}')
            return result
            
        except Exception as e:
            print(f'❌ Lỗi: {str(e)}')
            raise

    def create_file(self, file_path, content, commit_message='Create file via API'):
        """Tạo file mới trên GitHub"""
        try:
            url = f'{self.api_base}/repos/{self.owner}/{self.repo}/contents/{file_path}'
            
            content_base64 = base64.b64encode(
                content.encode('utf-8') if isinstance(content, str) 
                else json.dumps(content, indent=2).encode('utf-8')
            ).decode('utf-8')
            
            payload = {
                'message': commit_message,
                'content': content_base64,
            }
            
            response = requests.put(url, headers=self.headers, json=payload)
            
            if response.status_code not in [200, 201]:
                raise Exception(f'Lỗi tạo file: {response.text}')
            
            print(f'✅ Tạo file thành công: {file_path}')
            return response.json()
            
        except Exception as e:
            print(f'❌ Lỗi: {str(e)}')
            raise


def main():
    editor = GitHubFileEditor()
    
    print(f'🔗 Repo: {editor.owner}/{editor.repo}\n')
    
    # Ví dụ 1: Đọc file JSON
    file_path = 'data/coupon/coupons.json'
    print('--- Đọc file từ GitHub ---')
    try:
        file_data = editor.get_file(file_path)
        data = json.loads(file_data['content'])
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f'Lỗi khi đọc: {e}')
    
    # Ví dụ 2: Cập nhật file (bỏ comment nếu muốn dùng)
    # print('\n--- Cập nhật file ---')
    # new_data = {'coupon': 'NEW_CODE_2026', 'updated': True}
    # editor.update_file(file_path, json.dumps(new_data, ensure_ascii=False), 'Update coupons via API')
    
    # Ví dụ 3: Tạo file mới
    # new_file_path = 'data/new_file.json'
    # editor.create_file(new_file_path, {'new': 'data'}, 'Create new file via API')


if __name__ == '__main__':
    main()
