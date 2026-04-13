# R2 Drive

基于 Cloudflare R2 的网盘工具，提供 CLI 和 Web 界面来管理云端文件。

## 功能特性

### CLI 命令

- 📤 **上传文件** - 支持单文件、多文件、目录上传
- 📥 **下载文件** - 支持单文件下载和整个目录下载
- 📂 **列出文件** - 查看存储桶中的文件列表
- 🗑️ **删除文件** - 支持删除单个文件或整个目录
- 🔄 **同步目录** - 本地目录与云端同步
- 🔍 **搜索文件** - 按文件名搜索
- 🔗 **分享链接** - 生成签名或公开访问链接
- 📊 **存储统计** - 查看存储桶使用情况

### Web 界面

- 🖥️ **可视化管理** - 现代化 Web 界面
- 📁 **文件浏览** - 文件夹导航、面包屑路径
- ⬆️ **拖拽上传** - 支持文件和文件夹拖拽上传
- 👁️ **在线预览** - 支持图片、文本、PDF 预览
- 🔗 **一键分享** - 生成分享链接
- 🔍 **即时搜索** - 快速搜索文件
- 📊 **存储统计** - 可视化存储信息

## 安装

### 方式一：从源码安装

```bash
git clone https://github.com/xiaojay/r2-drive.git
cd r2-drive
pip install -e .
```

### 方式二：直接使用

```bash
pip install -r requirements.txt
python -m r2_drive.cli --help
```

## 配置

### 初始化配置

```bash
python -m r2_drive.config
```

或者手动创建配置文件 `~/.config/r2-drive/config.json`：

```json
{
    "account_id": "your_account_id",
    "access_key_id": "your_access_key_id",
    "secret_access_key": "your_secret_access_key",
    "bucket_name": "your_bucket_name",
    "public_url": "https://your-bucket.r2.dev"
}
```

### 获取 R2 凭证

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com)
2. 进入 R2 → 管理 R2 API 令牌
3. 创建新的 API 令牌，获取 Account ID、Access Key ID、Secret Access Key

## 使用方法

### CLI 命令

```bash
# 上传文件
r2-drive upload file.txt
r2-drive upload ./folder/ --workers 8

# 下载文件
r2-drive download remote-file.txt
r2-drive pull remote-folder/ --output ./local/

# 列出文件
r2-drive ls
r2-drive ls --prefix documents/

# 删除文件
r2-drive rm file.txt
r2-drive rm folder/ --recursive

# 同步目录
r2-drive sync ./local-folder/ remote-backup/

# 搜索文件
r2-drive search keyword

# 生成分享链接
r2-drive share file.txt
r2-drive url file.txt --public

# 查看统计
r2-drive info
```

### Web 界面

```bash
# 启动 Web 服务器（默认 127.0.0.1:5000）
r2-drive web

# 指定端口
r2-drive web --port 8080

# 允许外部访问
r2-drive web --host 0.0.0.0

# 调试模式
r2-drive web --debug
```

然后在浏览器打开 http://localhost:5000

### Web 界面功能

1. **文件浏览**
   - 点击文件夹进入
   - 面包屑导航快速跳转
   - 返回上级目录

2. **文件上传**
   - 点击"上传"按钮选择文件
   - 拖拽文件到上传区域
   - 支持文件夹上传

3. **文件操作**
   - ⬇️ 下载文件
   - 🔗 生成分享链接
   - ✏️ 重命名文件
   - 🗑️ 删除文件

4. **在线预览**
   - 图片文件直接预览
   - 文本文件代码高亮
   - PDF 文件内嵌预览

5. **批量操作**
   - 勾选多个文件
   - 批量删除

6. **搜索**
   - 实时搜索文件名

7. **统计**
   - 文件数量
   - 总大小
   - 文件类型分布

## 命令速查表

| 命令 | 说明 |
|------|------|
| `r2-drive upload <files>` | 上传文件 |
| `r2-drive download <file>` | 下载文件 |
| `r2-drive pull <dir>` | 下载整个目录 |
| `r2-drive ls` | 列出文件 |
| `r2-drive rm <files>` | 删除文件 |
| `r2-drive sync <local> <remote>` | 同步目录 |
| `r2-drive search <query>` | 搜索文件 |
| `r2-drive url <file>` | 生成访问链接 |
| `r2-drive share <file>` | 生成分享链接 |
| `r2-drive info` | 查看存储信息 |
| `r2-drive web` | 启动 Web 界面 |

## 项目结构

```
r2-drive/
├── r2_drive/
│   ├── __init__.py
│   ├── cli.py          # CLI 命令
│   ├── config.py       # 配置工具
│   ├── web.py          # Web 服务器
│   ├── templates/      # HTML 模板
│   │   ├── index.html
│   │   ├── error.html
│   │   ├── preview_text.html
│   │   ├── preview_image.html
│   │   └── preview_pdf.html
│   └── static/         # 静态资源
│       ├── style.css
│       └── app.js
├── test_connection.py
├── install.sh
├── setup.py
├── requirements.txt
└── README.md
```

## 与 Hermes Agent 集成

R2 Drive 可以与 Hermes Agent 配合使用：

```bash
# 让 Hermes 处理 R2 上的文件
hermes "下载 r2-drive://reports/quarterly.pdf 并总结要点"

# 让 Hermes 上传处理结果
hermes "分析 data.csv 并将结果上传到 r2-drive://analysis/"
```

## 故障排除

### 连接失败

```bash
# 检查配置
python -m r2_drive.config show

# 测试连接
python test_connection.py
```

### Web 界面无法访问

1. 检查端口是否被占用
2. 尝试使用 `--host 0.0.0.0` 允许外部访问
3. 检查防火墙设置

### 上传大文件失败

1. 检查网络连接
2. 增加并发数：`--workers 8`
3. 检查 R2 配额限制

## 开发

### 运行测试

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/
```

### 添加新功能

1. CLI 命令：在 `cli.py` 中添加
2. Web API：在 `web.py` 中添加路由
3. 前端功能：修改 `static/app.js` 和 `templates/`

## 许可证

MIT License

## 相关项目

- [Hermes Agent](https://github.com/xiaojay/hermes-agent) - AI 助手
- [Langfuse Plugin](https://github.com/xiaojay/hermes-langfuse-plugin) - Hermes Langfuse 追踪插件
- [Cloudflare R2](https://developers.cloudflare.com/r2/) - 对象存储服务
