"""
GitHub API Helper - Update data/keys files directly via GitHub API
This replaces local file operations with GitHub API calls for cloud-based data management
"""

import os
import json
import base64
import requests
from datetime import datetime

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
                # File doesn't exist yet
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
                return ""  # File doesn't exist
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
            
            # Get current SHA if file exists
            sha = self._get_file_sha(file_path)
            
            # Encode content to base64
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

    def delete_key_and_save_solved(self, key_to_delete):
        """
        Delete key from data/keys/*.txt and save to data/keys/key_solved.txt
        
        Workflow:
        1. Read key1d.txt, key7d.txt, key30d.txt, key90d.txt
        2. Remove key_to_delete from any file that contains it
        3. Append key + timestamp to key_solved.txt
        """
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
        
        # Step 1: Remove key from all key files
        for file_path in key_files:
            try:
                content = self._read_file_content(file_path)
                
                if content is None:
                    print(f"[GITHUB] ⚠️  Could not read {file_path}")
                    continue
                
                if not content:
                    print(f"[GITHUB] ℹ️  {file_path} is empty")
                    continue
                
                # Split into lines and filter out the key
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                
                if key_to_delete not in lines:
                    print(f"[GITHUB] ℹ️  Key not found in {file_path}")
                    continue
                
                # Remove the key
                new_lines = [line for line in lines if line != key_to_delete]
                new_content = '\n'.join(new_lines)
                if new_lines:
                    new_content += '\n'  # Trailing newline
                
                # Update file
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
        
        # Step 2: Save key to key_solved.txt
        try:
            solved_file_path = 'data/keys/key_solved.txt'
            current_content = self._read_file_content(solved_file_path)
            
            if current_content is None:
                print(f"[GITHUB] ⚠️  Could not read {solved_file_path}")
                current_content = ""
            
            # Append new entry with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_entry = f"{key_to_delete} | {timestamp}\n"
            
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
        
        # Summary
        if removed_from:
            print(f"[GITHUB] ✅ Successfully processed key across {len(removed_from)} file(s)")
            return True
        else:
            print(f"[GITHUB] ⚠️  Key was not found in any file (but saved to solved file)")
            return True  # Still return True since we saved it

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
            
            # Append new key
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
