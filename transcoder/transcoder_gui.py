"""transcoder 主程序：将文件夹下的视频自动转为 m3u8 + 缩略图，并可选发布。

- 图形界面（tkinter）：选源/输出目录、设置选项、手动转换或监视模式
- 发布：生成 meta.json / manifest.json；可选自动上传到媒体服务器（SFTP/FTP/none）
- 命令行：python transcoder_gui.py --source <dir> --output <dir> [--watch]

打包为 exe 后，ffmpeg 需放在程序旁 ffmpeg/ffmpeg.exe（或系统 PATH）。
"""
import os
import sys
import queue
import threading

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox

import hls_converter
import folder_watcher
import publish
import appconfig
from ffmpeg_util import get_ffmpeg, find_binary


class App:
    def __init__(self, root):
        self.root = root
        root.title("StreamNest 转码器 · m3u8 + 缩略图")
        root.geometry("900x720")

        self.cfg = appconfig.load_config()
        self.queue = queue.Queue()          # 子线程 -> 主线程 消息
        self.task_queue = queue.Queue()     # 待转换文件路径
        self.worker = None
        self.watcher = None
        self.watching = False

        self._build_ui()
        self._check_ffmpeg()
        self.root.after(100, self._poll_queue)

    # ---------------- UI ----------------
    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill="x")

        ttk.Label(frm, text="源文件夹：").grid(row=0, column=0, sticky="w")
        self.src_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.src_var, width=58).grid(row=0, column=1)
        ttk.Button(frm, text="浏览", command=self._pick_src).grid(row=0, column=2, padx=4)

        ttk.Label(frm, text="输出文件夹：").grid(row=1, column=0, sticky="w")
        self.out_var = tk.StringVar(value=os.path.join(os.getcwd(), "output"))
        ttk.Entry(frm, textvariable=self.out_var, width=58).grid(row=1, column=1)
        ttk.Button(frm, text="浏览", command=self._pick_out).grid(row=1, column=2, padx=4)

        # 转换选项
        opt = ttk.LabelFrame(self.root, text="转换选项", padding=10)
        opt.pack(fill="x", padx=10, pady=5)
        self.mode_var = tk.StringVar(value=self.cfg["convert"].get("preset", "multi"))
        ttk.Radiobutton(opt, text="多码率(3档)", variable=self.mode_var,
                        value="multi").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(opt, text="单码率", variable=self.mode_var,
                        value="single").grid(row=0, column=1, sticky="w")
        ttk.Label(opt, text="切片时长(s)：").grid(row=0, column=2, sticky="w")
        self.seg_var = tk.StringVar(value=str(self.cfg["convert"].get("seg_len", 6)))
        ttk.Entry(opt, textvariable=self.seg_var, width=6).grid(row=0, column=3)
        self.poster_var = tk.BooleanVar(value=bool(self.cfg["convert"].get("poster", True)))
        ttk.Checkbutton(opt, text="生成封面图", variable=self.poster_var
                        ).grid(row=1, column=0, sticky="w")
        self.sprite_var = tk.BooleanVar(value=bool(self.cfg["convert"].get("sprite", True)))
        ttk.Checkbutton(opt, text="生成雪碧图+VTT", variable=self.sprite_var
                        ).grid(row=1, column=1, sticky="w")
        self.watch_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt, text="监视模式(自动转新文件)", variable=self.watch_var
                        ).grid(row=1, column=2, sticky="w")

        # 发布选项
        pub = ttk.LabelFrame(self.root, text="发布（meta.json / 上传到媒体服务器）", padding=10)
        pub.pack(fill="x", padx=10, pady=5)
        ttk.Label(pub, text="媒体基地址：").grid(row=0, column=0, sticky="w")
        self.media_var = tk.StringVar(value=appconfig.get_media_base(self.cfg))
        ttk.Entry(pub, textvariable=self.media_var, width=45).grid(row=0, column=1, columnspan=3, sticky="w")

        _up = self.cfg.get("upload", {})
        ttk.Label(pub, text="上传方式：").grid(row=1, column=0, sticky="w")
        self.up_method = tk.StringVar(value=_up.get("method", "sftp"))
        ttk.Combobox(pub, textvariable=self.up_method, width=10, state="readonly",
                     values=["sftp", "none"]).grid(row=1, column=1, sticky="w")
        ttk.Label(pub, text="主机：").grid(row=1, column=2, sticky="e")
        self.up_host = tk.StringVar(value=_up.get("host", ""))
        ttk.Entry(pub, textvariable=self.up_host, width=20).grid(row=1, column=3, sticky="w")

        ttk.Label(pub, text="端口：").grid(row=2, column=0, sticky="w")
        self.up_port = tk.StringVar(value=str(_up.get("port", 22)))
        ttk.Entry(pub, textvariable=self.up_port, width=8).grid(row=2, column=1, sticky="w")
        ttk.Label(pub, text="用户：").grid(row=2, column=2, sticky="e")
        self.up_user = tk.StringVar(value=_up.get("user", ""))
        ttk.Entry(pub, textvariable=self.up_user, width=20).grid(row=2, column=3, sticky="w")

        ttk.Label(pub, text="密码：").grid(row=3, column=0, sticky="w")
        self.up_pass = tk.StringVar(value=_up.get("password", ""))
        ttk.Entry(pub, textvariable=self.up_pass, width=18, show="*").grid(row=3, column=1, sticky="w")
        ttk.Label(pub, text="远程目录：").grid(row=3, column=2, sticky="e")
        self.up_dir = tk.StringVar(value=_up.get("remote_dir", "/"))
        ttk.Entry(pub, textvariable=self.up_dir, width=20).grid(row=3, column=3, sticky="w")

        ttk.Label(pub, text="密钥文件：").grid(row=4, column=0, sticky="w")
        self.up_key = tk.StringVar(value=_up.get("key_file", ""))
        ttk.Entry(pub, textvariable=self.up_key, width=18).grid(row=4, column=1, sticky="w")
        ttk.Button(pub, text="浏览", command=self._pick_key).grid(row=4, column=2, sticky="w")
        self.up_on = tk.BooleanVar(value=bool(_up.get("enabled", False)))
        ttk.Checkbutton(pub, text="转码后自动上传", variable=self.up_on
                        ).grid(row=4, column=3, sticky="w")

        # 按钮
        btn = ttk.Frame(self.root, padding=10)
        btn.pack(fill="x")
        ttk.Button(btn, text="转换源文件夹内全部", command=self._start_all
                   ).grid(row=0, column=0, padx=4)
        self.watch_btn = ttk.Button(btn, text="开始监视", command=self._toggle_watch)
        self.watch_btn.grid(row=0, column=1, padx=4)
        ttk.Button(btn, text="打开输出目录", command=self._open_out
                   ).grid(row=0, column=2, padx=4)

        self.prog = ttk.Progressbar(self.root, length=100, mode="determinate")
        self.prog.pack(fill="x", padx=10, pady=6)
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(self.root, textvariable=self.status_var).pack(anchor="w", padx=10)

        self.log = scrolledtext.ScrolledText(self.root, height=18, state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=6)

    # ---------------- 文件选择 ----------------
    def _pick_src(self):
        d = filedialog.askdirectory(title="选择源文件夹")
        if d:
            self.src_var.set(d)

    def _pick_out(self):
        d = filedialog.askdirectory(title="选择输出文件夹")
        if d:
            self.out_var.set(d)

    def _pick_key(self):
        f = filedialog.askopenfilename(
            title="选择 SSH 私钥文件",
            filetypes=[("私钥", "*.pem *.key *.ppk *.rsa *.ed25519"), ("所有文件", "*.*")])
        if f:
            self.up_key.set(f)

    def _open_out(self):
        out = self.out_var.get()
        if os.path.isdir(out):
            if sys.platform == "win32":
                os.startfile(out)
            else:
                os.system('open "%s"' % out)

    # ---------------- ffmpeg 检测 ----------------
    def _check_ffmpeg(self):
        p = find_binary("ffmpeg")
        if p:
            self._log("ffmpeg 已就绪：%s" % p)
        else:
            self._log("⚠ 未找到 ffmpeg！请将 ffmpeg.exe 放到 ffmpeg/ 子目录或加入 PATH。")

    # ---------------- 手动转换 ----------------
    def _start_all(self):
        src = self.src_var.get()
        out = self.out_var.get()
        if not src or not os.path.isdir(src):
            messagebox.showwarning("提示", "请先选择有效的源文件夹。")
            return
        os.makedirs(out, exist_ok=True)
        files = [os.path.join(src, f) for f in os.listdir(src)
                 if os.path.isfile(os.path.join(src, f))
                 and os.path.splitext(f)[1].lower() in folder_watcher.VIDEO_EXTS]
        if not files:
            messagebox.showinfo("提示", "源文件夹内没有可转换的视频文件。")
            return
        for f in files:
            self.task_queue.put(f)
        self._ensure_worker()
        self._log("已加入 %d 个文件到转换队列。" % len(files))

    def _ensure_worker(self):
        if self.worker and self.worker.is_alive():
            return
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

    def _worker_loop(self):
        while True:
            try:
                path = self.task_queue.get(timeout=1)
            except queue.Empty:
                if self.task_queue.empty():
                    return
                continue
            if not path:
                return
            try:
                self._convert_one(path)
            except Exception as e:
                self.queue.put(("log", "[错误] %s : %s" % (path, e)))
            self.task_queue.task_done()

    def _convert_one(self, path):
        base = os.path.basename(path)
        self.queue.put(("status", "转换中：%s" % base))
        self.queue.put(("progress", 0))
        out_root = self.out_var.get()
        result = hls_converter.convert(
            path, out_root,
            preset=self.mode_var.get(),
            seg_len=int(self.seg_var.get() or 6),
            make_poster_img=self.poster_var.get(),
            make_sprite_img=self.sprite_var.get(),
            log_cb=lambda m: self.queue.put(("log", m)),
            progress_cb=lambda v: self.queue.put(("progress", v)),
            media_base=self.media_var.get().strip(),
        )
        # 写 manifest.json
        if result.get("meta"):
            mp = publish.append_manifest(out_root, result["meta"])
            self.queue.put(("log", "[清单] 已更新 %s" % mp))
        # 可选上传到媒体服务器（SFTP / FTP / none）
        if self.up_on.get() and self.up_method.get() != "none":
            self.queue.put(("status", "上传中：%s" % base))
            up = publish.make_uploader({
                "method": self.up_method.get(),
                "host": self.up_host.get().strip(),
                "port": int(self.up_port.get() or 22),
                "user": self.up_user.get().strip(),
                "password": self.up_pass.get(),
                "key_file": self.up_key.get().strip(),
                "remote_dir": self.up_dir.get() or "/",
            })
            if up and publish.upload_ready(up):
                up.upload_dir(result["dir"], remote_sub=result["base"],
                              log_cb=lambda m: self.queue.put(("log", m)))
            else:
                self.queue.put(("log", "[跳过] 上传未配置完整（请填主机与用户名）"))
        self.queue.put(("progress", 100))

    # ---------------- 监视模式 ----------------
    def _toggle_watch(self):
        if self.watching:
            if self.watcher:
                self.watcher.stop()
            self.watching = False
            self.watch_btn.config(text="开始监视")
            self.queue.put(("status", "监视已停止"))
            self.queue.put(("log", "监视已停止。"))
            return
        src = self.src_var.get()
        out = self.out_var.get()
        if not src or not os.path.isdir(src):
            messagebox.showwarning("提示", "请先选择有效的源文件夹。")
            return
        os.makedirs(out, exist_ok=True)
        self.watcher = folder_watcher.FolderWatcher(
            src, on_new_file=lambda p: self.task_queue.put(p), interval=5)
        self.watcher.start()
        self._ensure_worker()
        self.watching = True
        self.watch_btn.config(text="停止监视")
        self.queue.put(("status", "监视中：%s" % src))
        self.queue.put(("log", "开始监视 %s，发现新视频将自动转换。" % src))

    # ---------------- 日志/进度桥接 ----------------
    def _log(self, msg):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _poll_queue(self):
        try:
            while True:
                kind, val = self.queue.get_nowait()
                if kind == "log":
                    self._log(val)
                elif kind == "progress":
                    self.prog["value"] = val
                elif kind == "status":
                    self.status_var.set(val)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)


def run_cli(source, output, watch, preset, seg_len, poster, sprite,
            media_base, upload=None):
    """命令行模式。upload 为 dict 或 None。"""
    os.makedirs(output, exist_ok=True)
    try:
        get_ffmpeg()
    except FileNotFoundError as e:
        print("错误：", e)
        sys.exit(1)

    def do_convert(path):
        try:
            print(">>> 转换：", path)
            result = hls_converter.convert(
                path, output, preset=preset, seg_len=seg_len,
                make_poster_img=poster, make_sprite_img=sprite,
                log_cb=lambda m: print("   ", m),
                media_base=media_base,
            )
            if result.get("meta"):
                mp = publish.append_manifest(output, result["meta"])
                print("    清单已更新：", mp)
            if upload and publish.upload_ready(publish.make_uploader(upload)):
                print(">>> 上传：", result["base"])
                up = publish.make_uploader(upload)
                up.upload_dir(result["dir"], remote_sub=result["base"],
                              log_cb=lambda m: print("   ", m))
        except Exception as e:
            print("   失败：", e)

    if watch:
        w = folder_watcher.FolderWatcher(source, on_new_file=do_convert, interval=5)
        w.start()
        print("监视模式已启动，按 Ctrl+C 退出。")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            w.stop()
            print("已停止。")
    else:
        files = [os.path.join(source, f) for f in os.listdir(source)
                 if os.path.isfile(os.path.join(source, f))
                 and os.path.splitext(f)[1].lower() in folder_watcher.VIDEO_EXTS]
        if not files:
            print("源文件夹内没有可转换的视频文件。")
            return
        for f in files:
            do_convert(f)
        print("全部完成，输出目录：", output)


def main():
    args = sys.argv[1:]
    if any(a in ("-h", "--help") for a in args):
        print(__doc__)
        return
    source = output = None
    watch = False
    cfg = appconfig.load_config()
    conv = cfg.get("convert", {})
    preset = conv.get("preset", "multi")
    seg_len = int(conv.get("seg_len", 6))
    poster = bool(conv.get("poster", True))
    sprite = bool(conv.get("sprite", True))
    media_base = appconfig.get_media_base(cfg)
    upload = dict(cfg.get("upload", {}))
    upload_enabled = bool(upload.get("enabled", False))

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--source":
            source = args[i + 1]; i += 2; continue
        if a == "--output":
            output = args[i + 1]; i += 2; continue
        if a == "--watch":
            watch = True; i += 1; continue
        if a == "--single":
            preset = "single"; i += 1; continue
        if a == "--seg":
            seg_len = int(args[i + 1]); i += 2; continue
        if a == "--no-poster":
            poster = False; i += 1; continue
        if a == "--no-sprite":
            sprite = False; i += 1; continue
        if a == "--media-base":
            media_base = args[i + 1]; i += 2; continue
        if a == "--sftp-host":
            upload["host"] = args[i + 1]; i += 2; continue
        if a == "--sftp-user":
            upload["user"] = args[i + 1]; i += 2; continue
        if a == "--sftp-pass":
            upload["password"] = args[i + 1]; i += 2; continue
        if a == "--sftp-port":
            upload["port"] = int(args[i + 1]); i += 2; continue
        if a == "--sftp-dir":
            upload["remote_dir"] = args[i + 1]; i += 2; continue
        if a == "--sftp-key":
            upload["key_file"] = args[i + 1]; i += 2; continue
        if a == "--sftp-upload":
            upload_enabled = True; i += 1; continue
        i += 1

    if source and output:
        if upload_enabled:
            upload["enabled"] = True
        do_upload = upload_enabled and appconfig.upload_ready(upload)
        if upload_enabled and not appconfig.upload_ready(upload):
            print("[提示] 启用了上传，但主机或用户名为空，已跳过上传。")
        run_cli(source, output, watch, preset, seg_len, poster, sprite,
                media_base, upload if do_upload else None)
        return

    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
