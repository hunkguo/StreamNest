<?php
/**
 * 站点配置 —— 部署到 Serv00 后按需修改
 *
 * 关于 PHP 版本：
 * Serv00 默认 PHP 8.1，可在 DevilWEB 面板
 *   WWW Websites → 选择你的域名 → Additional settings → PHP version
 * 里切到 8.2 / 8.3 / 8.4。若面板没直接显示当前版本，
 * 访问本目录下的 check.php 即可看到 phpversion() 与已加载扩展。
 *
 * 本代码兼容 PHP 8.0 ~ 8.4，无需改动。
 */

// ---- 数据库（Serv00 面板：MySQL databases 里创建后填这里）----
define('DB_HOST', 'localhost');          // Serv00 多为 localhost
define('DB_NAME', '你的数据库名');
define('DB_USER', '你的数据库用户');
define('DB_PASS', '你的数据库密码');
define('DB_CHARSET', 'utf8mb4');

// ---- 站点（前端域名）----
// 留空则自动探测（适合本地预览）；正式部署建议显式填写。
define('SITE_NAME', 'StreamNest');
define('SITE_URL', 'https://site.example.com');   // ← 前端站点域名（可改）
define('ITEMS_PER_PAGE', 12);

// ---- 媒体 CDN（视频与缩略图所在服务器，与前端不同域）----
// 转码器上传 m3u8/切片/封面到这里；前端只存 URL，不从本站读流。
define('MEDIA_BASE', 'https://cdn.example.com');   // ← 媒体域名（可改）

// ---- 数据同步令牌（本地转码机调用 web/sync.php 时携带）----
// 建议改成一串随机字符；留空则只有管理员登录后才能同步。
define('SYNC_TOKEN', '');

// ---- 会话安全 ----
define('SESSION_NAME', 'streamnest_session');
define('CSRF_TOKEN_NAME', 'csrf_token');
define('LOGIN_MAX_ATTEMPTS', 5);         // 同一 IP+账号 5 次锁定
define('LOGIN_LOCK_MINUTES', 15);

// 启动会话（在所有输出之前）
if (session_status() === PHP_SESSION_NONE) {
    ini_set('session.cookie_httponly', 1);
    ini_set('session.cookie_samesite', 'Lax');
    if (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') {
        ini_set('session.cookie_secure', 1);
    }
    session_name(SESSION_NAME);
    session_start();
}
