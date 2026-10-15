"""读取 config.json 配置。

设计目标：**改配置不改代码**。
- 主配置：config.json（可入库，含域名等非敏感信息）
- 本地覆盖：config.local.json（不入库，放 FTP 密码等敏感信息）

查找顺序（后者覆盖前者）：
    程序目录/config.json
    程序目录/config.local.json
"""
import os
import json
import sys

DEFAULT_CONFIG = {
    "site": {
        "base_url": "https://site.example.com",
        "sync_endpoint": "https://site.example.com/sync.php",
        "sync_token": "",
    },
    "media": {
        "base_url": "https://cdn.example.com",
    },
    "convert": {
        "preset": "multi",
        "seg_len": 6,
        "poster": True,
        "sprite": True,
    },
    "upload": {
        "enabled": False,
        "method": "sftp",
        "host": "",
        "port": 22,
        "user": "",
        "password": "",
        "key_file": "",
        "remote_dir": "/var/www/media",
    },
    "sync": {
        "auto_sync": False,
    },
}


def app_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _search_dirs():
    """配置查找目录。打包后同时包含 exe 同级目录与 _MEIPASS（内置默认配置）。"""
    dirs = [app_base_dir()]
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass and meipass not in dirs:
            dirs.append(meipass)
    return dirs


def _deep_merge(dst, src):
    """把 src 递归合并进 dst（返回新 dict，不修改入参）。"""
    out = dict(dst)
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _load_file(path):
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print("[配置] 读取 %s 失败：%s（使用默认配置）" % (path, e))
        return {}


def load_config(base_dir=None):
    """加载配置。

    优先级（后者覆盖前者）：
        内置默认值 ← _MEIPASS/config.json（exe 内置，仅开发/缺省时）
                    ← exe 同级 config.json（用户可编辑）
                    ← exe 同级 config.local.json（本地覆盖，建议放密码）
    """
    cfg = dict(DEFAULT_CONFIG)
    if base_dir:
        dirs = [base_dir]
    else:
        # _MEIPASS 在前（内置默认），exe 同级在后（用户覆盖）
        dirs = list(reversed(_search_dirs()))
    for d in dirs:
        cfg = _deep_merge(cfg, _load_file(os.path.join(d, "config.json")))
    if not base_dir:
        cfg = _deep_merge(cfg, _load_file(os.path.join(app_base_dir(), "config.local.json")))
    return cfg


def get_media_base(cfg=None):
    """媒体服务器基地址（去掉尾部斜杠）。"""
    cfg = cfg or load_config()
    return (cfg.get("media", {}).get("base_url") or "").rstrip("/")


def get_site(cfg=None):
    """前端站点配置。"""
    cfg = cfg or load_config()
    return cfg.get("site", {})


def get_upload(cfg=None):
    """媒体上传配置（method=sftp/ftp/none）。"""
    cfg = cfg or load_config()
    return cfg.get("upload", {})


def upload_ready(upload_cfg):
    """上传配置是否可用（主机与用户名都填了，且 method != none）。"""
    if not upload_cfg:
        return False
    if str(upload_cfg.get("method", "none")).lower() == "none":
        return False
    return bool(upload_cfg.get("host") and upload_cfg.get("user"))


if __name__ == "__main__":
    import json as _json
    print(_json.dumps(load_config(), ensure_ascii=False, indent=2))