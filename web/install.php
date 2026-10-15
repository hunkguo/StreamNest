<?php
/**
 * 一键初始化：建表 + 导入 video-data.js 里的视频
 * 安全起见：完成后请删除本文件，或把下方 $ALLOW_INSTALL 设为 false。
 */
require_once __DIR__ . '/config.php';
$ALLOW_INSTALL = true;

$pageTitle = '初始化';
$messages = [];

if (!$ALLOW_INSTALL) {
    die('初始化已关闭。如需重新初始化，请把 install.php 顶部的 $ALLOW_INSTALL 设为 true。');
}

// 内置演示数据（占位示例，地址使用 example.com，部署时请替换为你自己的视频）。
$seed = [
    [1, '示例视频一', '示例简介：这是一段用于演示的占位视频。', 'https://cdn.example.com/sample/demo1/poster.jpg', 'https://cdn.example.com/sample/demo1/index.m3u8'],
    [2, '示例视频二', '示例简介：部署时请替换为你的真实视频数据。', 'https://cdn.example.com/sample/demo2/poster.jpg', 'https://cdn.example.com/sample/demo2/index.m3u8'],
    [3, '示例视频三', '示例简介：可在 web/js/video-data.js 与 install.php 中修改。', 'https://cdn.example.com/sample/demo3/poster.jpg', 'https://cdn.example.com/sample/demo3/index.m3u8'],
];

try {
    $pdo = DB::pdo();
    $pdo->exec("CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role ENUM('user','admin') DEFAULT 'user',
        status TINYINT DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_login_at DATETIME NULL,
        last_login_ip VARCHAR(45) NULL
    )");
    $pdo->exec("CREATE TABLE IF NOT EXISTS videos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        thumbnail VARCHAR(512),
        video_url VARCHAR(1024) NOT NULL,
        video_type VARCHAR(64) DEFAULT 'application/x-mpegURL',
        category VARCHAR(100) DEFAULT '',
        views INT DEFAULT 0,
        is_active TINYINT DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )");
    $pdo->exec("CREATE TABLE IF NOT EXISTS favorites (
        user_id INT, video_id INT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(user_id,video_id),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
    )");
    $pdo->exec("CREATE TABLE IF NOT EXISTS watch_history (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT, video_id INT,
        watched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
    )");
    $messages[] = '数据表创建完成。';

    $cnt = $pdo->query("SELECT COUNT(*) FROM videos")->fetchColumn();
    if ($cnt == 0) {
        $st = $pdo->prepare('INSERT INTO videos(id,title,description,thumbnail,video_url) VALUES(?,?,?,?,?)');
        foreach ($seed as $r) { $st->execute($r); }
        $messages[] = '已导入 ' . count($seed) . ' 个视频。';
    } else {
        $messages[] = 'videos 已存在数据（' . $cnt . ' 条），跳过导入。';
    }
    $messages[] = '初始化成功！请删除或禁用 install.php / check.php。';
} catch (Throwable $e) {
    $messages[] = '错误：' . $e->getMessage();
}
?>
<?php require __DIR__ . '/includes/header.php'; ?>
  <h4>初始化结果</h4>
  <ul class="list-group">
    <?php foreach ($messages as $m): ?><li class="list-group-item"><?= htmlspecialchars($m) ?></li><?php endforeach; ?>
  </ul>
  <a href="index.php" class="btn btn-primary mt-3">进入首页</a>
<?php require __DIR__ . '/includes/footer.php'; ?>
