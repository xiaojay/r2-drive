"""
R2 Drive Web 界面

使用方法:
    r2-drive web                    # 启动 Web 服务器（默认 5000 端口）
    r2-drive web --port 8080        # 指定端口
    r2-drive web --host 0.0.0.0     # 允许外部访问
"""

import os
import json
import mimetypes
from pathlib import Path
from datetime import datetime
from functools import wraps

import boto3
from botocore.config import Config
from flask import (
    Flask, render_template, request, jsonify, send_file,
    redirect, url_for, abort, Response
)
from werkzeug.utils import secure_filename
import io

# 配置
CONFIG_DIR = Path.home() / ".config" / "r2-drive"
CONFIG_FILE = CONFIG_DIR / "config.json"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB 上传限制
app.config["SECRET_KEY"] = os.urandom(24)

# 全局 R2 客户端
_r2_client = None
_r2_config = None
_bucket_name = None


def load_config():
    """加载配置文件"""
    global _r2_config, _bucket_name
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"配置文件不存在: {CONFIG_FILE}")
    
    with open(CONFIG_FILE) as f:
        _r2_config = json.load(f)
    
    _bucket_name = _r2_config["bucket_name"]
    return _r2_config


def get_r2_client():
    """获取 R2 客户端"""
    global _r2_client
    if _r2_client is None:
        config = _r2_config or load_config()
        account_id = config["account_id"]
        endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
        
        _r2_client = boto3.client(
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
    return _r2_client


def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_time(dt):
    """格式化时间"""
    if not dt:
        return "-"
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    return dt.strftime("%Y-%m-%d %H:%M")


def get_file_icon(key, is_folder=False):
    """获取文件图标"""
    if is_folder:
        return "📁"
    
    ext = Path(key).suffix.lower()
    icons = {
        ".pdf": "📄",
        ".doc": "📝", ".docx": "📝",
        ".xls": "📊", ".xlsx": "📊",
        ".ppt": "📽️", ".pptx": "📽️",
        ".jpg": "🖼️", ".jpeg": "🖼️", ".png": "🖼️", ".gif": "🖼️", ".webp": "🖼️",
        ".mp3": "🎵", ".wav": "🎵", ".ogg": "🎵",
        ".mp4": "🎬", ".avi": "🎬", ".mov": "🎬", ".mkv": "🎬",
        ".zip": "📦", ".rar": "📦", ".7z": "📦", ".tar": "📦", ".gz": "📦",
        ".py": "🐍",
        ".js": "📜", ".ts": "📜",
        ".html": "🌐", ".css": "🌐",
        ".json": "📋", ".xml": "📋", ".yaml": "📋", ".yml": "📋",
        ".txt": "📝", ".md": "📝",
        ".exe": "⚙️", ".sh": "⚙️",
    }
    return icons.get(ext, "📄")


def list_objects(prefix="", delimiter="/"):
    """列出对象"""
    client = get_r2_client()
    
    # 获取文件夹
    folders = []
    files = []
    
    paginator = client.get_paginator("list_objects_v2")
    pages = paginator.paginate(
        Bucket=_bucket_name,
        Prefix=prefix,
        Delimiter=delimiter
    )
    
    for page in pages:
        # 文件夹
        for prefix_obj in page.get("CommonPrefixes", []):
            folder_key = prefix_obj["Prefix"]
            folder_name = folder_key.rstrip("/").split("/")[-1]
            folders.append({
                "name": folder_name,
                "key": folder_key,
                "is_folder": True,
                "icon": "📁"
            })
        
        # 文件
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key == prefix:  # 跳过目录本身
                continue
            
            file_name = key.rstrip("/").split("/")[-1]
            files.append({
                "name": file_name,
                "key": key,
                "size": obj["Size"],
                "size_display": format_size(obj["Size"]),
                "modified": format_time(obj.get("LastModified")),
                "modified_iso": str(obj.get("LastModified", "")),
                "is_folder": False,
                "icon": get_file_icon(key),
                "content_type": mimetypes.guess_type(key)[0] or "application/octet-stream"
            })
    
    return folders + files


# ==================== Web 路由 ====================

@app.route("/")
def index():
    """首页 - 文件列表"""
    prefix = request.args.get("prefix", "")
    
    # 获取父目录
    parent = ""
    if prefix:
        parts = prefix.rstrip("/").split("/")
        if len(parts) > 1:
            parent = "/".join(parts[:-1]) + "/"
    
    try:
        items = list_objects(prefix)
        return render_template(
            "index.html",
            items=items,
            prefix=prefix,
            parent=parent,
            format_size=format_size
        )
    except Exception as e:
        return render_template("error.html", error=str(e)), 500


@app.route("/api/list")
def api_list():
    """API: 列出文件"""
    prefix = request.args.get("prefix", "")
    search = request.args.get("search", "")
    
    try:
        if search:
            # 搜索模式
            client = get_r2_client()
            items = []
            
            paginator = client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=_bucket_name)
            
            for page in pages:
                for obj in page.get("Contents", []):
                    if search.lower() in obj["Key"].lower():
                        items.append({
                            "name": obj["Key"].split("/")[-1],
                            "key": obj["Key"],
                            "size": obj["Size"],
                            "size_display": format_size(obj["Size"]),
                            "modified": format_time(obj.get("LastModified")),
                            "is_folder": False,
                            "icon": get_file_icon(obj["Key"])
                        })
        else:
            items = list_objects(prefix)
        
        return jsonify({"success": True, "items": items})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """API: 上传文件"""
    if "files" not in request.files:
        return jsonify({"success": False, "error": "没有选择文件"}), 400
    
    files = request.files.getlist("files")
    prefix = request.form.get("prefix", "")
    
    client = get_r2_client()
    uploaded = []
    errors = []
    
    for file in files:
        if file.filename == "":
            continue
        
        try:
            filename = secure_filename(file.filename)
            key = f"{prefix}{filename}".replace("//", "/").lstrip("/")
            
            # 检测内容类型
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            
            # 上传
            client.upload_fileobj(
                file,
                _bucket_name,
                key,
                ExtraArgs={"ContentType": content_type}
            )
            
            uploaded.append({
                "name": filename,
                "key": key,
                "size_display": format_size(file.content_length or 0)
            })
        except Exception as e:
            errors.append({"file": file.filename, "error": str(e)})
    
    return jsonify({
        "success": len(errors) == 0,
        "uploaded": uploaded,
        "errors": errors
    })


@app.route("/api/upload-folder", methods=["POST"])
def api_upload_folder():
    """API: 上传文件夹"""
    if "files" not in request.files:
        return jsonify({"success": False, "error": "没有选择文件"}), 400
    
    files = request.files.getlist("files")
    paths = request.form.getlist("paths")
    prefix = request.form.get("prefix", "")
    
    client = get_r2_client()
    uploaded = []
    errors = []
    
    for file, path in zip(files, paths):
        if file.filename == "":
            continue
        
        try:
            # 保持原始目录结构
            key = f"{prefix}{path}".replace("//", "/").lstrip("/")
            
            content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
            
            client.upload_fileobj(
                file,
                _bucket_name,
                key,
                ExtraArgs={"ContentType": content_type}
            )
            
            uploaded.append({"path": path, "key": key})
        except Exception as e:
            errors.append({"path": path, "error": str(e)})
    
    return jsonify({
        "success": len(errors) == 0,
        "uploaded": len(uploaded),
        "errors": errors
    })


@app.route("/api/download/<path:key>")
def api_download(key):
    """API: 下载文件"""
    try:
        client = get_r2_client()
        
        # 生成签名 URL
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": _bucket_name, "Key": key},
            ExpiresIn=3600
        )
        
        return redirect(url)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/delete", methods=["POST"])
def api_delete():
    """API: 删除文件"""
    data = request.get_json()
    keys = data.get("keys", [])
    
    if not keys:
        return jsonify({"success": False, "error": "没有指定文件"}), 400
    
    client = get_r2_client()
    deleted = []
    errors = []
    
    try:
        # 批量删除
        objects = [{"Key": key} for key in keys]
        
        for i in range(0, len(objects), 1000):
            batch = objects[i:i+1000]
            response = client.delete_objects(
                Bucket=_bucket_name,
                Delete={"Objects": batch}
            )
            
            for deleted_obj in response.get("Deleted", []):
                deleted.append(deleted_obj["Key"])
        
        return jsonify({
            "success": True,
            "deleted": deleted
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/new-folder", methods=["POST"])
def api_new_folder():
    """API: 创建新文件夹"""
    data = request.get_json()
    path = data.get("path", "")
    
    if not path:
        return jsonify({"success": False, "error": "没有指定路径"}), 400
    
    # 确保路径以 / 结尾
    if not path.endswith("/"):
        path += "/"
    
    client = get_r2_client()
    
    try:
        # 创建空对象作为文件夹标记
        client.put_object(
            Bucket=_bucket_name,
            Key=path,
            Body=b""
        )
        
        return jsonify({"success": True, "path": path})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/rename", methods=["POST"])
def api_rename():
    """API: 重命名/移动文件"""
    data = request.get_json()
    old_key = data.get("old_key", "")
    new_key = data.get("new_key", "")
    
    if not old_key or not new_key:
        return jsonify({"success": False, "error": "缺少参数"}), 400
    
    client = get_r2_client()
    
    try:
        # 复制
        client.copy_object(
            Bucket=_bucket_name,
            CopySource={"Bucket": _bucket_name, "Key": old_key},
            Key=new_key
        )
        
        # 删除原文件
        client.delete_object(Bucket=_bucket_name, Key=old_key)
        
        return jsonify({"success": True, "old_key": old_key, "new_key": new_key})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/share/<path:key>")
def api_share(key):
    """API: 生成分享链接"""
    expires = int(request.args.get("expires", 604800))  # 默认 7 天
    
    client = get_r2_client()
    
    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": _bucket_name, "Key": key},
            ExpiresIn=expires
        )
        
        return jsonify({
            "success": True,
            "url": url,
            "expires_in": expires
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/info")
def api_info():
    """API: 获取存储桶信息"""
    client = get_r2_client()
    
    try:
        total_size = 0
        file_count = 0
        file_types = {}
        
        paginator = client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=_bucket_name)
        
        for page in pages:
            for obj in page.get("Contents", []):
                file_count += 1
                total_size += obj["Size"]
                
                ext = Path(obj["Key"]).suffix.lower() or "无扩展名"
                file_types[ext] = file_types.get(ext, 0) + 1
        
        return jsonify({
            "success": True,
            "bucket": _bucket_name,
            "file_count": file_count,
            "total_size": total_size,
            "total_size_display": format_size(total_size),
            "file_types": file_types
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/preview/<path:key>")
def preview(key):
    """预览文件"""
    client = get_r2_client()
    
    try:
        # 获取文件内容
        response = client.get_object(Bucket=_bucket_name, Key=key)
        content = response["Body"].read()
        content_type = response["ContentType"]
        
        # 根据类型处理
        if content_type.startswith("text/") or content_type in [
            "application/json", "application/javascript", "application/xml"
        ]:
            # 文本文件
            try:
                text = content.decode("utf-8")
            except:
                text = content.decode("latin-1")
            
            return render_template(
                "preview_text.html",
                key=key,
                content=text,
                content_type=content_type
            )
        
        elif content_type.startswith("image/"):
            # 图片
            import base64
            b64 = base64.b64encode(content).decode()
            return render_template(
                "preview_image.html",
                key=key,
                content_type=content_type,
                data=b64
            )
        
        elif content_type == "application/pdf":
            # PDF
            import base64
            b64 = base64.b64encode(content).decode()
            return render_template(
                "preview_pdf.html",
                key=key,
                data=b64
            )
        
        else:
            # 其他类型 - 提供下载
            return redirect(url_for("api_download", key=key))
    
    except Exception as e:
        return render_template("error.html", error=str(e)), 500


# ==================== 启动函数 ====================

def create_app():
    """创建 Flask 应用"""
    # 确保模板目录存在
    template_dir = Path(__file__).parent / "templates"
    static_dir = Path(__file__).parent / "static"
    
    app.template_folder = str(template_dir)
    app.static_folder = str(static_dir)
    
    return app


def run_web_server(host="127.0.0.1", port=5000, debug=False):
    """启动 Web 服务器"""
    try:
        load_config()
        print(f"✅ 配置加载成功")
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return
    
    print(f"🚀 启动 R2 Drive Web 界面")
    print(f"   地址: http://{host}:{port}")
    print(f"   存储桶: {_bucket_name}")
    print(f"\n按 Ctrl+C 停止服务器\n")
    
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_web_server()
