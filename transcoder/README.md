# Transcoder — 视频自动转 m3u8 + 缩略图

单机 Windows 工具：把某个文件夹下的视频文件自动转换为 HLS（m3u8）点播切片，
并生成缩略图（封面图 + 雪碧图时间轴）。可打包为单个 exe 运行，无需安装环境。

## 功能
- 自动扫描源文件夹，将视频转为标准 HLS：
  - **多码率（3档，默认）**：高/中/低，播放器按带宽自适应
  - **单码率**：更简单、体积更小
- 生成缩略图：
  - `poster.jpg` 封面图（视频 10% 处截图）
  - `thumbnails/sprite.jpg` + `thumbnails.vtt` 雪碧图时间轴（类似 YouTube 预览）
- **监视模式**：持续盯着源文件夹，发现新视频自动转换（文件写完才处理）
- 图形界面（tkinter）与命令行两种用法

## 目录结构
转换后每个视频生成一个独立子目录，例如 `output/我的视频/`：
```
我的视频/
├── index.m3u8        # 主播放列表（多码率入口）
├── 我的视频_0.m3u8    # 高码率
├── 我的视频_1.m3u8    # 中码率
├── 我的视频_2.m3u8    # 低码率
├── 我的视频_0_000.ts  # 切片
├── poster.jpg         # 封面
├── meta.json          # 该视频的元数据（CDN 地址、时长等）
└── thumbnails/
    ├── sprite.jpg     # 雪碧图
    └── thumbnails.vtt # 缩略图时间轴
```
把整个子目录上传到 CDN（如 cdn.example.com）即可通过 `index.m3u8` 播放。

输出根目录还会生成一个 `manifest.json`：包含本次（历史累计）所有视频的清单，
用于一次性导入 web 端数据库，实现前端自动同步。

## 前置：ffmpeg
程序需要 ffmpeg（含 ffprobe）。把 `ffmpeg.exe` / `ffprobe.exe` 放入 `ffmpeg/` 子目录，
或加入系统 PATH，或设置环境变量 `FFMPEG_PATH`。
下载：https://www.gyan.dev/ffmpeg/builds/

## 用法
### 图形界面
```
python transcoder_gui.py
```
选择源文件夹、输出文件夹，设置选项，点“转换源文件夹内全部”或勾选“监视模式”。

### 命令行
```
# 转换源文件夹内全部
python transcoder_gui.py --source D:/videos --output D:/out

# 持续监视（发现新文件自动转）
python transcoder_gui.py --source D:/videos --output D:/out --watch

# 单码率、切片 10 秒、不生成雪碧图
python transcoder_gui.py --source D:/videos --output D:/out --single --seg 10 --no-sprite

# 转码 + 写入 CDN 地址 + 自动 FTP 上传
python transcoder_gui.py --source D:/videos --output D:/out \
  --media-base https://cdn.example.com \
  --ftp-host ftp.example.com --ftp-user u --ftp-pass p --ftp-dir /www/media --ftp-upload
```

## 发布：转码 → 上传 → 前端同步
1. 转码得到 `output/<名称>/`（含 index.m3u8、切片、poster.jpg、meta.json、thumbnails/）
2. **上传**：FTP 上传到媒体 CDN（如 cdn.example.com），或手动上传
3. **同步数据**：把 `output/manifest.json` 提交给站点：
   ```
   curl -X POST "https://你的域名/sync.php?token=SYNC_TOKEN" \
        -H "Content-Type: application/json" \
        --data-binary @output/manifest.json
   ```
   站点会按 `video_url` 去重：新的插入、已有的更新。前端（index.php 读数据库）即同步。

## 打包为 exe
1. 把 `ffmpeg.exe` / `ffprobe.exe` 放入 `ffmpeg/` 目录
2. 用系统 Python 3.14（自带 tkinter）运行：右键 `build_exe.ps1` → 用 PowerShell 运行
   （脚本会自动建虚拟环境并调用 PyInstaller，约 1~2 分钟）
3. 产物：`dist/Transcoder.exe`（单文件，双击即用）
> 说明：WorkBuddy 托管 Python 3.13 不含 tkinter，故使用系统 Python 3.14 打包。

## 技术要点
- 纯标准库 + subprocess 调用 ffmpeg，无第三方运行时依赖
- 目录监视用轮询（不依赖 watchdog），便于打包
- 进度通过 ffmpeg stderr 的 `time=` 字段实时解析
- 多码率用 ffmpeg `-var_stream_map` 单遍输出，效率高于多次转码
