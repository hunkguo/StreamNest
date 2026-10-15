"""轮询式目录监视（不依赖 watchdog，方便 PyInstaller 打包）。

原理：每隔 interval 秒扫描一次源目录，发现新的视频文件后，
等其大小/mtime 稳定（连续两轮一致）再判定为完整文件，
通过回调交给上层转换，避免转换未写完的文件。
"""
import os
import time
import threading

from ffmpeg_util import VIDEO_EXTS


class FolderWatcher:
    def __init__(self, source_dir, on_new_file, interval=5, extensions=None):
        self.source_dir = source_dir
        self.on_new_file = on_new_file
        self.interval = interval
        self.extensions = {e.lower() for e in (extensions or VIDEO_EXTS)}
        self._stop = threading.Event()
        self._thread = None
        self._stable = {}      # path -> (size, mtime) 上一轮快照
        self._processed = set()  # 已触发过的文件，避免重复

    def _is_video(self, path):
        return os.path.splitext(path)[1].lower() in self.extensions

    def _scan_once(self):
        try:
            names = os.listdir(self.source_dir)
        except FileNotFoundError:
            return
        for name in names:
            p = os.path.join(self.source_dir, name)
            if not os.path.isfile(p) or not self._is_video(p):
                continue
            if p in self._processed:
                continue
            try:
                st = os.stat(p)
            except OSError:
                continue
            key = (st.st_size, int(st.st_mtime))
            prev = self._stable.get(p)
            if prev is not None and prev == key:
                self._stable[p] = key
                self._processed.add(p)
                try:
                    self.on_new_file(p)
                except Exception as e:   # 回调异常不应中断监视循环
                    print("on_new_file error:", e)
            else:
                self._stable[p] = key

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop.is_set():
            self._scan_once()
            self._stop.wait(self.interval)

    def stop(self):
        self._stop.set()

    def is_running(self):
        return bool(self._thread and self._thread.is_alive())
