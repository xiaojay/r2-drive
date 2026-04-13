# R2 Drive

基于 Cloudflare R2 的网盘 CLI 工具，提供简单易用的命令行界面来管理云端文件。

## 功能特性

- 📤 **上传文件** - 支持单文件、多文件、目录上传
- 📥 **下载文件** - 支持单文件下载和整个目录下载
- 📂 **列出文件** - 查看存储桶中的文件列表
- 🗑️ **删除文件** - 支持删除单个文件或整个目录
- 🔄 **同步目录** - 本地目录与云端同步
- 🔍 **搜索文件** - 按文件名搜索
- 🔗 **分享链接** - 生成签名或公开访问链接
- 📊 **存储统计** - 查看存储桶使用情况

## 安装

### 方式一：从源码安装

```bash
git clone https://github.com/yourusername/r2-drive.git
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

### 上传文件

```bash
# 上传单个文件
r2-drive upload file.txt

# 上传多个文件
r2-drive upload file1.txt file2.pdf image.png

# 上传到指定路径
r2-drive upload file.txt --path documents/

# 上传整个目录
r2-drive upload ./my-folder/

# 并发上传（默认4线程）
r2-drive upload ./big-folder/ --workers 8

# 设置为公开访问
r2-drive upload file.txt --public
```

### 下载文件

```bash
# 下载文件
r2-drive download remote-file.txt

# 下载到指定路径
r2-drive download remote-file.txt --output ./local-folder/

# 下载整个目录
r2-drive pull remote-folder/ --output ./local-folder/
```

### 列出文件

```bash
# 列出所有文件
r2-drive ls

# 列出指定路径的文件
r2-drive ls --prefix documents/

# 限制显示数量
r2-drive ls --limit 50

# 递归列出所有文件
r2-drive ls --all
```

### 删除文件

```bash
# 删除单个文件
r2-drive rm file.txt

# 删除多个文件
r2-drive rm file1.txt file2.txt

# 删除整个目录（递归）
r2-drive rm documents/ --recursive

# 强制删除，不提示
r2-drive rm file.txt --force
```

### 同步目录

```bash
# 同步本地目录到云端
r2-drive sync ./local-folder/ remote-backup/

# 同步并删除云端多余的文件
r2-drive sync ./local-folder/ remote-backup/ --delete
```

### 搜索文件

```bash
# 搜索文件名包含 "report" 的文件
r2-drive search report

# 在指定路径下搜索
r2-drive search report --prefix documents/

# 限制结果数量
r2-drive search report --limit 10
```

### 生成访问链接

```bash
# 生成签名链接（默认1小时有效）
r2-drive url remote-file.txt

# 设置有效期（秒）
r2-drive url remote-file.txt --expires 86400

# 生成公开链接（需配置 public_url）
r2-drive url remote-file.txt --public
```

### 分享文件

```bash
# 生成分享链接（默认7天有效）
r2-drive share remote-file.txt

# 设置有效期（秒）
r2-drive share remote-file.txt --expires 604800
```

### 查看存储信息

```bash
# 查看存储桶统计
r2-drive info

# 以 JSON 格式输出
r2-drive info --format json

# 以 CSV 格式输出
r2-drive info --format csv
```

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

## 高级用法

### 批量操作

```bash
# 批量上传
r2-drive upload *.pdf

# 批量删除
r2-drive rm temp/*.txt --force

# 批量下载
for f in $(r2-drive ls --prefix data/ | awk '{print $1}'); do
    r2-drive download "$f" --output ./data/
done
```

### 定时备份

```bash
# 每天备份数据库
0 2 * * * cd /path/to/project && r2-drive sync ./data/ backup/$(date +\%Y\%m\%d)/
```

### 与 Hermes Agent 集成

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
r2-drive ls --limit 1
```

### 权限问题

确保 R2 API 令牌有以下权限：
- `com.cloudflare.api.account.storage.bucket.read`
- `com.cloudflare.api.account.storage.bucket.write`

### 上传大文件

对于大文件，建议：
1. 增加并发数：`--workers 8`
2. 使用分片上传（自动）
3. 检查网络连接

## 开发

### 项目结构

```
r2-drive/
├── r2_drive/
│   ├── __init__.py
│   ├── cli.py          # 主 CLI 命令
│   └── config.py       # 配置工具
├── requirements.txt
├── setup.py
└── README.md
```

### 添加新命令

1. 在 `cli.py` 中添加新函数
2. 使用 `@cli.command()` 装饰器
3. 添加参数和选项

### 运行测试

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 相关项目

- [Hermes Agent](https://github.com/yourusername/hermes-agent) - AI 助手
- [Cloudflare R2](https://developers.cloudflare.com/r2/) - 对象存储服务
