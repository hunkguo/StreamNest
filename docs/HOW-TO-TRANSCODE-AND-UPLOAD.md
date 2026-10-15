# 视频转换与上传操作手册 · How to Transcode & Upload

> 适用版本：StreamNest v1.0 ｜ 目标读者：站点维护者 / 转码操作员
>
> 本手册覆盖从「本地原始视频」到「网站能在线播放并同步到前端」的完整流程。
> 全程**无需改代码**，所有域名、上传方式、同步地址都在配置文件中。

---

## 📐 整体架构：两个域名各管什么

StreamNest 采用**前端与媒体分离**架构，这是理解整条链路的前提：

```
┌─────────────────────────────────────────────────────────────────┐
│ 你的本地电脑（Windows）                                          │
│                                                                 │
│   原始视频 ──> StreamNest 转码器 ──> HLS + 缩略图                │
│                   (Transcoder.exe)         │                    │
└───────────────────────────────────────────┼────────────────────┘
                                            │
                    ①SFTP 上传              │ ②HTTP 同步数据
                    ▼                       ▼
        ┌───────────────────────┐  ┌──────────────────────────┐
        │  媒体服务器            │  │  前端站点                │
        │  cdn.example.com       │  │  site.example.com            │
        │  （无 FTP，用 SSH）    │  │  （Serv00，有 FTP）      │
        │                       │  │                          │
        │  · index.m3u8         │  │  · index.php 列表/搜索   │
        │  · *.ts 视频切片      │  │  · player.php 播放页     │
        │  · poster.jpg 封面    │  │  · login.php 登录        │
        │  · sprite.jpg 雪碧图  │  │  · MySQL: videos 表      │
        │                       │  │                          │
        │  （纯静态托管/CDN）    │  │  （PHP + MySQL）         │
        └───────────────────────┘  └──────────────────────────┘
                    ▲                            │
                    └───── 浏览器播放器直接拉流 ◄─┘
                          （视频流不经过前端服务器）
```

**关键点**：前端 `site.example.com`（Serv00，有 FTP，只用于部署网页和跑数据库）只存放**页面和数据库**；
视频流由浏览器**直接**从 `cdn.example.com`（另一台服务器，**无 FTP**，用 SSH/SFTP 上传）拉取。
这样媒体服务器可以是任意静态托管/CDN，前端服务器压力极小，两者互不影响。

---

## ⚙️ 第一步：配置（只做一次）

### 1.1 前端站点配置：`web/config.php`

编辑 `web/config.php`：

```php
// 数据库（Serv00 面板 MySQL databases 里创建后填这里）
define('DB_HOST', 'localhost');
define('DB_NAME', '你的数据库名');
define('DB_USER', '你的数据库用户');
define('DB_PASS', '你的数据库密码');

// 前端站点域名
define('SITE_URL', 'https://site.example.com');

// 媒体服务器域名（转码后的 m3u8 / 缩略图上传到这里）
define('MEDIA_BASE', 'https://cdn.example.com');

// 数据同步令牌：本地转码机调用 sync.php 时携带，建议改成一串随机字符
define('SYNC_TOKEN', '换成你自己的随机字符串');
```

> 生成随机令牌可在服务器执行：`head -c 32 /dev/urandom | base64`

### 1.2 转码器配置：`transcoder/config.json`

编辑 `transcoder/config.json`（**这是转码器改域名的主入口**）：

```json
{
  "site": {
    "base_url": "https://site.example.com",
    "sync_endpoint": "https://site.example.com/sync.php",
    "sync_token": "与上面 SYNC_TOKEN 一致"
  },
  "media": {
    "base_url": "https://cdn.example.com"
  },
  "convert": {
    "preset": "multi",
    "seg_len": 6,
    "poster": true,
    "sprite": true
  },
  "upload": {
    "enabled": true,
    "method": "sftp",
    "host": "cdn.example.com",
    "port": 22,
    "user": "你的SSH用户名",
    "password": "",
    "key_file": "",
    "remote_dir": "/var/www/media"
  },
  "sync": {
    "auto_sync": false
  }
}
```

> `upload.method` 可选：`sftp`（媒体服务器无 FTP，默认用这个）／`ftp`（少数还支持 FTP 的服务器）／`none`（只生成本地文件，手动上传）。

### 1.3 SSH 私钥建议单独存放（推荐）

> SFTP 以**密钥文件**登录，**无需密码**。私钥文件请用 OpenSSH / PEM 格式
> （`.ppk` 请先用 PuTTYgen 转换为 OpenSSH 格式）；若私钥本身有口令，把口令填到 `password` 字段。

不想把密钥 / 令牌提交到 Git？新建 `transcoder/config.local.json`（该文件已在 `.gitignore` 中）：

```json
{
  "upload": {
    "enabled": true,
    "method": "sftp",
    "host": "cdn.example.com",
    "user": "sshuser",
    "key_file": "/path/to/id_ed25519",
    "remote_dir": "/var/www/media"
  },
  "site": { "sync_token": "真实令牌" }
}
```

**配置优先级**（后者覆盖前者）：
`内置默认值` ← `exe 内置 config.json` ← `exe 同级 config.json` ← `exe 同级 config.local.json`

---

## 🎬 第二步：准备转码环境

### 2.1 首次使用（源码方式）

1. 下载 **ffmpeg（含 ffprobe）**，解压后把 `ffmpeg.exe`、`ffprobe.exe` 放进 `transcoder/ffmpeg/` 目录。
   - 推荐下载 **essentials** 版本（gyan.dev / BtbN 均可），体积小、够用。
2. 用**带 tkinter 的 Python 3.13/3.14 官方版**运行（tkinter 用于图形界面）：
   ```bash
   cd transcoder
   python transcoder_gui.py
   ```

### 2.2 打包为 exe（推荐分发）

```powershell
cd transcoder
powershell -ExecutionPolicy Bypass -File build_exe.ps1
```

产物：`transcoder/dist/Transcoder.exe`（约 90MB，**已内嵌 ffmpeg/ffprobe，单文件即可运行**）。

> 打包脚本会自动创建 `.build/venv` 并安装 PyInstaller。
> 注意：ffmpeg 会被一并打进 exe，所以生成的 exe 无需再单独携带 ffmpeg。

---

## 🔄 第三步：转换视频

### 方式 A：图形界面（推荐日常使用）

1. 双击运行 `Transcoder.exe`。
2. **源文件夹**：点「浏览」选择存放原始视频的目录（如 `D:\videos`）。
3. **输出文件夹**：选择转码结果存放目录（如 `D:\hls`）。
4. **转换选项**（默认值来自 `config.json`）：
   - 多码率（3 档自适应）**或** 单码率
   - 切片时长（秒）
   - ☑ 生成封面图　☑ 生成雪碧图+VTT
5. **发布选项**：
   - 媒体基地址：默认取 `config.json` 的 `media.base_url`
   - 上传方式：选 `sftp`（媒体服务器无 FTP）
   - 填入 SSH 主机/端口/用户名，并选择「密钥文件」（无需密码）与远程目录，☑「转码后自动上传」
6. 点击 **「转换源文件夹内全部」** 开始；或点 **「开始监视」** 进入监视模式，
   之后往源文件夹丢新视频会自动转码。

### 方式 B：命令行

```bash
# 转换文件夹内全部视频
Transcoder.exe --source D:/videos --output D:/hls

# 持续监视（发现新视频自动转）
Transcoder.exe --source D:/videos --output D:/hls --watch

# 单码率、切片 10 秒、不生成雪碧图
Transcoder.exe --source D:/videos --output D:/hls --single --seg 10 --no-sprite

# 写入 CDN 地址 + 自动 SFTP 上传（媒体服务器无 FTP，用 SSH；不传 --media-base 时用配置默认值）
Transcoder.exe --source D:/videos --output D:/hls \
  --sftp-host cdn.example.com --sftp-user u --sftp-key C:/keys/id_ed25519 --sftp-dir /var/www/media --sftp-upload
```

### 转码产物结构

每个视频会在输出目录下生成一个以其命名的子目录：

```
output/
├── <视频名>/
│   ├── index.m3u8          # HLS 主播放列表（多码率时含多档，或单码率直接切片）
│   ├── <视频名>_0.m3u8     # （多码率时）各码率子列表
│   ├── *.ts                # 视频切片
│   ├── poster.jpg          # 封面图（约 10% 处截图）
│   ├── thumbnails/
│   │   ├── sprite.jpg      # 雪碧图（每 10 秒一帧拼成一张长图）
│   │   └── thumbnails.vtt  # 缩略图时间轴（播放器进度条预览）
│   └── meta.json           # 本视频元数据（含 cdn.example.com 完整地址）
└── manifest.json           # 全部视频清单（用于同步到前端）
```

> **缩略图说明**：封面 `poster.jpg` 用作列表卡片图；雪碧图 + VTT 让播放器在**拖动进度条时**实时预览画面。

---

## 📤 第四步：上传到媒体服务器（cdn.example.com，无 FTP）

> 该服务器**没有 FTP**，请用 SSH/SFTP 相关方式上传。

### 方式 A：转码器自动 SFTP 上传（最省事）

在 GUI 的「发布」区填好 SSH 信息并勾选「转码后自动上传」（方式选 `sftp`），或在命令行加 `--sftp-upload`。
转码完成后会自动把 `output/<视频名>/` 整个目录递归上传到 `remote_dir/<视频名>/`。

### 方式 B：手动上传（SCP / WinSCP / 面板）

用 WinSCP（选 SFTP 协议）、或命令行 `scp -r`，或服务器面板文件管理器，
把 `output/<视频名>/` **整个目录**上传到媒体服务器的站点根目录，
确保 `index.m3u8`、`poster.jpg`、切片、`thumbnails/` 都在。

```bash
# 例：用 scp 手动上传
scp -r D:/hls/<视频名> sshuser@cdn.example.com:/var/www/media/
```

### 上传后自检

在浏览器打开（应能直接播放/看到图片）：

- `https://cdn.example.com/<视频名>/index.m3u8` → 应显示 m3u8 文件内容
- `https://cdn.example.com/<视频名>/poster.jpg` → 应显示封面图

> ⚠️ **跨域要求**：媒体服务器需允许前端域名跨域访问 m3u8 与切片。
> 若媒体服务器是 Nginx，添加：
> ```nginx
> add_header Access-Control-Allow-Origin *;
> ```
> 若用 CDN，请在 CDN 控制台配置 CORS 允许 `https://site.example.com`。

---

## 🔄 第五步：同步数据到前端（让网站显示新视频）

上传完成后，需要把「有哪些视频」告诉前端数据库。

### 方式 A：命令行一条同步（推荐）

```bash
curl -X POST "https://site.example.com/sync.php?token=你的SYNC_TOKEN" \
     -H "Content-Type: application/json" \
     --data-binary @output/manifest.json
```

成功返回：
```json
{"ok":true,"inserted":3,"updated":1,"skipped":0,"total":4}
```

- `inserted`：新增入库数量
- `updated`：已存在、已更新标题/封面的数量
- `video_url` 相同的视为同一条，**重复执行不会产生重复记录**（幂等）。

### 方式 B：手动提交

浏览器打开 `https://site.example.com/sync.php?token=你的SYNC_TOKEN`，
把 `manifest.json` 内容作为 JSON 数组 POST 过去（可用 curl / Postman）。

### 同步后

刷新 `https://site.example.com`，新视频即出现在列表中；点进播放页即可播放
（浏览器直接从 `cdn.example.com` 拉流）。

---

## 🔁 一键流水线（推荐日常用法）

把「转码 → 上传 → 同步」串成一条命令（Windows 批处理 `pipeline.bat`）：

```bat
@echo off
set TOKEN=你的SYNC_TOKEN
set MEDIA=https://cdn.example.com
set SITE=https://site.example.com

REM 1) 转码（SFTP 自动上传已在 config.json 开启）
Transcoder.exe --source D:\videos --output D:\hls --sftp-upload

REM 2) 同步数据到前端
curl -X POST "%SITE%/sync.php?token=%TOKEN%" ^
     -H "Content-Type: application/json" ^
     --data-binary @D:\hls\manifest.json
```

以后只需：把视频丢进 `D:\videos` → 双击 `pipeline.bat` → 刷新网站即可看到新视频。

---

## ❓ 常见问题排查

| 现象 | 原因与解决 |
|---|---|
| 提示「未找到 ffmpeg」 | exe 已内嵌 ffmpeg，若仍报错请确认用的是完整 `Transcoder.exe`；源码运行则检查 `transcoder/ffmpeg/ffmpeg.exe` 是否存在 |
| 打包报 tkinter 缺失 | 打包用的 Python 不含 tkinter，换官方 Python 3.13/3.14（`python -c "import tkinter"` 验证） |
| exe 无法启动就闪退 | 用带 tkinter 的 Python 打包；或 `Transcoder.exe --help` 看是否正常 |
| 上传后播放器黑屏 | ①确认 `index.m3u8` 与切片都能访问；②检查媒体服务器 CORS 是否允许前端域名；③确认 `meta.json` 里 `video_url` 正确 |
| 同步返回 403 | `SYNC_TOKEN` 与提交 token 不一致，或 `SYNC_TOKEN` 为空 |
| 同步没报错但前端没变 | 确认提交的是最新 `manifest.json`；`skipped` 偏大说明条目缺 `video_url` |
| 封面/雪碧图不显示 | 浏览器直接访问 `poster.jpg` 确认 200；`.htaccess`/Nginx 是否拦了图片 |
| 视频不自动播放/进度条无预览 | 播放器需能访问 `thumbnails/thumbnails.vtt` 与 `sprite.jpg` |

---

## 🔐 安全提醒

- `SYNC_TOKEN` 等于数据写入口令，务必改成随机字符串，且不要提交到公开仓库。
- SSH 密码放在 `config.local.json`（已 gitignore），不要写进 `config.json`。
- 部署完成后建议**删除或禁用** `web/install.php`、`web/check.php`。
- 站点已内置 CSRF、登录限流、`password_hash`、会话再生等防护。

---

## 📎 相关文件速查

| 文件 | 作用 |
|---|---|
| `web/config.php` | 前端站点：数据库、站点域名、媒体域名、同步令牌 |
| `web/sync.php` | 数据同步端点（导入 manifest.json） |
| `web/install.php` | 一键建表 + 导入示例数据（用完请删） |
| `transcoder/config.json` | 转码器配置：前端/媒体域名、上传方式、同步（主配置，可入库） |
| `transcoder/config.local.json` | 本地覆盖配置，放 SSH 密码（不入库） |
| `transcoder/appconfig.py` | 配置加载模块 |
| `transcoder/build_exe.ps1` | 一键打包 exe |