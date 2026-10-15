把 ffmpeg 的可执行文件放在本目录下：

  ffmpeg/
    ffmpeg.exe      <-- 必需
    ffprobe.exe     <-- 推荐（探测视频信息用，通常随 ffmpeg 一起下载）

下载地址（Windows 静态构建，选“essentials”或“full”均可）：
  https://www.gyan.dev/ffmpeg/builds/  或  https://ffbinaries.com/downloads

放置后：
- 开发运行：python transcoder_gui.py 会自动找到本目录的 ffmpeg
- 打包 exe：运行 build_exe.ps1，ffmpeg.exe 会被打进单文件 exe
- 若未放入，也可把 ffmpeg 所在目录加入系统 PATH，或设置环境变量 FFMPEG_PATH 指向 ffmpeg.exe
