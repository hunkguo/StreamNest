# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置
# 使用系统 Python 3.14（自带 tkinter）构建，避免使用缺模块的托管 Python。
# ffmpeg/ffmpeg.exe 若存在则一并打进 exe；否则需把 ffmpeg.exe 放到程序旁 ffmpeg/ 目录。
import os

# 打包时把本地 ffmpeg/ 下的 ffmpeg.exe 与 ffprobe.exe 一并打进 exe，
# 运行时解压到 _MEIPASS/ffmpeg/，find_binary() 会优先在此查找。
ffmpeg_local = os.path.join("ffmpeg", "ffmpeg.exe")
ffprobe_local = os.path.join("ffmpeg", "ffprobe.exe")
binaries = []
if os.path.isfile(ffmpeg_local):
    binaries.append((ffmpeg_local, "ffmpeg"))
if os.path.isfile(ffprobe_local):
    binaries.append((ffprobe_local, "ffmpeg"))

# 把默认配置打进 exe，用户可在 exe 同级放 config.local.json 覆盖
config_json = os.path.join(os.path.dirname(os.path.abspath("config.json")), "config.json")
datas = [(config_json, ".")] if os.path.isfile(config_json) else []

a = Analysis(
    ["transcoder_gui.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        "tkinter", "tkinter.ttk",
        "hls_converter", "folder_watcher", "ffmpeg_util", "publish", "appconfig",
        # SFTP 上传器在运行时才 import paramiko，需显式声明以便打包
        "paramiko", "paramiko.RSAKey", "paramiko.Ed25519Key",
        "paramiko.ECDSAKey", "paramiko.DSSKey",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Transcoder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # 图形界面，无控制台窗口
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
