"""发布：写 meta.json / manifest.json，可选上传到媒体服务器。

转码完成的每个视频会在其输出目录生成 meta.json（含媒体服务器播放/封面地址），
并在输出根目录维护一个 manifest.json（所有视频的清单），
供 web 端 sync.php 一次性导入数据库。

上传支持三种方式（在 config.json 的 upload.method 中切换）：
  - "sftp" : 通过 SSH/SFTP 上传（媒体服务器通常没有 FTP，优先用这个）
  - "ftp"  : 传统 FTP 上传（少数仍支持 FTP 的服务器）
  - "none" : 不上传，仅生成本地文件，由你手动上传（面板/SCP 等）
"""
import os
import json
from datetime import datetime


def build_meta(safe, src, media_base, duration, title=None, description=""):
    """根据转码输出构造一条媒体元数据。"""
    base_url = (media_base or "").rstrip("/")

    def url(rel):
        return "%s/%s/%s" % (base_url, safe, rel) if base_url else "%s/%s" % (safe, rel)

    master = url("index.m3u8")
    poster = url("poster.jpg")
    return {
        "base": safe,
        "title": title or safe,
        "description": description or "",
        "duration": round(float(duration or 0), 2),
        "video_url": master,
        "master": master,
        "thumbnail": poster,
        "poster": poster,
        "vtt": url("thumbnails/thumbnails.vtt"),
        "video_type": "application/x-mpegURL",
        "source_file": os.path.basename(src),
        "converted_at": datetime.now().isoformat(timespec="seconds"),
    }


def write_meta(out_dir, meta):
    """把 meta.json 写到视频输出目录。"""
    p = os.path.join(out_dir, "meta.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return p


def append_manifest(output_root, meta):
    """把一条 meta 合并进输出根目录的 manifest.json（按 base 去重）。"""
    p = os.path.join(output_root, "manifest.json")
    items = []
    if os.path.isfile(p):
        try:
            with open(p, encoding="utf-8") as f:
                items = json.load(f)
            if not isinstance(items, list):
                items = []
        except Exception:
            items = []
    items = [it for it in items if it.get("base") != meta.get("base")]
    items.append(meta)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    return p


# --------------------------------------------------------------------------
# 上传器
# --------------------------------------------------------------------------

def make_uploader(upload_cfg):
    """根据配置返回上传器实例，或 None（method=none / 未配置时）。"""
    if not upload_cfg:
        return None
    method = str(upload_cfg.get("method", "none")).lower()
    if method == "sftp":
        return SftpUploader(
            host=upload_cfg.get("host", ""),
            port=int(upload_cfg.get("port", 22) or 22),
            user=upload_cfg.get("user", ""),
            password=upload_cfg.get("password", ""),
            key_file=upload_cfg.get("key_file", ""),
            remote_dir=upload_cfg.get("remote_dir", "/"),
        )
    if method == "ftp":
        return FtpUploader(
            host=upload_cfg.get("host", ""),
            user=upload_cfg.get("user", ""),
            password=upload_cfg.get("password", ""),
            port=int(upload_cfg.get("port", 21) or 21),
            remote_dir=upload_cfg.get("remote_dir", "/"),
        )
    return None


def upload_ready(up):
    """上传器是否可用（已配置主机与用户名）。"""
    if up is None:
        return False
    return bool(getattr(up, "host", None) and getattr(up, "user", None))


class FtpUploader:
    """基于标准库 ftplib 的递归上传器（无需额外依赖）。"""

    def __init__(self, host, user, password, port=21, remote_dir="/", passive=True):
        self.host = host
        self.port = int(port or 21)
        self.user = user
        self.password = password
        self.remote_dir = remote_dir or "/"
        self.passive = passive

    def _connect(self):
        import ftplib
        ftp = ftplib.FTP()
        ftp.connect(self.host, self.port, timeout=30)
        ftp.login(self.user, self.password)
        ftp.set_pasv(self.passive)
        return ftp

    @staticmethod
    def _ensure_remote_dir(ftp, path):
        parts = [p for p in path.replace("\\", "/").split("/") if p]
        cur = ""
        for p in parts:
            cur = cur + "/" + p if cur else p
            try:
                ftp.mkd(cur)
            except Exception:
                pass   # 已存在
        return "/" + "/".join(parts) if parts else "/"

    def upload_dir(self, local_dir, remote_sub=None, log_cb=None):
        """把 local_dir 整个目录上传到 remote_dir[/remote_sub]。"""
        def log(m):
            if log_cb:
                log_cb(m)

        remote_base = self.remote_dir.rstrip("/")
        if remote_sub:
            remote_base = remote_base + "/" + remote_sub.strip("/")

        ftp = self._connect()
        try:
            self._ensure_remote_dir(ftp, remote_base)
            for root, _dirs, files in os.walk(local_dir):
                rel = os.path.relpath(root, local_dir).replace("\\", "/")
                target = remote_base if rel == "." else remote_base + "/" + rel
                self._ensure_remote_dir(ftp, target)
                for name in files:
                    lp = os.path.join(root, name)
                    rp = target + "/" + name
                    size = os.path.getsize(lp)
                    log("[上传] %s (%d bytes)" % (rp, size))
                    with open(lp, "rb") as fh:
                        ftp.storbinary("STOR " + rp, fh)
            log("[上传完成] %s -> %s" % (local_dir, remote_base))
        finally:
            try:
                ftp.quit()
            except Exception:
                ftp.close()


class SftpUploader:
    """基于 paramiko 的 SFTP 递归上传器（媒体服务器无 FTP 时的首选）。

    paramiko 在运行时才 import（仅真正用 SFTP 上传时才需要），
    因此「只转码不上传」的用户无需安装它。
    """

    def __init__(self, host, user, password="", port=22, remote_dir="/", key_file=""):
        self.host = host
        self.port = int(port or 22)
        self.user = user
        self.password = password or ""
        self.key_file = key_file or ""
        self.remote_dir = remote_dir or "/"

    def _connect(self):
        import paramiko
        transport = paramiko.Transport((self.host, self.port))
        transport.banner_timeout = 30
        if self.key_file:
            pkey = self._load_key(self.key_file, self.password or None)
            transport.connect(username=self.user, pkey=pkey)
        else:
            transport.connect(username=self.user, password=self.password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        return sftp, transport

    @staticmethod
    def _load_key(path, password):
        import paramiko
        for key_cls in (paramiko.RSAKey, paramiko.Ed25519Key,
                        paramiko.ECDSAKey, paramiko.DSSKey):
            try:
                return key_cls.from_private_key_file(path, password=password)
            except Exception:
                continue
        raise ValueError("无法以任何受支持类型加载私钥：%s" % path)

    @staticmethod
    def _ensure_remote_dir(sftp, path):
        parts = [p for p in path.replace("\\", "/").split("/") if p]
        cur = ""
        for p in parts:
            cur = cur + "/" + p if cur else p
            try:
                sftp.stat(cur)
            except OSError:
                try:
                    sftp.mkdir(cur)
                except OSError:
                    pass   # 已存在或竞态
        return "/" + "/".join(parts) if parts else "/"

    def upload_dir(self, local_dir, remote_sub=None, log_cb=None):
        """把 local_dir 整个目录递归上传到 remote_dir[/remote_sub]。"""
        def log(m):
            if log_cb:
                log_cb(m)

        remote_base = self.remote_dir.rstrip("/")
        if remote_sub:
            remote_base = remote_base + "/" + remote_sub.strip("/")

        sftp, transport = self._connect()
        try:
            self._ensure_remote_dir(sftp, remote_base)
            for root, _dirs, files in os.walk(local_dir):
                rel = os.path.relpath(root, local_dir).replace("\\", "/")
                target = remote_base if rel == "." else remote_base + "/" + rel
                self._ensure_remote_dir(sftp, target)
                for name in files:
                    lp = os.path.join(root, name)
                    rp = target + "/" + name
                    size = os.path.getsize(lp)
                    log("[上传] %s (%d bytes)" % (rp, size))
                    sftp.put(lp, rp)
            log("[上传完成] %s -> %s" % (local_dir, remote_base))
        finally:
            try:
                sftp.close()
            except Exception:
                pass
            try:
                transport.close()
            except Exception:
                pass
