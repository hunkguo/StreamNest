<?php
/**
 * 数据同步端点：把本地转码器生成的 manifest.json 导入数据库。
 *
 * 用法（本地转码机上执行）：
 *   curl -X POST "https://site.example.com/sync.php?token=SYNC_TOKEN" \
 *        -H "Content-Type: application/json" \
 *        --data-binary @output/manifest.json
 *
 * 请求体：JSON 数组，每个元素形如
 *   {"base":"xxx","title":"...","description":"...","poster":"https://...",
 *    "video_url":"https://.../index.m3u8","thumbnail":"https://.../poster.jpg"}
 *
 * 鉴权：URL 参数 token 与 config.php 的 SYNC_TOKEN 一致，或已登录管理员。
 */
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/includes/auth.php';

header('Content-Type: application/json; charset=utf-8');

function sync_out(array $arr, int $code = 200): void
{
    http_response_code($code);
    echo json_encode($arr, JSON_UNESCAPED_UNICODE);
    exit;
}

// ---- 鉴权 ----
$token   = $_GET['token'] ?? ($_SERVER['HTTP_X_SYNC_TOKEN'] ?? '');
$isAdmin = false;
$u = current_user();
if ($u && ($u['role'] ?? '') === 'admin') {
    $isAdmin = true;
}
$tokenOk = (SYNC_TOKEN !== '') && is_string($token) && hash_equals(SYNC_TOKEN, $token);
if (!$tokenOk && !$isAdmin) {
    sync_out(['ok' => false, 'error' => 'forbidden：token 不正确，或未以管理员身份登录'], 403);
}

// ---- 解析请求体 ----
$raw = file_get_contents('php://input');
$items = json_decode($raw, true);
if (!is_array($items)) {
    sync_out(['ok' => false, 'error' => '请求体必须是 JSON 数组'], 400);
}

// ---- 导入（按 video_url 去重：存在则更新，不存在则插入）----
try {
    $pdo = DB::pdo();
    $find = $pdo->prepare('SELECT id FROM videos WHERE video_url=? LIMIT 1');
    $ins  = $pdo->prepare(
        'INSERT INTO videos(title,description,thumbnail,video_url,video_type,category,is_active)
         VALUES(?,?,?,?,?,?,1)'
    );
    $upd  = $pdo->prepare(
        'UPDATE videos SET title=?,description=?,thumbnail=?,video_type=? WHERE id=?'
    );

    $inserted = 0; $updated = 0; $skipped = 0;
    foreach ($items as $it) {
        if (empty($it['video_url'])) { $skipped++; continue; }
        $title = (string)($it['title'] ?? ($it['base'] ?? 'Untitled'));
        $desc  = (string)($it['description'] ?? '');
        $thumb = (string)($it['thumbnail'] ?? ($it['poster'] ?? ''));
        $url   = (string)$it['video_url'];
        $type  = (string)($it['video_type'] ?? 'application/x-mpegURL');
        $cat   = (string)($it['category'] ?? '');

        $find->execute([$url]);
        $id = $find->fetchColumn();
        if ($id) {
            $upd->execute([$title, $desc, $thumb, $type, $id]);
            $updated++;
        } else {
            $ins->execute([$title, $desc, $thumb, $url, $type, $cat]);
            $inserted++;
        }
    }
    sync_out([
        'ok' => true,
        'inserted' => $inserted,
        'updated' => $updated,
        'skipped' => $skipped,
        'total' => count($items),
    ]);
} catch (Throwable $e) {
    sync_out(['ok' => false, 'error' => $e->getMessage()], 500);
}
