"""ffmpeg / ffprobe 定位与调用工具。

负责：
1. 按优先级找到 ffmpeg / ffprobe 可执行文件（环境变量 > 程序旁 ffmpeg/ 子目录 > 系统 PATH）
2. 运行命令并实时回传日志、解析 ffmpeg 进度
3. 用 ffprobe 探测视频时长、是否含音视频流
"""
import os
import re
import sys
import json
import shutil
import subprocess

# 支持的视频扩展名（用于自动扫描与监视）
VIDEO_EXTS = {
    ".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".m4v",
    ".ts", ".webm", ".mpg", ".mpeg", ".3gp", ".m2ts", ".vob", ".mts",
}


def app_base_dir():
    """程序基准目录：打包后为 exe 所在目录，开发时为脚本目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _name_variants(name):
    """生成待查找的文件名候选（Windows 上需带 .exe 后缀）。"""
    if os.name == "nt" and not name.lower().endswith(".exe"):
        return [name + ".exe", name]
    return [name]


def find_binary(name):
    """按优先级查找 ffmpeg / ffprobe。

    查找顺序：
    1) 环境变量 FFMPEG_PATH / FFPROBE_PATH
    2) 程序旁 ./ffmpeg/ 子目录（打包后随 exe 发布，或开发时手动放置）
    3) PyInstaller 解压目录 _MEIPASS（含 ffmpeg/ffmpeg/ 子目录）
    4) 系统 PATH
    """
    env_map = {"ffmpeg": "FFMPEG_PATH", "ffprobe": "FFPROBE_PATH"}
    env = env_map.get(name)
    if env and os.environ.get(env):
        p = os.environ[env]
        if os.path.isfile(p):
            return p

    base = app_base_dir()
    names = _name_variants(name)
    candidates = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            for n in names:
                candidates.append(os.path.join(meipass, n))
                candidates.append(os.path.join(meipass, "ffmpeg", n))
    for n in names:
        candidates.append(os.path.join(base, "ffmpeg", n))
        candidates.append(os.path.join(base, n))
    for c in candidates:
        if os.path.isfile(c):
            return c

    found = shutil.which(name)
    if found:
        return found
    return None


def get_ffmpeg():
    p = find_binary("ffmpeg")
    if not p:
        raise FileNotFoundError(
            "未找到 ffmpeg。请将 ffmpeg.exe 放到程序目录下的 ffmpeg/ 子目录，"
            "或把 ffmpeg 所在目录加入系统 PATH，或设置环境变量 FFMPEG_PATH。"
        )
    return p


def get_ffprobe():
    p = find_binary("ffprobe")
    if not p:
        raise FileNotFoundError("未找到 ffprobe（通常随 ffmpeg 一起提供）。")
    return p


def run(cmd, log_cb=None, progress_cb=None, duration=None):
    """运行命令，实时把输出传给 log_cb，并从 ffmpeg 进度行中解析进度百分比。"""
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,   # ffmpeg 进度在 stderr，stdout 丢弃避免死锁
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    time_re = re.compile(r"time=(\d+):(\d+):(\d+)\.(\d+)")
    for line in proc.stderr:
        line = line.rstrip("\n")
        if log_cb:
            log_cb(line)
        if progress_cb and duration and duration > 0:
            m = time_re.search(line)
            if m:
                h, mi, s, frac = (int(x) for x in m.groups())
                cur = h * 3600 + mi * 60 + s + int(frac) / 100
                progress_cb(min(100.0, cur / duration * 100.0))
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(
            "命令执行失败（退出码 %d）: %s ..." % (proc.returncode, " ".join(cmd[:6]))
        )
    return proc.returncode


def probe(path):
    """用 ffprobe 解析视频信息，返回字典。"""
    ffprobe = get_ffprobe()
    cmd = [
        ffprobe, "-v", "error",
        "-show_entries", "format=duration:stream=codec_type,width,height",
        "-of", "json", path,
    ]
    out = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if out.returncode != 0:
        raise RuntimeError("ffprobe 解析失败: " + out.stderr[:300])
    data = json.loads(out.stdout)
    dur = 0.0
    has_video = has_audio = False
    width = height = 0
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            has_video = True
            width = int(s.get("width", 0) or 0)
            height = int(s.get("height", 0) or 0)
        elif s.get("codec_type") == "audio":
            has_audio = True
    try:
        dur = float(data.get("format", {}).get("duration", 0) or 0)
    except (ValueError, TypeError):
        dur = 0.0
    fps = 0.0
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            fr = s.get("avg_frame_rate", "0/1")
            try:
                a, b = fr.split("/")
                fps = float(a) / float(b) if float(b) else 0.0
            except Exception:
                fps = 0.0
            break
    return {
        "duration": dur,
        "has_video": has_video,
        "has_audio": has_audio,
        "width": width,
        "height": height,
        "fps": fps,
    }
