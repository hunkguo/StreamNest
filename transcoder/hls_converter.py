"""把单个视频文件转成 HLS(m3u8) + 缩略图。

- HLS：多码率(3档) 或 单码率，输出标准 VOD 点播切片
- 缩略图1：poster.jpg 封面图（在 10% 处截图）
- 缩略图2：sprite.jpg 雪碧图 + thumbnails.vtt 缩略图时间轴（类似 YouTube 预览）
"""
import os
import math

from ffmpeg_util import get_ffmpeg, run, probe

# 码率预设：(视频码率, 音频码率, 分辨率上限)；分辨率上限 None 表示不缩放
PRESETS = {
    "single": [("1000k", "128k", None)],
    "multi": [
        ("2500k", "192k", 1280),   # 高
        ("1200k", "128k", 854),    # 中
        ("600k",  "96k",  640),    # 低
    ],
}


def build_hls_command(ffmpeg, src, out_dir, safe, preset, seg_len, duration, has_audio):
    """构造 ffmpeg HLS 转码命令，返回 (cmd, master_playlist_path)。"""
    os.makedirs(out_dir, exist_ok=True)
    seg_pattern = os.path.join(out_dir, safe + "_%v_%03d.ts")
    playlist_pattern = os.path.join(out_dir, safe + "_%v.m3u8")
    master = os.path.join(out_dir, "index.m3u8")

    cmd = [ffmpeg, "-y", "-i", src]
    cmd += [
        "-c:v", "libx264", "-preset", "veryfast",
        "-g", str(seg_len * 8), "-keyint_min", str(seg_len * 8),
        "-sc_threshold", "0", "-pix_fmt", "yuv420p",
    ]

    streams = PRESETS[preset]
    for i, (vb, _ab, maxres) in enumerate(streams):
        cmd += [
            f"-b:v:{i}", vb,
            f"-maxrate:v:{i}", vb,
            f"-bufsize:v:{i}", str(int(vb[:-1]) * 2) + "k",
        ]
        if maxres:
            cmd += [f"-vf:v:{i}", f"scale='min({maxres},iw)':'-2'"]

    cmd += ["-map", "0:v:0"]
    if has_audio:
        cmd += ["-map", "0:a:0", "-c:a", "aac", "-ar", "44100"]
        for i, (_vb, ab, _maxres) in enumerate(streams):
            cmd += [f"-b:a:{i}", ab]

    var_map = []
    for i in range(len(streams)):
        var_map.append("v:%d%s" % (i, (",a:%d" % i) if has_audio else ""))

    cmd += [
        "-var_stream_map", " ".join(var_map),
        "-master_pl_name", "index.m3u8",
        "-f", "hls",
        "-hls_time", str(seg_len),
        "-hls_list_size", "0",
        "-hls_playlist_type", "vod",
        "-hls_segment_filename", seg_pattern,
        playlist_pattern,
    ]
    return cmd, master


def make_poster(ffmpeg, src, out_dir, duration):
    """在视频 10% 处截取一张封面图 poster.jpg。"""
    poster = os.path.join(out_dir, "poster.jpg")
    ss = max(1.0, duration * 0.1)
    cmd = [ffmpeg, "-y", "-ss", "%.2f" % ss, "-i", src,
           "-frames:v", "1", "-q:v", "2", poster]
    run(cmd)
    return poster


def make_sprite(ffmpeg, src, out_dir, duration, fps=0.0):
    """生成雪碧图 sprite.jpg + thumbnails.vtt 缩略图时间轴。

    采用按帧序号抽帧（select='not(mod(n,STEP))'），对任意长度视频都至少抽到 1 帧，
    避免 fps 滤镜在极短视频上采样出 0 帧导致失败。
    """
    if duration <= 0:
        return None
    thumb_dir = os.path.join(out_dir, "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)
    sprite = os.path.join(thumb_dir, "sprite.jpg")
    vtt = os.path.join(thumb_dir, "thumbnails.vtt")

    interval = 10.0                      # 目标：每约 10 秒取一帧
    n = max(1, int(math.ceil(duration / interval)))
    if n > 100:                          # 超长视频降采样，限制最多 100 格
        n = 100
        interval = duration / n
    cols = 5
    rows = math.ceil(n / cols)
    tw, th = 160, 90                     # 每格缩略图尺寸（16:9）

    # 计算抽帧步长：按总帧数均匀取 n 帧；若帧率未知则退化为按时间 fps 滤镜
    total_frames = int(duration * (fps or 25))
    if total_frames >= n:
        step = max(1, total_frames // n)
        filt = "select='not(mod(n\\,%d))',scale=%d:%d,tile=%dx%d" % (step, tw, th, cols, rows)
    else:
        # 帧数不足 n（极短视频）：用 fps 滤镜尽量抽帧即可
        filt = "scale=%d:%d,tile=%dx%d" % (tw, th, cols, rows)

    cmd = [ffmpeg, "-y", "-i", src, "-vf", filt, "-q:v", "5", sprite]
    run(cmd)

    with open(vtt, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for i in range(n):
            start = i * interval
            end = min(duration, (i + 1) * interval)
            x = (i % cols) * tw
            y = (i // cols) * th
            f.write("%s --> %s\n" % (_ts(start), _ts(end)))
            f.write("sprite.jpg#xywh=%d,%d,%d,%d\n\n" % (x, y, tw, th))
    return {"sprite": sprite, "vtt": vtt}


def _ts(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return "%02d:%02d:%06.3f" % (h, m, s)


def convert(src, output_root, preset="multi", seg_len=6,
            make_poster_img=True, make_sprite_img=True,
            log_cb=None, progress_cb=None,
            media_base="", title=None, description=""):
    """转换单个视频文件。

    参数：
      src              源视频路径
      output_root      输出根目录（会在其下建 <文件名>/ 子目录）
      preset           "multi" 多码率 / "single" 单码率
      seg_len          切片时长（秒）
      make_poster_img  是否生成封面
      make_sprite_img  是否生成雪碧图+VTT
      log_cb           日志回调(str)
      progress_cb      进度回调(0~100)
      media_base       媒体 CDN 基地址（如 https://cdn.example.com），写入 meta.json
      title/description 可选标题/简介，写入 meta.json
    返回结果字典：{master, dir, base, poster, sprite, vtt, meta}
    """
    ffmpeg = get_ffmpeg()
    info = probe(src)
    base = os.path.splitext(os.path.basename(src))[0]
    # 文件名清理，用作输出子目录名（避免非法字符）
    safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in base)
    out_dir = os.path.join(output_root, safe)
    os.makedirs(out_dir, exist_ok=True)

    if log_cb:
        log_cb("[信息] 解析 %s：时长 %.1fs，视频=%s，音频=%s"
               % (base, info["duration"], info["has_video"], info["has_audio"]))

    cmd, master = build_hls_command(
        ffmpeg, src, out_dir, safe, preset, seg_len,
        info["duration"], info["has_audio"])
    if log_cb:
        log_cb("[执行] " + " ".join(cmd[:8]) + " ...")
    run(cmd, log_cb=log_cb, progress_cb=progress_cb, duration=info["duration"])

    result = {"master": master, "dir": out_dir, "base": safe}
    if make_poster_img:
        try:
            result["poster"] = make_poster(ffmpeg, src, out_dir, info["duration"])
            if log_cb:
                log_cb("[完成] 封面 poster.jpg")
        except Exception as e:
            if log_cb:
                log_cb("[警告] 封面生成失败，已跳过：%s" % e)
    if make_sprite_img:
        try:
            sp = make_sprite(ffmpeg, src, out_dir, info["duration"], info.get("fps", 0.0))
            if sp:
                result["sprite"] = sp["sprite"]
                result["vtt"] = sp["vtt"]
                if log_cb:
                    log_cb("[完成] 雪碧图 + VTT 缩略图时间轴")
        except Exception as e:
            if log_cb:
                log_cb("[警告] 雪碧图生成失败，已跳过：%s" % e)

    # 生成 meta.json（供 web 端 sync.php 导入数据库）
    import publish
    meta = publish.build_meta(safe, src, media_base, info["duration"],
                              title=title, description=description)
    publish.write_meta(out_dir, meta)
    result["meta"] = meta
    if log_cb:
        log_cb("[完成] meta.json（CDN 地址已写入）")

    if log_cb:
        log_cb("[成功] %s -> %s" % (base, master))
    return result
