<?php
require_once __DIR__ . '/includes/db.php';
$pageTitle = '播放';

$id = isset($_GET['id']) ? (int)$_GET['id'] : 0;
$video = null;
try {
    $pdo = DB::pdo();
    $st = $pdo->prepare('SELECT * FROM videos WHERE id=? AND is_active=1');
    $st->execute([$id]);
    $video = $st->fetch();
    if ($video) {
        $pdo->prepare('UPDATE videos SET views = views + 1 WHERE id=?')->execute([$id]);
        if (!empty($_SESSION['user_id'])) {
            $pdo->prepare('INSERT IGNORE INTO watch_history(user_id,video_id) VALUES(?,?)')
                ->execute([$_SESSION['user_id'], $id]);
        }
    }
} catch (Throwable $e) { /* 回退到 JS */ }
?>
<?php require __DIR__ . '/includes/header.php'; ?>

  <?php if ($video): ?>
    <h3 id="video-title"><?= htmlspecialchars($video['title']) ?></h3>
    <p id="video-desc" class="text-muted"><?= htmlspecialchars($video['description'] ?? '') ?></p>
    <div class="ratio ratio-16x9">
      <video id="player" class="video-js vjs-big-play-centered" controls preload="auto" poster="<?= htmlspecialchars($video['thumbnail']) ?>">
        <source src="<?= htmlspecialchars($video['video_url']) ?>" type="application/x-mpegURL" />
        <p class="vjs-no-js">您的浏览器不支持 HTML5 视频。</p>
      </video>
    </div>
    <script>
      window.__CURRENT_VIDEO__ = <?= json_encode([
          'id' => $video['id'],
          'title' => $video['title'],
          'videoUrl' => $video['video_url'],
          'type' => $video['video_type'] ?? 'application/x-mpegURL'
      ], JSON_UNESCAPED_UNICODE) ?>;
    </script>
  <?php else: ?>
    <div class="alert alert-info">未找到该视频，或数据库尚未初始化（先用 install.php 导入数据）。</div>
  <?php endif; ?>

<?php require __DIR__ . '/includes/footer.php'; ?>
