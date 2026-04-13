#!/usr/bin/env python3
"""
R2 Drive 连接测试脚本

使用方法:
    python test_connection.py
"""

import json
import sys
from pathlib import Path
from rich.console import Console

console = Console()

CONFIG_DIR = Path.home() / ".config" / "r2-drive"
CONFIG_FILE = CONFIG_DIR / "config.json"


def test_connection():
    """测试 R2 连接"""
    console.print("[bold cyan]🔍 R2 Drive 连接测试[/bold cyan]\n")
    
    # 检查配置文件
    if not CONFIG_FILE.exists():
        console.print("[red]❌ 配置文件不存在[/red]")
        console.print(f"请先运行: python -m r2_drive.config")
        return False
    
    # 加载配置
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    except Exception as e:
        console.print(f"[red]❌ 读取配置失败: {e}[/red]")
        return False
    
    # 检查必要字段
    required_fields = ["account_id", "access_key_id", "secret_access_key", "bucket_name"]
    for field in required_fields:
        if field not in config or not config[field]:
            console.print(f"[red]❌ 缺少配置项: {field}[/red]")
            return False
    
    console.print("[green]✅ 配置文件检查通过[/green]")
    
    # 测试 boto3 导入
    try:
        import boto3
        from botocore.config import Config
        console.print("[green]✅ boto3 导入成功[/green]")
    except ImportError:
        console.print("[red]❌ boto3 未安装[/red]")
        console.print("请运行: pip install boto3")
        return False
    
    # 测试 R2 连接
    console.print("\n[cyan]📡 测试 R2 连接...[/cyan]")
    
    try:
        account_id = config["account_id"]
        endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
        
        client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=config["access_key_id"],
            aws_secret_access_key=config["secret_access_key"],
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"}
            ),
            region_name="auto"
        )
        
        # 测试列出对象
        bucket = config["bucket_name"]
        response = client.list_objects_v2(Bucket=bucket, MaxKeys=1)
        
        console.print(f"[green]✅ 连接成功！[/green]")
        console.print(f"  存储桶: {bucket}")
        console.print(f"  Endpoint: {endpoint_url}")
        
        # 显示对象数量
        if "Contents" in response:
            console.print(f"  包含文件: 是")
        else:
            console.print(f"  包含文件: 空")
        
        return True
        
    except client.exceptions.NoSuchBucket:
        console.print(f"[red]❌ 存储桶不存在: {bucket}[/red]")
        return False
    except client.exceptions.AccessDenied:
        console.print("[red]❌ 访问被拒绝，请检查凭证权限[/red]")
        return False
    except Exception as e:
        console.print(f"[red]❌ 连接失败: {e}[/red]")
        return False


if __name__ == "__main__":
    success = test_connection()
    
    if success:
        console.print("\n[green]🎉 所有测试通过！[/green]")
        console.print("\n现在可以使用 r2-drive 命令了:")
        console.print("  r2-drive --help")
    else:
        console.print("\n[red]❌ 测试失败[/red]")
        console.print("\n故障排除:")
        console.print("1. 检查配置文件: ~/.config/r2-drive/config.json")
        console.print("2. 确认 R2 凭证正确")
        console.print("3. 确认存储桶存在")
        console.print("4. 检查网络连接")
        sys.exit(1)
