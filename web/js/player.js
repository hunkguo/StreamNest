// 播放器逻辑：video.js + hls.js 兜底解封装；Safari/iOS 走原生 HLS
document.addEventListener('DOMContentLoaded', function () {
    var el = document.getElementById('player');
    if (!el) return;

    var data = window.__CURRENT_VIDEO__;
    if (!data) {
        var params = new URLSearchParams(window.location.search);
        var vid = parseInt(params.get('id'), 10);
        if (typeof videoData !== 'undefined') {
            data = videoData.find(function (v) { return v.id === vid; });
        }
    }
    if (!data) return;

    document.title = data.title;
    var t = document.getElementById('video-title');
    var d = document.getElementById('video-desc');
    if (t) t.textContent = data.title;
    if (d) d.textContent = data.description || '';

    var player = videojs('player');
    var src = data.videoUrl;
    var type = data.type || 'application/x-mpegURL';

    if (window.Hls && window.Hls.isSupported()) {
        var hls = new window.Hls({ maxBufferLength: 30 });
        hls.loadSource(src);
        hls.attachMedia(el);
        hls.on(window.Hls.Events.ERROR, function (evt, data2) {
            if (data2.fatal) {
                if (data2.type === window.Hls.ErrorTypes.NETWORK_ERROR) hls.startLoad();
                else if (data2.type === window.Hls.ErrorTypes.MEDIA_ERROR) hls.recoverMediaError();
                else hls.destroy();
            }
        });
    } else if (el.canPlayType(type)) {
        // Safari / iOS 原生支持 HLS，video.js 直接放行
        player.src({ type: type, src: src });
        player.ready(function () { player.play(); });
    }
});
