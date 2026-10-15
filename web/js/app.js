// 数据库未就绪时的兜底渲染（与 index.php 后端逻辑一致）
(function () {
    var container = document.getElementById('video-container');
    if (!container) return;
    // 若后端已渲染卡片（有内容），则不重复渲染
    if (container.children.length > 0) return;
    if (typeof videoData === 'undefined') return;

    videoData.forEach(function (v) {
        var col = document.createElement('div');
        col.className = 'col-lg-4 col-md-6 mb-4';
        col.innerHTML =
            '<div class="card h-100">' +
            '<img src="' + v.thumbnail + '" class="img-fluid video-thumb card-img-top" loading="lazy" alt="' + v.title + '">' +
            '<div class="card-body d-flex flex-column">' +
            '<h5 class="card-title">' + v.title + '</h5>' +
            '<p class="card-text text-muted small flex-grow-1">' + (v.description || '').substring(0, 80) + '</p>' +
            '<a href="player.php?id=' + v.id + '" class="btn btn-primary mt-2"><i class="fas fa-play"></i> 播放</a>' +
            '</div></div>';
        container.appendChild(col);
    });
})();
