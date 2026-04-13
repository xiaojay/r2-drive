#!/bin/bash
# R2 Drive 安装脚本

set -e

echo "==========================================="
echo "R2 Drive 安装脚本"
echo "==========================================="

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 需要 Python 3.8+"
    exit 1
fi

# 检查 pip
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo "❌ 需要 pip"
    exit 1
fi

echo "✅ Python 环境检查通过"

# 安装依赖
echo ""
echo "📦 安装 R2 Drive..."
pip install -e .

if [ $? -eq 0 ]; then
    echo "✅ R2 Drive 安装成功"
else
    echo "❌ R2 Drive 安装失败"
    exit 1
fi

# 创建配置目录
CONFIG_DIR="$HOME/.config/r2-drive"
mkdir -p "$CONFIG_DIR"

# 检查是否已有配置
if [ -f "$CONFIG_DIR/config.json" ]; then
    echo "✅ 配置文件已存在: $CONFIG_DIR/config.json"
else
    echo ""
    echo "📝 配置 R2 凭证"
    echo "请从 Cloudflare Dashboard 获取 R2 凭证:"
    echo "  路径: R2 → 管理 R2 API 令牌"
    echo ""
    
    # 运行配置向导
    python3 -m r2_drive.config
fi

# 测试安装
echo ""
echo "🧪 测试安装..."
r2-drive --version

if [ $? -eq 0 ]; then
    echo "✅ 安装测试成功"
else
    echo "⚠️  安装测试失败，但 r2-drive 命令可能仍然可用"
fi

# 显示使用说明
echo ""
echo "==========================================="
echo "安装完成！"
echo "==========================================="
echo ""
echo "使用方法:"
echo "  r2-drive --help          # 查看帮助"
echo "  r2-drive upload file.txt # 上传文件"
echo "  r2-drive ls              # 列出文件"
echo "  r2-drive download key    # 下载文件"
echo ""
echo "配置文件位置:"
echo "  $CONFIG_DIR/config.json"
echo ""
echo "如果需要重新配置:"
echo "  python3 -m r2_drive.config"
echo ""
echo "==========================================="
echo "常见问题"
echo "==========================================="
echo ""
echo "1. 如果提示 'command not found':"
echo "   - 确保 pip 安装路径在 PATH 中"
echo "   - 或者使用: python3 -m r2_drive.cli"
echo ""
echo "2. 如果连接失败:"
echo "   - 检查配置文件是否正确"
echo "   - 确认 R2 凭证有效"
echo "   - 测试: r2-drive ls --limit 1"
echo ""
echo "3. 如果权限不足:"
echo "   - 确保 R2 API 令牌有读写权限"
echo ""
