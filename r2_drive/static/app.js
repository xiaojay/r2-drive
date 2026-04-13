// R2 Drive - 前端逻辑

// 全局状态
let selectedFiles = new Set();
let uploadFiles = [];
let currentPrefix = new URLSearchParams(window.location.search).get('prefix') || '';

// ==================== 工具函数 ====================

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let i = 0;
    while (bytes >= 1024 && i < units.length - 1) {
        bytes /= 1024;
        i++;
    }
    return `${bytes.toFixed(1)} ${units[i]}`;
}

// ==================== 选择操作 ====================

function toggleSelectAll() {
    const selectAll = document.getElementById('selectAll');
    const checkboxes = document.querySelectorAll('.file-checkbox');
    
    checkboxes.forEach(cb => {
        cb.checked = selectAll.checked;
    });
    
    updateSelection();
}

function updateSelection() {
    const checkboxes = document.querySelectorAll('.file-checkbox:checked');
    selectedFiles.clear();
    
    checkboxes.forEach(cb => {
        selectedFiles.add(cb.value);
    });
    
    // 更新全选状态
    const allCheckboxes = document.querySelectorAll('.file-checkbox');
    const selectAll = document.getElementById('selectAll');
    selectAll.checked = allCheckboxes.length > 0 && allCheckboxes.length === checkboxes.length;
}

// ==================== 文件操作 ====================

function refreshList() {
    window.location.reload();
}

function downloadFile(key) {
    window.open(`/api/download/${key}`, '_blank');
}

function previewFile(key) {
    window.open(`/preview/${key}`, '_blank');
}

async function deleteFile(key) {
    if (!confirm(`确定要删除 ${key.split('/').pop()} 吗？`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keys: [key] })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('删除成功', 'success');
            refreshList();
        } else {
            showToast(data.error || '删除失败', 'error');
        }
    } catch (e) {
        showToast('删除失败: ' + e.message, 'error');
    }
}

async function deleteSelected() {
    if (selectedFiles.size === 0) {
        showToast('请先选择文件', 'warning');
        return;
    }
    
    if (!confirm(`确定要删除选中的 ${selectedFiles.size} 个文件吗？`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keys: Array.from(selectedFiles) })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`成功删除 ${data.deleted.length} 个文件`, 'success');
            refreshList();
        } else {
            showToast(data.error || '删除失败', 'error');
        }
    } catch (e) {
        showToast('删除失败: ' + e.message, 'error');
    }
}

async function renameFile(oldKey, isFolder) {
    const oldName = oldKey.split('/').pop();
    const newName = prompt('输入新名称:', oldName);
    
    if (!newName || newName === oldName) {
        return;
    }
    
    // 计算新路径
    const pathParts = oldKey.split('/');
    pathParts.pop();
    const newKey = [...pathParts, newName].join('/') + (isFolder ? '/' : '');
    
    try {
        const response = await fetch('/api/rename', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_key: oldKey, new_key: newKey })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('重命名成功', 'success');
            refreshList();
        } else {
            showToast(data.error || '重命名失败', 'error');
        }
    } catch (e) {
        showToast('重命名失败: ' + e.message, 'error');
    }
}

async function createFolder() {
    const name = prompt('输入文件夹名称:');
    
    if (!name) {
        return;
    }
    
    const path = currentPrefix + name + '/';
    
    try {
        const response = await fetch('/api/new-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('文件夹创建成功', 'success');
            refreshList();
        } else {
            showToast(data.error || '创建失败', 'error');
        }
    } catch (e) {
        showToast('创建失败: ' + e.message, 'error');
    }
}

// ==================== 分享 ====================

let currentShareKey = '';

function shareFile(key) {
    currentShareKey = key;
    document.getElementById('shareModal').classList.add('active');
}

function closeShareModal() {
    document.getElementById('shareModal').classList.remove('active');
}

async function generateShareLink() {
    const expiry = document.getElementById('shareExpiry').value;
    
    try {
        const response = await fetch(`/api/share/${currentShareKey}?expires=${expiry}`);
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('shareUrl').value = data.url;
        } else {
            showToast(data.error || '生成链接失败', 'error');
        }
    } catch (e) {
        showToast('生成链接失败: ' + e.message, 'error');
    }
}

function copyShareLink() {
    const urlInput = document.getElementById('shareUrl');
    urlInput.select();
    document.execCommand('copy');
    showToast('链接已复制', 'success');
}

// 监听有效期变化
document.getElementById('shareExpiry')?.addEventListener('change', generateShareLink);

// 打开分享模态框时生成链接
document.getElementById('shareModal')?.addEventListener('click', function(e) {
    if (e.target === this) closeShareModal();
});

// ==================== 上传 ====================

function showUploadModal() {
    document.getElementById('uploadModal').classList.add('active');
    uploadFiles = [];
    updateUploadList();
}

function closeUploadModal() {
    document.getElementById('uploadModal').classList.remove('active');
    uploadFiles = [];
    document.getElementById('uploadList').innerHTML = '';
}

function switchTab(type) {
    const tabs = document.querySelectorAll('.upload-tabs .tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    event.target.classList.add('active');
    
    const fileInput = document.getElementById('fileInput');
    const folderInput = document.getElementById('folderInput');
    
    if (type === 'files') {
        fileInput.removeAttribute('webkitdirectory');
    } else {
        fileInput.setAttribute('webkitdirectory', '');
    }
}

function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('uploadArea').classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('uploadArea').classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('uploadArea').classList.remove('drag-over');
    
    const files = Array.from(e.dataTransfer.files);
    addFilesToUpload(files);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    addFilesToUpload(files);
}

function handleFolderSelect(e) {
    const files = Array.from(e.target.files);
    addFilesToUpload(files);
}

function addFilesToUpload(files) {
    files.forEach(file => {
        // 检查是否已存在
        if (!uploadFiles.some(f => f.name === file.name && f.size === file.size)) {
            uploadFiles.push(file);
        }
    });
    
    updateUploadList();
}

function updateUploadList() {
    const list = document.getElementById('uploadList');
    const uploadBtn = document.getElementById('uploadBtn');
    
    if (uploadFiles.length === 0) {
        list.innerHTML = '';
        uploadBtn.disabled = true;
        return;
    }
    
    uploadBtn.disabled = false;
    
    list.innerHTML = uploadFiles.map((file, index) => `
        <div class="upload-item">
            <div class="file-info">
                <span>📄</span>
                <span>${file.name}</span>
                <span class="file-size">${formatSize(file.size)}</span>
            </div>
            <button class="btn-icon" onclick="removeUploadFile(${index})">❌</button>
        </div>
    `).join('');
}

function removeUploadFile(index) {
    uploadFiles.splice(index, 1);
    updateUploadList();
}

async function startUpload() {
    if (uploadFiles.length === 0) {
        showToast('请先选择文件', 'warning');
        return;
    }
    
    const uploadBtn = document.getElementById('uploadBtn');
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<span class="loading"></span> 上传中...';
    
    const formData = new FormData();
    formData.append('prefix', currentPrefix);
    
    uploadFiles.forEach(file => {
        formData.append('files', file);
    });
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`成功上传 ${data.uploaded.length} 个文件`, 'success');
            closeUploadModal();
            refreshList();
        } else {
            showToast(data.error || '上传失败', 'error');
        }
    } catch (e) {
        showToast('上传失败: ' + e.message, 'error');
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '上传';
    }
}

// ==================== 搜索 ====================

async function searchFiles() {
    const query = document.getElementById('searchInput').value.trim();
    
    if (!query) {
        refreshList();
        return;
    }
    
    try {
        const response = await fetch(`/api/list?search=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.success) {
            updateFileList(data.items, query);
        } else {
            showToast(data.error || '搜索失败', 'error');
        }
    } catch (e) {
        showToast('搜索失败: ' + e.message, 'error');
    }
}

function updateFileList(items, searchQuery = '') {
    const tbody = document.querySelector('.file-table tbody');
    
    if (items.length === 0) {
        tbody.innerHTML = `
            <tr class="empty-row">
                <td colspan="6">
                    <div class="empty-state">
                        <span class="empty-icon">🔍</span>
                        <p>未找到匹配的文件</p>
                        <button class="btn" onclick="refreshList()">返回</button>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = items.map(item => `
        <tr class="file-row" data-key="${item.key}" data-is-folder="${item.is_folder}">
            <td class="col-checkbox">
                <input type="checkbox" class="file-checkbox" value="${item.key}" onchange="updateSelection()">
            </td>
            <td class="col-icon">${item.icon}</td>
            <td class="col-name">
                ${item.is_folder 
                    ? `<a href="/?prefix=${item.key}">${item.name}</a>`
                    : `<span class="file-name" onclick="previewFile('${item.key}')">${item.name}</span>`
                }
            </td>
            <td class="col-size">${item.size_display || '-'}</td>
            <td class="col-modified">${item.modified || '-'}</td>
            <td class="col-actions">
                ${!item.is_folder ? `
                    <button class="btn-icon" onclick="downloadFile('${item.key}')" title="下载">⬇️</button>
                    <button class="btn-icon" onclick="shareFile('${item.key}')" title="分享">🔗</button>
                ` : ''}
                <button class="btn-icon" onclick="renameFile('${item.key}', ${item.is_folder})" title="重命名">✏️</button>
                <button class="btn-icon" onclick="deleteFile('${item.key}')" title="删除">🗑️</button>
            </td>
        </tr>
    `).join('');
}

// 搜索回车
document.getElementById('searchInput')?.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        searchFiles();
    }
});

// ==================== 统计 ====================

function showInfo() {
    document.getElementById('infoModal').classList.add('active');
    loadInfo();
}

function closeInfoModal() {
    document.getElementById('infoModal').classList.remove('active');
}

async function loadInfo() {
    const content = document.getElementById('infoContent');
    content.innerHTML = '<div style="text-align: center;"><span class="loading"></span></div>';
    
    try {
        const response = await fetch('/api/info');
        const data = await response.json();
        
        if (data.success) {
            // 获取前 10 个文件类型
            const types = Object.entries(data.file_types)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10);
            
            content.innerHTML = `
                <div class="info-stats">
                    <div class="info-stat">
                        <div class="value">${data.file_count}</div>
                        <div class="label">文件总数</div>
                    </div>
                    <div class="info-stat">
                        <div class="value">${data.total_size_display}</div>
                        <div class="label">总大小</div>
                    </div>
                </div>
                
                <div class="file-types">
                    <h4>文件类型分布 (Top 10)</h4>
                    ${types.map(([ext, count]) => `
                        <div class="type-item">
                            <span>${ext || '无扩展名'}</span>
                            <span>${count} 个</span>
                        </div>
                    `).join('')}
                </div>
            `;
        } else {
            content.innerHTML = `<p style="color: var(--danger);">${data.error}</p>`;
        }
    } catch (e) {
        content.innerHTML = `<p style="color: var(--danger);">加载失败: ${e.message}</p>`;
    }
}

// 关闭模态框
document.getElementById('infoModal')?.addEventListener('click', function(e) {
    if (e.target === this) closeInfoModal();
});

// ==================== 键盘快捷键 ====================

document.addEventListener('keydown', function(e) {
    // Ctrl+A 全选
    if (e.ctrlKey && e.key === 'a') {
        e.preventDefault();
        document.getElementById('selectAll').checked = true;
        toggleSelectAll();
    }
    
    // Delete 删除选中
    if (e.key === 'Delete' && selectedFiles.size > 0) {
        deleteSelected();
    }
    
    // Escape 关闭模态框
    if (e.key === 'Escape') {
        closeUploadModal();
        closeShareModal();
        closeInfoModal();
    }
    
    // F5 刷新
    if (e.key === 'F5') {
        e.preventDefault();
        refreshList();
    }
});

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('R2 Drive 已加载');
});
