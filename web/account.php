<?php
require_once __DIR__ . '/includes/auth.php';
$pageTitle = '个人中心';
$user = require_login();

// 收藏
$favs = [];
$history = [];
try {
    $pdo = DB::pdo();
    $favs = $pdo->prepare(
        'SELECT v.id,v.title,v.thumbnail FROM favorites f JOIN videos v ON v.id=f.video_id WHERE f.user_id=? ORDER BY f.created_at DESC'
    );
    $favs->execute([$user['id']]);
    $favs = $favs->fetchAll();

    $history = $pdo->prepare(
        'SELECT v.id,v.title,v.thumbnail,wh.watched_at FROM watch_history wh JOIN videos v ON v.id=wh.video_id WHERE wh.user_id=? ORDER BY wh.watched_at DESC LIMIT 20'
    );
    $history->execute([$user['id']]);
    $history = $history->fetchAll();
} catch (Throwable $e) { }
?>
<?php require __DIR__ . '/includes/header.php'; ?>

  <h4>欢迎，<?= htmlspecialchars($user['username']) ?></h4>
  <p class="text-muted">邮箱：<?= htmlspecialchars($user['email']) ?> ｜ 角色：<?= htmlspecialchars($user['role']) ?></p>

  <h5 class="mt-4">我的收藏</h5>
  <?php if (empty($favs)): ?><p class="text-muted">还没有收藏。</p><?php endif; ?>
  <div class="row">
    <?php foreach ($favs as $v): ?>
      <div class="col-lg-3 col-md-4 mb-3">
        <a href="player.php?id=<?= $v['id'] ?>">
          <img src="<?= htmlspecialchars($v['thumbnail']) ?>" loading="lazy" class="img-fluid video-thumb card-img-top rounded">
          <div class="small mt-1"><?= htmlspecialchars($v['title']) ?></div>
        </a>
      </div>
    <?php endforeach; ?>
  </div>

  <h5 class="mt-4">观看历史</h5>
  <?php if (empty($history)): ?><p class="text-muted">暂无记录。</p><?php endif; ?>
  <ul class="list-group">
    <?php foreach ($history as $h): ?>
      <li class="list-group-item d-flex justify-content-between">
        <a href="player.php?id=<?= $h['id'] ?>"><?= htmlspecialchars($h['title']) ?></a>
        <span class="text-muted small"><?= $h['watched_at'] ?></span>
      </li>
    <?php endforeach; ?>
  </ul>

<?php require __DIR__ . '/includes/footer.php'; ?>
