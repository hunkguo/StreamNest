<?php
/**
 * 认证核心：注册 / 登录 / 登出 / 会话保护 / CSRF
 */
require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/db.php';

/* ---------- CSRF ---------- */
function csrf_token(): string
{
    if (empty($_SESSION[CSRF_TOKEN_NAME])) {
        $_SESSION[CSRF_TOKEN_NAME] = bin2hex(random_bytes(32));
    }
    return $_SESSION[CSRF_TOKEN_NAME];
}

function csrf_input(): string
{
    $t = csrf_token();
    return '<input type="hidden" name="' . CSRF_TOKEN_NAME . '" value="' . $t . '">';
}

function csrf_check(): bool
{
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') return true;
    $sent = $_POST[CSRF_TOKEN_NAME] ?? '';
    if (!hash_equals($_SESSION[CSRF_TOKEN_NAME] ?? '', $sent)) {
        return false;
    }
    return true;
}

/* ---------- 登录尝试限流（文件级，无需额外表）---------- */
function too_many_attempts(string $key): bool
{
    $file = sys_get_temp_dir() . '/streamnest_login_' . md5($key);
    if (!file_exists($file)) return false;
    $data = json_decode(file_get_contents($file), true) ?: ['n' => 0, 't' => 0];
    if (time() - $data['t'] > LOGIN_LOCK_MINUTES * 60) return false;
    return $data['n'] >= LOGIN_MAX_ATTEMPTS;
}

function register_attempt(string $key)
{
    $file = sys_get_temp_dir() . '/streamnest_login_' . md5($key);
    $data = ['n' => 1, 't' => time()];
    if (file_exists($file)) {
        $d = json_decode(file_get_contents($file), true) ?: ['n' => 0, 't' => 0];
        if (time() - $d['t'] <= LOGIN_LOCK_MINUTES * 60) {
            $data['n'] = $d['n'] + 1;
            $data['t'] = $d['t'];
        }
    }
    file_put_contents($file, json_encode($data), LOCK_EX);
}

function clear_attempts(string $key)
{
    @unlink(sys_get_temp_dir() . '/xyz_login_' . md5($key));
}

/* ---------- 当前用户 ---------- */
function current_user(): ?array
{
    if (empty($_SESSION['user_id'])) return null;
    $pdo = DB::pdo();
    $st = $pdo->prepare('SELECT id,username,email,role,status FROM users WHERE id=? AND status=1');
    $st->execute([$_SESSION['user_id']]);
    return $st->fetch() ?: null;
}

function require_login(): array
{
    $u = current_user();
    if (!$u) {
        header('Location: login.php');
        exit;
    }
    return $u;
}

/* ---------- 注册 ---------- */
function register_user(string $username, string $email, string $password): array
{
    $username = trim($username);
    $email    = trim($email);
    if (mb_strlen($username) < 3) return ['ok' => false, 'msg' => '用户名至少 3 个字符'];
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) return ['ok' => false, 'msg' => '邮箱格式不正确'];
    if (mb_strlen($password) < 8) return ['ok' => false, 'msg' => '密码至少 8 位'];

    $pdo = DB::pdo();
    $st = $pdo->prepare('SELECT id FROM users WHERE username=? OR email=?');
    $st->execute([$username, $email]);
    if ($st->fetch()) return ['ok' => false, 'msg' => '用户名或邮箱已存在'];

    $hash = password_hash($password, PASSWORD_DEFAULT);
    $st = $pdo->prepare('INSERT INTO users(username,email,password_hash) VALUES(?,?,?)');
    $st->execute([$username, $email, $hash]);
    return ['ok' => true, 'user_id' => $pdo->lastInsertId()];
}

/* ---------- 登录 ---------- */
function login_user(string $login, string $password): array
{
    $key = ($_SERVER['REMOTE_ADDR'] ?? 'cli') . '|' . $login;
    if (too_many_attempts($key)) {
        return ['ok' => false, 'msg' => '尝试次数过多，请 ' . LOGIN_LOCK_MINUTES . ' 分钟后再试'];
    }
    $pdo = DB::pdo();
    $st = $pdo->prepare('SELECT * FROM users WHERE (username=? OR email=?) AND status=1');
    $st->execute([$login, $login]);
    $u = $st->fetch();
    if (!$u || !password_verify($password, $u['password_hash'])) {
        register_attempt($key);
        return ['ok' => false, 'msg' => '账号或密码错误'];
    }
    clear_attempts($key);
    session_regenerate_id(true);     // 防会话固定
    $_SESSION['user_id'] = $u['id'];
    $st = $pdo->prepare('UPDATE users SET last_login_at=NOW(), last_login_ip=? WHERE id=?');
    $st->execute([$_SERVER['REMOTE_ADDR'] ?? '', $u['id']]);
    return ['ok' => true, 'user' => $u];
}

function logout()
{
    $_SESSION = [];
    if (ini_get('session.use_cookies')) {
        $p = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000,
            $p['path'], $p['domain'], $p['secure'], $p['httponly']);
    }
    session_destroy();
}
