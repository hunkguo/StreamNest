<?php
require_once __DIR__ . '/auth.php';
$user = current_user();
$pageTitle = $pageTitle ?? SITE_NAME;
?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
  <title><?= htmlspecialchars($pageTitle) ?></title>
  <link rel="icon" href="img/favicon.ico" type="image/x-icon" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
  <link rel="stylesheet" href="css/mdb.min.css" />
  <link href="https://vjs.zencdn.net/8.10.0/video-js.css" rel="stylesheet" />
  <link href="css/styles.css" rel="stylesheet" />
  <style>
    .video-thumb { aspect-ratio: 16/9; object-fit: cover; width: 100%; }
    .card-title { font-size: 1rem; }
  </style>
</head>
<body>
<header>
  <nav class="navbar navbar-expand-lg navbar-dark" style="z-index:2000; background:#1c2331;">
    <div class="container-fluid">
      <a class="navbar-brand" href="index.php"><strong><?= htmlspecialchars(SITE_NAME) ?></strong></a>
      <button class="navbar-toggler" type="button" data-mdb-toggle="collapse" data-mdb-target="#navMain"
              aria-controls="navMain" aria-expanded="false" aria-label="Toggle navigation">
        <i class="fas fa-bars"></i>
      </button>
      <div class="collapse navbar-collapse" id="navMain">
        <ul class="navbar-nav me-auto mb-2 mb-lg-0">
          <li class="nav-item"><a class="nav-link" href="index.php">首页</a></li>
        </ul>
        <ul class="navbar-nav list-inline">
          <?php if ($user): ?>
            <li class="nav-item"><a class="nav-link" href="account.php"><i class="fas fa-user"></i> <?= htmlspecialchars($user['username']) ?></a></li>
            <li class="nav-item">
              <form method="post" action="logout.php" style="display:inline;">
                <?= csrf_input() ?>
                <button class="btn btn-link nav-link" type="submit">退出</button>
              </form>
            </li>
          <?php else: ?>
            <li class="nav-item"><a class="nav-link" href="login.php"><i class="fas fa-sign-in-alt"></i> 登录</a></li>
          <?php endif; ?>
        </ul>
      </div>
    </div>
  </nav>
</header>
<main class="mt-4">
  <div class="container">
