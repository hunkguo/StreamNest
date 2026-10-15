<h1 align="center">StreamNest · 流巢</h1>

<p align="center">
  <b>Self-hosted HLS video library · 自建 HLS 视频站 + 一键本地转码器</b><br />
  A lightweight PHP + MySQL streaming catalog that pairs with a Windows desktop tool
  which turns any video folder into HLS (m3u8) playlists, thumbnails, and a synced database.
</p>

<p align="center">
  <img alt="PHP" src="https://img.shields.io/badge/PHP-8.0%2B-777BB4?logo=php&logoColor=white" />
  <img alt="MySQL" src="https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white" />
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" />
  <img alt="ffmpeg" src="https://img.shields.io/badge/ffmpeg-required-007808?logo=ffmpeg&logoColor=white" />
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green" />
</p>

---

## 📖 简介 / Intro

**StreamNest（流巢）** 是一套"自建视频库 + 本地转码"的完整方案，由两个独立部分组成：

- **`web/`** — 一个轻量 PHP + MySQL 视频目录站：作品展示、搜索、分页、用户注册/登录、
  播放页（video.js + hls.js 自适应 HLS），部署在支持 PHP 的空间（如 Serv00）上。
- **`transcoder/`** — 一个 Windows 桌面工具（Python，可打包为单文件 exe）：
  监视某个文件夹，把新视频**自动**转成标准 HLS（m3u8 + 多码率切片），
  并生成**封面图**与**雪碧图缩略图时间轴**，最后可选上传到媒体服务器（SFTP/手动）、输出数据清单。

两者通过一份 `manifest.json` 打通：转码器产出 → 上传媒体 → 一条命令把数据导入站点数据库 → 前端自动同步。

> **StreamNest** is a self-hosted HLS streaming stack: a PHP + MySQL catalog site
> plus a Windows transcoder that watches a folder, converts videos to HLS with
> thumbnails, uploads them, and syncs the catalog automatically.

---

## ✨ 特性 / Features

**Web 端**
- 视频目录：卡片列表、关键词搜索、分页
- 用户系统：注册 / 登录 / 登出 / 用户中心，PDO 预处理、`password_hash`、CSRF、登录限流、会话再生
- 播放页：video.js + hls.js（非 Safari）与原生 HLS（Safari/iOS）双分支
- 收藏、观看历史数据表（可扩展会员分级、权限）
- 无数据库时自动回退到内置 JS 数据，方便本地预览

**转码器（transcoder）**
- 自动扫描 / 监视文件夹，**发现新视频即自动转码**
- 标准 HLS 点播：多码率（3 档自适应）或单码率
- **缩略图**：`poster.jpg` 封面 + `sprite.jpg` 雪碧图 + `thumbnails.vtt` 时间轴
- 生成 `meta.json` / `manifest.json`，可直接导入站点
- 可选**上传**到媒体服务器（SFTP 优先；媒体服务器无 FTP 时用 SSH；也支持手动）
- 纯标准库 + 调用 ffmpeg，可 PyInstaller 打包为单文件 exe
- 图形界面（tkinter）与命令行双模式

---

## 🏗️ 架构 / Architecture

```
┌─────────────────────────── 本地（Windows）───────────────────────────┐
│  transcoder.exe                                                       │
│  监控 source/  ──> ffmpeg 转 HLS ──> output/<名称>/                   │
│      │                                ├─ index.m3u8 (多码率)          │
│      │                                ├─ *.ts 切片                    │
│      │                                ├─ poster.jpg   (封面)          │
│      │                                ├─ thumbnails/  (雪碧图+VTT)    │
│      │                                └─ meta.json                    │
│      └──> output/manifest.json （全部视频清单）                       │
└───────────────┬───────────────────────────────┬─────────────────────┘
                │ SFTP 上传媒体                  │ POST manifest.json
                ▼                               ▼
        media server (cdn.example.com)  web/sync.php (token 鉴权)
        https://.../index.m3u8                 │  upsert by video_url
                                               ▼
                                    MySQL: videos / users / favorites ...
                                               │
                                               ▼
                                   web/ 站点（PHP）→ 前端自动同步
```

---

## 📂 目录结构 / Structure

```
.
├── web/                     # 视频目录站（部署到 Serv00 / 任意 PHP 空间）
│   ├── index.php            # 首页：列表 + 搜索 + 分页
│   ├── player.php           # 播放页
│   ├── login.php            # 注册 / 登录合页
│   ├── logout.php / account.php
│   ├── install.php          # 一键建表 + 导入示例数据（用完请删）
│   ├── check.php            # 查看 PHP 版本 / 扩展（用完请删）
│   ├── sync.php             # 数据同步端点（导入 manifest.json）
│   ├── config.php           # 数据库 / 站点 / 媒体 / 同步令牌配置
│   ├── includes/            # db.php / auth.php / header.php / footer.php
│   ├── css/ js/ img/        # 前端资源
│   └── .htaccess            # 缓存、安全头、PHP 优先
│
├── transcoder/              # 本地转码器（Windows）
│   ├── transcoder_gui.py    # 主程序（GUI + CLI）
│   ├── hls_converter.py     # ffmpeg 转 HLS + 缩略图核心
│   ├── ffmpeg_util.py       # ffmpeg/ffprobe 定位、执行、进度解析
│   ├── folder_watcher.py    # 轮询式目录监视
│   ├── publish.py           # meta/manifest 生成 + 上传（SFTP/FTP/none）
│   ├── build.spec           # PyInstaller 打包配置
│   ├── build_exe.ps1        # 一键打包脚本（Windows）
│   ├── ffmpeg/              # 放置 ffmpeg.exe / ffprobe.exe
│   └── README.md
│
└── README.md
```

---

## ⚙️ 配置（改配置不改代码）

全项目**两个域名**通过配置解耦，改任何一处都不需要动代码：

| 用途 | 配置位置 | 当前值 |
|---|---|---|
| 前端站点 | `web/config.php` → `SITE_URL` | `https://site.example.com` |
| 媒体服务器 | `web/config.php` → `MEDIA_BASE` | `https://cdn.example.com` |
| 媒体服务器 | `transcoder/config.json` → `media.base_url` | `https://cdn.example.com` |
| 前端站点 | `transcoder/config.json` → `site.base_url` | `https://site.example.com` |
| 数据同步令牌 | `web/config.php` → `SYNC_TOKEN` / `transcoder/config.json` → `site.sync_token` | 需自行填写 |

- **前端（`site.example.com`）**：只跑 `web/`（PHP + MySQL），负责页面、搜索、登录、视频清单数据库。
- **媒体（`cdn.example.com`）**：只存 `m3u8 / 切片 / 封面 / 雪碧图`，由转码器上传。两边通过 URL 解耦，
  前端从不在本站输出视频流，因此媒体服务器可以用纯静态托管/CDN。

> **transcoder 配置文件优先级**（后者覆盖前者）：
> 内置默认值 ← exe 内置 `config.json` ← exe 同级 `config.json` ← exe 同级 `config.local.json`
> （`config.local.json` 不入库，用来放 SSH 密码等敏感信息）。

---

## 🧰 技术栈 / Stack

| 部分 | 技术 |
|---|---|
| Web | PHP 8.0+、PDO(MySQL)、Session、CSRF、MDB5 UI、video.js + hls.js |
| DB | MySQL 8.0 / MariaDB |
| Transcoder | Python 3.10+（标准库）、tkinter、subprocess；SFTP 上传用 paramiko（仅上传时依赖） |
| 转码核心 | ffmpeg（libx264 / aac / HLS muxer）、ffprobe |
| 打包 | PyInstaller（单文件 exe） |

---

## 🚀 快速开始 / Quick Start

### 1) 部署 Web 端（以 Serv00 为例）

1. 在面板 **MySQL Databases** 建库，记下 库名 / 用户 / 密码。
2. 编辑 `web/config.php`，填入 `DB_*`，并设置 `MEDIA_BASE` 与 `SYNC_TOKEN`
   （`SYNC_TOKEN` 建议改成一串随机字符）。
3. 上传 `web/` 到站点根目录，浏览器访问 `install.php` 建表并导入示例数据。
4. **完成后删除 `install.php` 与 `check.php`**（或把 `install.php` 顶部 `$ALLOW_INSTALL` 设为 `false`）。
5. PHP 版本：面板 `WWW Websites → 你的域名 → Additional settings → PHP version`，建议 8.3 / 8.4。

### 2) 使用转码器

1. 下载 ffmpeg（含 ffprobe），把 `ffmpeg.exe` / `ffprobe.exe` 放进 `transcoder/ffmpeg/`。
2. 开发运行：
   ```bash
   python transcoder_gui.py
   ```
3. 打包为单文件 exe（使用带 tkinter 的 Python，如 3.13/3.14）：
   ```powershell
   powershell -ExecutionPolicy Bypass -File build_exe.ps1
   ```
   产物：`transcoder/dist/Transcoder.exe`。

---

## 🔁 工作流：转码 → 上传 → 前端同步

这是把"本地视频"变成"网站线上可播"的完整链路。

**① 转码**：把视频丢进 `source/`，或用 GUI 点"转换源文件夹内全部"（也可开监视模式自动转）。
产出 `output/<名称>/`：`index.m3u8`、切片、`poster.jpg`、`thumbnails/`、`meta.json`。

**② 上传**：把 `output/<名称>/` 整个目录上传到媒体服务器 `cdn.example.com`（SFTP / SCP / 面板，因为该服务器**无 FTP**）。
转码器亦可勾选"转码后自动上传"（SFTP 方式）直接完成。上传后地址形如：
`https://cdn.example.com/<名称>/index.m3u8`。

**③ 同步数据**：把清单提交给前端站点，前端即更新：
```bash
curl -X POST "https://site.example.com/sync.php?token=SYNC_TOKEN" \
     -H "Content-Type: application/json" \
     --data-binary @output/manifest.json
# => {"ok":true,"inserted":3,"updated":1,"skipped":0,"total":4}
```
`sync.php` 按 `video_url` 去重：不存在则插入，存在则更新标题/封面。前端 `index.php` 读数据库，自动同步。

> 完整的图文操作步骤见 **[docs/HOW-TO-TRANSCODE-AND-UPLOAD.md](docs/HOW-TO-TRANSCODE-AND-UPLOAD.md)**。

---

## ⌨️ 命令行参考（transcoder）

```bash
# 转换文件夹内全部视频，输出到 out/
python transcoder_gui.py --source D:/videos --output D:/out

# 持续监视（发现新视频自动转）
python transcoder_gui.py --source D:/videos --output D:/out --watch

# 单码率、切片 10s、不生成雪碧图
python transcoder_gui.py --source D:/videos --output D:/out --single --seg 10 --no-sprite

# 写入 CDN 地址 + 自动 SFTP 上传到媒体服务器（以 SSH 密钥登录，无需密码）
python transcoder_gui.py --source D:/videos --output D:/out \
  --media-base https://cdn.example.com \
  --sftp-host cdn.example.com --sftp-user u --sftp-key /path/to/id_ed25519 --sftp-dir /var/www/media --sftp-upload
```

> 命令行参数会覆盖 `config.json` 里的默认值；不传 `--media-base` 时自动使用配置中的媒体域名。

---

## ❓ 常见问题 / FAQ

- **ffmpeg 找不到？** 放进 `transcoder/ffmpeg/`，或加入 PATH，或设环境变量 `FFMPEG_PATH`。
- **打包报 tkinter 缺失？** 用带 tkinter 的 Python（3.13/3.14 官方版）打包；部分精简版发行版不含 tkinter。
- **能放到 Serv00 上跑转码吗？** 不建议。Serv00 为 FreeBSD、无 root、无预装 ffmpeg、内存受限，转码会被杀。
  转码在本地完成，服务器只放 `web/`。
- **为什么站点用 PHP？** 服务器空间（如 Serv00）对 PHP 最省资源：请求级进程、不占常驻名额与端口，且原生支持 `.htaccess`。
- **缩略图有几种？** 封面 `poster.jpg`（10% 处截图）与雪碧图 `thumbnails/sprite.jpg` + `thumbnails.vtt`（每 10s 一帧，播放器可做进度条预览）。

---

## 🗺️ Roadmap

- [ ] 转码任务队列与断点续传
- [ ] Web 端管理员后台（增删改视频、批量导入）
- [ ] 多语言 / 分类 / 标签
- [ ] 转码器支持硬件加速（NVENC / QSV）
- [ ] 会员分级与播放权限

---

## 📄 License

MIT License. 请确保你拥有所托管内容的合法权利，并遵守所在地区的法律法规与托管服务条款。
