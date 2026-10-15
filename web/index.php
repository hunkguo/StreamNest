<?php
require_once __DIR__ . '/includes/db.php';
$pageTitle = SITE_NAME . ' · 视频库';

// 搜索
$q = trim($_GET['q'] ?? '');
$page = max(1, (int)($_GET['page'] ?? 1));
$offset = ($page - 1) * ITEMS_PER_PAGE;

$videos = [];
$total = 0;
$dbOk = true;
try {
    $pdo = DB::pdo();
    $where = 'is_active=1';
    $params = [];
    if ($q !== '') {
        $where .= ' AND (title LIKE ? OR description LIKE ?)';
        $params[] = "%$q%";
        $params[] = "%$q%";
    }
    $cnt = $pdo->prepare("SELECT COUNT(*) FROM videos WHERE $where");
    $cnt->execute($params);
    $total = (int)$cnt->fetchColumn();

    $st = $pdo->prepare("SELECT id,title,description,thumbnail FROM videos WHERE $where ORDER BY id DESC LIMIT ? OFFSET ?");
    $i = 1;
    foreach ($params as $p) { $st->bindValue($i++, $p, PDO::PARAM_STR); }
    $st->bindValue($i++, ITEMS_PER_PAGE, PDO::PARAM_INT);
    $st->bindValue($i++, $offset, PDO::PARAM_INT);
    $st->execute();
    $videos = $st->fetchAll();
} catch (Throwable $e) {
    $dbOk = false;   // 未安装/未配置时回退到前端 JS 数据
}
$totalPages = max(1, ceil($total / ITEMS_PER_PAGE));
?>
<?php require __DIR__ . '/includes/header.php'; ?>

  <form class="mb-4" method="get" action="index.php">
    <div class="input-group">
      <input type="text" name="q" class="form-control" placeholder="搜索视频标题/简介" value="<?= htmlspecialchars($q) ?>">
      <button class="btn btn-primary" type="submit"><i class="fas fa-search"></i> 搜索</button>
    </div>
  </form>

  <?php if (!$dbOk): ?>
    <div class="alert alert-warning">数据库尚未初始化，正在展示前端内置数据。请访问 <a href="install.php">install.php</a> 初始化（建表 + 导入视频）。</div>
  <?php endif; ?>

  <div class="row" id="video-container">
    <?php if ($dbOk && !empty($videos)): ?>
      <?php foreach ($videos as $v): ?>
        <div class="col-lg-4 col-md-6 mb-4">
          <div class="card h-100">
            <img src="<?= htmlspecialchars($v['thumbnail']) ?>" class="img-fluid video-thumb card-img-top" loading="lazy" alt="<?= htmlspecialchars($v['title']) ?>">
            <div class="card-body d-flex flex-column">
              <h5 class="card-title"><?= htmlspecialchars($v['title']) ?></h5>
              <p class="card-text text-muted small flex-grow-1"><?= htmlspecialchars(mb_substr($v['description'] ?? '', 0, 80)) ?></p>
              <a href="player.php?id=<?= (int)$v['id'] ?>" class="btn btn-primary mt-2"><i class="fas fa-play"></i> 播放</a>
            </div>
          </div>
        </div>
      <?php endforeach; ?>
    <?php endif; ?>
    <!-- 数据库未就绪时由 app.js 用 video-data.js 兜底渲染 -->
  </div>

  <?php if ($dbOk && $totalPages > 1): ?>
    <nav class="my-4">
      <ul class="pagination justify-content-center">
        <?php for ($i = 1; $i <= $totalPages; $i++): ?>
          <li class="page-item <?= $i === $page ? 'active' : '' ?>">
            <a class="page-link" href="?q=<?= urlencode($q) ?>&page=<?= $i ?>"><?= $i ?></a>
          </li>
        <?php endfor; ?>
      </ul>
    </nav>
  <?php endif; ?>

<?php require __DIR__ . '/includes/footer.php'; ?>
