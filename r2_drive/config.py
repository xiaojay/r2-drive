#!/usr/bin/env python3
"""R2 Drive 配置工具"""

import json
import sys
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm

console = Console()

CONFIG_DIR = Path.home() / ".config" / "r2-drive"
CONFIG_FILE = CONFIG_DIR / "config.json"


def init_config():
    """初始化配置文件"""
    console.print("[bold cyan]🚀 R2 Drive 配置向导[/bold cyan]\n")
    
    # 检查是否已存在配置
    if CONFIG_FILE.exists():
        if not Confirm.ask("配置文件已存在，是否覆盖？"):
            console.print("[yellow]已取消[/yellow]")
            return
    
    # 获取配置信息
    console.print("[dim]请从 Cloudflare Dashboard 获取 R2 凭证[/dim]")
    console.print("[dim]路径: R2 → 管理 R2 API 令牌[/dim]\n")
    
    account_id = Prompt.ask("Account ID")
    access_key_id = Prompt.ask("Access Key ID")
    secret_access_key = Prompt.ask("Secret Access Key", password=True)
    bucket_name = Prompt.ask("Bucket Name")
    
    # 可选的公开 URL
    public_url = ""
    if Confirm.ask("是否配置公开访问 URL？（用于生成公开链接）"):
        public_url = Prompt.ask("Public URL", default=f"https://{bucket_name}.r2.dev")
    
    # 保存配置
    config = {
        "account_id": account_id,
        "access_key_id": access_key_id,
        "secret_access_key": secret_access_key,
        "bucket_name": bucket_name,
        "public_url": public_url
    }
    
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    
    # 设置文件权限
    CONFIG_FILE.chmod(0o600)
    
    console.print(f"\n[green]✅ 配置已保存到: {CONFIG_FILE}[/green]")
    console.print("[dim]文件权限已设置为 600（仅当前用户可读写）[/dim]")


def show_config():
    """显示当前配置"""
    if not CONFIG_FILE.exists():
        console.print("[red]❌ 配置文件不存在[/red]")
        return
    
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    
    console.print("[bold cyan]📋 当前配置[/bold cyan]\n")
    
    for key, value in config.items():
        if key == "secret_access_key":
            # 隐藏密钥
            display_value = value[:8] + "..." if len(value) > 8 else "***"
        else:
            display_value = value or "[dim]未设置[/dim]"
        
        console.print(f"  {key}: {display_value}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        show_config()
    else:
        init_config()
