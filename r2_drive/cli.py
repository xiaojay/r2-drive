#!/usr/bin/env python3
"""
R2 Drive - Cloudflare R2 网盘 CLI 工具

使用方法:
    r2-drive upload <file> [file2 ...] [--path remote_path]
    r2-drive download <remote_file> [--output local_path]
    r2-drive ls [--prefix path] [--limit N]
    r2-drive rm <remote_file> [file2 ...]
    r2-drive sync <local_dir> <remote_prefix>
    r2-drive url <remote_file> [--expires N]
"""

import os
import sys
import json
import click
import boto3
from botocore.config import Config
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import mimetypes
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import print as rprint

# 配置文件路径
CONFIG_DIR = Path.home() / ".config" / "r2-drive"
CONFIG_FILE = CONFIG_DIR / "config.json"

console = Console()


def load_config() -> dict:
    """加载配置文件"""
    if not CONFIG_FILE.exists():
        console.print("[red]❌ 配置文件不存在[/red]")
        console.print(f"请创建配置文件: {CONFIG_FILE}")
        console.print("示例配置:")
        console.print("""
{
    "account_id": "your_account_id",
    "access_key_id": "your_access_key_id",
    "secret_access_key": "your_secret_access_key",
    "bucket_name": "your_bucket_name",
    "public_url": "https://your-bucket.r2.dev"  # 可选，用于生成公开访问链接
}
        """)
        sys.exit(1)
    
    with open(CONFIG_FILE) as f:
        return json.load(f)


def get_r2_client(config: dict):
    """创建 R2 客户端（S3 兼容）"""
    account_id = config["account_id"]
    access_key = config["access_key_id"]
    secret_key = config["secret_access_key"]
    
    endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
    
    return boto3.client(
        "s2",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"}
        ),
        region_name="auto"
    )


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_time(iso_time: str) -> str:
    """格式化时间"""
    if not iso_time:
        return "-"
    dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
    return dt.strftime("%Y-%m-%d %H:%M")


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """R2 Drive - Cloudflare R2 网盘 CLI 工具"""
    pass


@cli.command()
@click.argument("files", nargs=-1, required=True)
@click.option("--path", "-p", default="", help="远程路径前缀")
@click.option("--public", is_flag=True, help="设置为公开访问")
@click.option("--workers", "-w", default=4, help="并发上传数")
def upload(files: tuple, path: str, public: bool, workers: int):
    """上传文件到 R2"""
    config = load_config()
    client = get_r2_client(config)
    bucket = config["bucket_name"]
    
    file_list = []
    for f in files:
        p = Path(f)
        if p.is_dir():
            file_list.extend(p.rglob("*"))
        elif p.is_file():
            file_list.append(p)
        else:
            console.print(f"[yellow]⚠️ 跳过: {f} (不存在)[/yellow]")
    
    if not file_list:
        console.print("[red]❌ 没有找到可上传的文件[/red]")
        return
    
    console.print(f"[cyan]📤 准备上传 {len(file_list)} 个文件到 {path or '/'}[/cyan]")
    
    def upload_single(local_path: Path) -> tuple:
        """上传单个文件"""
        try:
            # 计算远程 key
            rel_path = local_path.relative_to(Path(files[0]).parent) if Path(files[0]).is_dir() else local_path.name
            remote_key = f"{path}/{rel_path}" if path else str(rel_path)
            remote_key = remote_key.replace("//", "/").lstrip("/")
            
            # 检测内容类型
            content_type = mimetypes.guess_type(str(local_path))[0] or "application/octet-stream"
            
            # 上传参数
            extra_args = {}
            if public:
                extra_args["ACL"] = "public-read"
            
            # 上传
            client.upload_file(
                str(local_path),
                bucket,
                remote_key,
                ExtraArgs=extra_args
            )
            
            return (True, str(local_path), remote_key, local_path.stat().st_size)
        except Exception as e:
            return (False, str(local_path), str(e), 0)
    
    # 并发上传
    success_count = 0
    fail_count = 0
    total_size = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("上传中...", total=len(file_list))
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(upload_single, f): f for f in file_list}
            
            for future in as_completed(futures):
                success, path_str, result, size = future.result()
                if success:
                    success_count += 1
                    total_size += size
                    progress.console.print(f"  ✅ {path_str} → {result}")
                else:
                    fail_count += 1
                    progress.console.print(f"  ❌ {path_str}: {result}")
                progress.advance(task)
    
    console.print(f"\n[green]✅ 上传完成: {success_count} 成功, {fail_count} 失败, 总大小: {format_size(total_size)}[/green]")


@cli.command()
@click.argument("remote_file")
@click.option("--output", "-o", help="本地保存路径")
@click.option("--force", "-f", is_flag=True, help="覆盖已存在的文件")
def download(remote_file: str, output: str, force: bool):
    """从 R2 下载文件"""
    config = load_config()
    client = get_r2_client(config)
    bucket = config["bucket_name"]
    
    # 确定本地路径
    local_path = output or Path(remote_file).name
    
    if Path(local_path).exists() and not force:
        console.print(f"[yellow]⚠️ 文件已存在: {local_path} (使用 -f 覆盖)[/yellow]")
        return
    
    console.print(f"[cyan]📥 下载 {remote_file} → {local_path}[/cyan]")
    
    try:
        # 确保目录存在
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 获取文件信息
        head = client.head_object(Bucket=bucket, Key=remote_file)
        file_size = head["ContentLength"]
        
        # 下载
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("下载中...", total=file_size)
            
            def callback(bytes_transferred):
                progress.update(task, completed=bytes_transferred)
            
            client.download_file(bucket, remote_file, str(local_path), Callback=callback)
        
        console.print(f"[green]✅ 下载完成: {format_size(file_size)}[/green]")
    except client.exceptions.NoSuchKey:
        console.print(f"[red]❌ 文件不存在: {remote_file}[/red]")
    except Exception as e:
        console.print(f"[red]❌ 下载失败: {e}[/red]")


@cli.command("ls")
@click.option("--prefix", "-p", default="", help="路径前缀过滤")
@click.option("--limit", "-n", default=100, help="显示数量限制")
@click.option("--all", "-a", is_flag=True, help="显示所有文件（递归）")
@click.option("--human", is_flag=True, default=True, help="人类可读的文件大小")
def list_files(prefix: str, limit: int, all: bool, human: bool):
    """列出 R2 上的文件"""
    config = load_config()
    client = get_r2_client(config)
    bucket = config["bucket_name"]
    
    console.print(f"[cyan]📂 列出文件: {prefix or '/'}[/cyan]\n")
    
    try:
        # 列出对象
        paginator = client.get_paginator("list_objects_v2")
        pages = paginator.paginate(
            Bucket=bucket,
            Prefix=prefix,
            PaginationConfig={"PageSize": limit if not all else 1000}
        )
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("文件名", style="white")
        table.add_column("大小", justify="right", style="green")
        table.add_column("修改时间", style="yellow")
        table.add_column("类型", style="blue")
        
        count = 0
        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                size = obj["Size"]
                modified = obj.get("LastModified", "")
                
                # 检测类型
                content_type = mimetypes.guess_type(key)[0] or "-"
                
                # 格式化显示
                display_key = key
                if not all and "/" in key:
                    parts = key.split("/")
                    if len(parts) > 2:
                        display_key = f".../{'/'.join(parts[-2:])}"
                
                size_str = format_size(size) if human else str(size)
                time_str = format_time(str(modified)) if modified else "-"
                
                table.add_row(display_key, size_str, time_str, content_type)
                count += 1
                
                if count >= limit:
                    break
            
            if count >= limit:
                break
        
        if count == 0:
            console.print("[yellow]📭 没有找到文件[/yellow]")
        else:
            console.print(table)
            console.print(f"\n[green]共 {count} 个文件[/green]")
            
    except Exception as e:
        console.print(f"[red]❌ 列出文件失败: {e}[/red]")


@cli.command()
@click.argument("files", nargs=-1, required=True)
@click.option("--recursive", "-r", is_flag=True, help="递归删除目录")
@click.option("--force", "-f", is_flag=True, help="强制删除，不提示")
def rm(files: tuple, recursive: bool, force: bool):
    """删除 R2 上的文件"""
    config = load_config()
    client = get_r2_client(config)
    bucket = config["bucket_name"]
    
    for file_path in files:
        try:
            # 如果是目录（以 / 结尾），列出所有子文件
            if file_path.endswith("/"):
                if not recursive and not force:
                    if not click.confirm(f"确定要删除目录 {file_path} 吗？"):
                        continue
                
                # 列出目录下所有文件
                paginator = client.get_paginator("list_objects_v2")
                pages = paginator.paginate(Bucket=bucket, Prefix=file_path)
                
                objects_to_delete = []
                for page in pages:
                    for obj in page.get("Contents", []):
                        objects_to_delete.append({"Key": obj["Key"]})
                
                if not objects_to_delete:
                    console.print(f"[yellow]⚠️ 目录为空: {file_path}[/yellow]")
                    continue
                
                # 批量删除
                if not force:
                    if not click.confirm(f"将删除 {len(objects_to_delete)} 个文件，确定吗？"):
                        continue
                
                for i in range(0, len(objects_to_delete), 1000):
                    batch = objects_to_delete[i:i+1000]
                    client.delete_objects(
                        Bucket=bucket,
                        Delete={"Objects": batch}
                    )
                
                console.print(f"[green]✅ 已删除 {len(objects_to_delete)} 个文件[/green]")
            else:
                # 删除单个文件
                if not force:
                    if not click.confirm(f"确定要删除 {file_path} 吗？"):
                        continue
                
                client.delete_object(Bucket=bucket, Key=file_path)
                console.print(f"[green]✅ 已删除: {file_path}[/green]")
                
        except Exception as e:
            console.print(f"[red]❌ 删除失败 {file_path}: {e}[/red]")


@cli.command()
@click.argument("local_dir")
@click.argument("remote_prefix")
@click.option("--delete", is_flag=True, help="删除远程多余的文件")
@click.option("--workers", "-w", default=4, help="并发数")
def sync(local_dir: str, remote_prefix: str, delete: bool, workers: int):
    """同步本地目录到 R2"""
    config = load_config()
    client = get_r2_client(config)
    bucket = config["bucket_name"]
    
    local_path = Path(local_dir)
    if not local_path.is_dir():
        console.print(f"[red]❌ 目录不存在: {local_dir}[/red]")
        return
    
    # 获取本地文件列表
    local_files = {}
    for f in local_path.rglob("*"):
        if f.is_file():
            rel = f.relative_to(local_path)
            remote_key = f"{remote_prefix}/{rel}".replace("//", "/").lstrip("/")
            local_files[remote_key] = f
    
    # 获取远程文件列表
    remote_files = set()
    paginator = client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=remote_prefix)
    
    for page in pages:
        for obj in page.get("Contents", []):
            remote_files.add(obj["Key"])
    
    # 计算差异
    to_upload = []
    to_delete = []
    
    for remote_key, local_file in local_files.items():
        # 简单比较：如果远程不存在则上传
        if remote_key not in remote_files:
            to_upload.append((local_file, remote_key))
    
    if delete:
        for remote_key in remote_files:
            if remote_key not in local_files:
                to_delete.append(remote_key)
    
    # 执行同步
    console.print(f"[cyan]🔄 同步 {local_dir} → {remote_prefix}[/cyan]")
    console.print(f"  本地文件: {len(local_files)}")
    console.print(f"  远程文件: {len(remote_files)}")
    console.print(f"  待上传: {len(to_upload)}")
    console.print(f"  待删除: {len(to_delete)}")
    
    if not to_upload and not to_delete:
        console.print("[green]✅ 已是最新，无需同步[/green]")
        return
    
    # 上传
    if to_upload:
        console.print(f"\n[cyan]📤 上传 {len(to_upload)} 个文件...[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("上传中...", total=len(to_upload))
            
            with ThreadPoolExecutor(max_workers=workers) as executor:
                def upload_file(item):
                    local_file, remote_key = item
                    try:
                        content_type = mimetypes.guess_type(str(local_file))[0] or "application/octet-stream"
                        client.upload_file(str(local_file), bucket, remote_key)
                        return (True, str(local_file), remote_key)
                    except Exception as e:
                        return (False, str(local_file), str(e))
                
                futures = [executor.submit(upload_file, item) for item in to_upload]
                
                for future in as_completed(futures):
                    success, path_str, result = future.result()
                    if success:
                        progress.console.print(f"  ✅ {path_str}")
                    else:
                        progress.console.print(f"  ❌ {path_str}: {result}")
                    progress.advance(task)
    
    # 删除
    if to_delete:
        console.print(f"\n[cyan]🗑️ 删除 {len(to_delete)} 个远程文件...[/cyan]")
        
        for i in range(0, len(to_delete), 1000):
            batch = [{"Key": k} for k in to_delete[i:i+1000]]
            client.delete_objects(Bucket=bucket, Delete={"Objects": batch})
        
        console.print(f"[green]✅ 已删除 {len(to_delete)} 个文件[/green]")
    
    console.print(f"\n[green]✅ 同步完成[/green]")


@cli.command()
@click.argument("remote_file")
@click.option("--expires", "-e", default=3600, help="链接过期时间（秒）")
@click.option("--public", is_flag=True, help="生成公开访问链接（需配置 public_url）")
def url(remote_file: str, expires: int, public: bool):
    """生成文件访问链接"""
    config = load_config()
    client = get_r2_client(config)
    bucket = config["bucket_name"]
    
    try:
        if public:
            # 使用公开 URL
            public_url = config.get("public_url")
            if not public_url:
                console.print("[red]❌ 未配置 public_url[/red]")
                return
            
            link = f"{public_url}/{remote_file}"
        else:
            # 生成签名 URL
            link = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": remote_file},
                ExpiresIn=expires
            )
        
        console.print(f"[green]🔗 访问链接:[/green]")
        console.print(f"   {link}")
        console.print(f"\n[dim]有效期: {expires} 秒[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ 生成链接失败: {e}[/red]")


@cli.command()
@click.option("--prefix", "-p", default="", help="路径前缀")
@click.option("--format", "-f", "output_format", type=click.Choice(["table", "json", "csv"]), default="table")
def info(prefix: str, output_format: str):
    """显示存储桶信息和统计"""
    config = load_config()
    client = get_r2_client(config)
    bucket = config["bucket_name"]
    
    console.print(f"[cyan]📊 存储桶信息: {bucket}[/cyan]\n")
    
    try:
        # 统计文件
        total_size = 0
        file_count = 0
        file_types = {}
        
        paginator = client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        
        for page in pages:
            for obj in page.get("Contents", []):
                file_count += 1
                total_size += obj["Size"]
                
                # 统计文件类型
                ext = Path(obj["Key"]).suffix.lower() or "无扩展名"
                file_types[ext] = file_types.get(ext, 0) + 1
        
        # 显示统计
        if output_format == "table":
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("统计项", style="white")
            table.add_column("值", justify="right", style="green")
            
            table.add_row("文件数量", str(file_count))
            table.add_row("总大小", format_size(total_size))
            table.add_row("平均大小", format_size(total_size / file_count) if file_count else "0 B")
            
            console.print(table)
            
            # 文件类型统计
            if file_types:
                console.print("\n[bold]文件类型分布:[/bold]")
                type_table = Table(show_header=True, header_style="bold cyan")
                type_table.add_column("类型", style="white")
                type_table.add_column("数量", justify="right", style="green")
                
                for ext, count in sorted(file_types.items(), key=lambda x: -x[1])[:10]:
                    type_table.add_row(ext, str(count))
                
                console.print(type_table)
                
        elif output_format == "json":
            data = {
                "bucket": bucket,
                "prefix": prefix,
                "file_count": file_count,
                "total_size": total_size,
                "file_types": file_types
            }
            console.print_json(json.dumps(data, indent=2))
            
        elif output_format == "csv":
            console.print("metric,value")
            console.print(f"file_count,{file_count}")
            console.print(f"total_size_bytes,{total_size}")
            for ext, count in file_types.items():
                console.print(f"type_{ext},{count}")
                
    except Exception as e:
        console.print(f"[red]❌ 获取信息失败: {e}[/red]")


@cli.command()
@click.argument("query")
@click.option("--prefix", "-p", default="", help="搜索路径前缀")
@click.option("--limit", "-n", default=20, help="结果数量限制")
def search(query: str, prefix: str, limit: int):
    """搜索文件名"""
    config = load_config()
    client = get_r2_client(config)
    bucket = config["bucket_name"]
    
    console.print(f"[cyan]🔍 搜索: {query}[/cyan]\n")
    
    try:
        results = []
        paginator = client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        
        for page in pages:
            for obj in page.get("Contents", []):
                if query.lower() in obj["Key"].lower():
                    results.append(obj)
                    if len(results) >= limit:
                        break
            if len(results) >= limit:
                break
        
        if not results:
            console.print("[yellow]📭 未找到匹配文件[/yellow]")
            return
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("文件名", style="white")
        table.add_column("大小", justify="right", style="green")
        table.add_column("修改时间", style="yellow")
        
        for obj in results:
            table.add_row(
                obj["Key"],
                format_size(obj["Size"]),
                format_time(str(obj.get("LastModified", "")))
            )
        
        console.print(table)
        console.print(f"\n[green]找到 {len(results)} 个文件[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ 搜索失败: {e}[/red]")


@cli.command()
@click.argument("remote_file")
@click.option("--expires", "-e", default=604800, help="分享链接有效期（秒），默认7天")
def share(remote_file: str, expires: int):
    """生成文件分享链接"""
    config = load_config()
    client = get_r2_client(config)
    bucket = config["bucket_name"]
    
    try:
        # 检查文件是否存在
        client.head_object(Bucket=bucket, Key=remote_file)
        
        # 生成签名 URL
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": remote_file},
            ExpiresIn=expires
        )
        
        # 获取文件信息
        file_name = Path(remote_file).name
        expires_days = expires // 86400
        
        console.print(f"[green]📤 分享链接已生成[/green]\n")
        console.print(f"  文件: {file_name}")
        console.print(f"  路径: {remote_file}")
        console.print(f"  有效期: {expires_days} 天")
        console.print(f"\n🔗 链接:")
        console.print(f"  {url}")
        
        # 生成短链接信息（显示部分）
        console.print(f"\n[dim]提示: 可以复制链接分享给他人[/dim]")
        
    except client.exceptions.NoSuchKey:
        console.print(f"[red]❌ 文件不存在: {remote_file}[/red]")
    except Exception as e:
        console.print(f"[red]❌ 生成分享链接失败: {e}[/red]")


@cli.command()
@click.argument("remote_path")
@click.option("--output", "-o", default=".", help="下载保存目录")
@click.option("--workers", "-w", default=4, help="并发下载数")
def pull(remote_path: str, output: str, workers: int):
    """下载整个目录"""
    config = load_config()
    client = get_r2_client(config)
    bucket = config["bucket_name"]
    
    # 确保路径以 / 结尾
    if not remote_path.endswith("/"):
        remote_path += "/"
    
    console.print(f"[cyan]📥 下载目录: {remote_path} → {output}[/cyan]")
    
    try:
        # 列出所有文件
        paginator = client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=remote_path)
        
        files_to_download = []
        for page in pages:
            for obj in page.get("Contents", []):
                # 跳过目录本身
                if obj["Key"] == remote_path:
                    continue
                files_to_download.append(obj)
        
        if not files_to_download:
            console.print("[yellow]📭 目录为空[/yellow]")
            return
        
        console.print(f"  找到 {len(files_to_download)} 个文件")
        
        # 下载
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("下载中...", total=len(files_to_download))
            
            with ThreadPoolExecutor(max_workers=workers) as executor:
                def download_file(obj):
                    remote_key = obj["Key"]
                    # 计算本地路径
                    rel_path = remote_key[len(remote_path):]
                    local_file = output_path / rel_path
                    local_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    try:
                        client.download_file(bucket, remote_key, str(local_file))
                        return (True, remote_key, str(local_file))
                    except Exception as e:
                        return (False, remote_key, str(e))
                
                futures = [executor.submit(download_file, obj) for obj in files_to_download]
                
                for future in as_completed(futures):
                    success, remote_key, result = future.result()
                    if success:
                        progress.console.print(f"  ✅ {remote_key}")
                    else:
                        progress.console.print(f"  ❌ {remote_key}: {result}")
                    progress.advance(task)
        
        console.print(f"\n[green]✅ 下载完成: {len(files_to_download)} 个文件[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ 下载失败: {e}[/red]")


@cli.command()
@click.option("--host", "-h", default="127.0.0.1", help="监听地址")
@click.option("--port", "-p", default=5000, help="监听端口")
@click.option("--debug", is_flag=True, help="调试模式")
def web(host: str, port: int, debug: bool):
    """启动 Web 界面"""
    try:
        from .web import run_web_server
        run_web_server(host=host, port=port, debug=debug)
    except ImportError:
        console.print("[red]❌ Web 模块加载失败[/red]")
        console.print("请确保已安装 Flask: pip install flask")
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Web 服务器已停止[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ 启动失败: {e}[/red]")


if __name__ == "__main__":
    cli()
