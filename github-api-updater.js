/**
 * GitHub File Editor - Cập nhật file trực tiếp qua GitHub API
 * 
 * Cách sử dụng:
 * 1. Tạo Personal Access Token tại https://github.com/settings/tokens
 * 2. Set environment variables hoặc điền trực tiếp
 * 3. Chạy: node github-api-updater.js
 */

const GITHUB_TOKEN = process.env.GITHUB_TOKEN || 'your_github_token_here';
const GITHUB_OWNER = process.env.GITHUB_OWNER || 'abcxyznd';
const GITHUB_REPO = process.env.GITHUB_REPO || 'keys';
const FILE_PATH = 'data/coupon/coupons.json'; // Thay đổi path file cần sửa

/**
 * Cập nhật file trên GitHub
 * @param {string} filePath - Đường dẫn file trong repo
 * @param {string} newContent - Nội dung mới
 * @param {string} commitMessage - Thông điệp commit
 */
async function updateGitHubFile(filePath, newContent, commitMessage) {
  try {
    // Bước 1: Lấy thông tin file hiện tại (để lấy SHA)
    const getFileUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/${filePath}`;
    
    const getResponse = await fetch(getFileUrl, {
      method: 'GET',
      headers: {
        'Authorization': `token ${GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github.v3+json',
      },
    });

    if (!getResponse.ok) {
      throw new Error(`Không tìm thấy file: ${getResponse.statusText}`);
    }

    const fileData = await getResponse.json();
    const currentSha = fileData.sha;

    // Bước 2: Cập nhật file
    const updateResponse = await fetch(getFileUrl, {
      method: 'PUT',
      headers: {
        'Authorization': `token ${GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: commitMessage,
        content: Buffer.from(newContent).toString('base64'), // GitHub API yêu cầu base64
        sha: currentSha, // SHA của file hiện tại để xác nhận
      }),
    });

    if (!updateResponse.ok) {
      throw new Error(`Lỗi cập nhật: ${updateResponse.statusText}`);
    }

    const result = await updateResponse.json();
    console.log('✅ Cập nhật thành công!');
    console.log(`Commit: ${result.commit.html_url}`);
    return result;

  } catch (error) {
    console.error('❌ Lỗi:', error.message);
    throw error;
  }
}

/**
 * Đọc file từ GitHub
 */
async function readGitHubFile(filePath) {
  try {
    const url = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/${filePath}`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `token ${GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github.v3.raw',
      },
    });

    if (!response.ok) {
      throw new Error(`Không tìm thấy file: ${response.statusText}`);
    }

    const content = await response.text();
    console.log('📄 Nội dung file:');
    console.log(content);
    return content;

  } catch (error) {
    console.error('❌ Lỗi:', error.message);
    throw error;
  }
}

/**
 * Ví dụ sử dụng
 */
async function main() {
  console.log(`🔗 Repo: ${GITHUB_OWNER}/${GITHUB_REPO}`);
  console.log(`📁 File: ${FILE_PATH}\n`);

  // Ví dụ 1: Đọc file
  console.log('--- Đọc file từ GitHub ---');
  await readGitHubFile(FILE_PATH);

  // Ví dụ 2: Cập nhật file
  // const newContent = JSON.stringify({ coupon: 'NEW_CODE_2026' }, null, 2);
  // await updateGitHubFile(FILE_PATH, newContent, 'Update coupons via API');
}

// Export functions để sử dụng trong module khác
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { updateGitHubFile, readGitHubFile };
}

// Chạy nếu file được gọi trực tiếp
if (require.main === module) {
  main().catch(console.error);
}
