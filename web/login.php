<?php
require_once __DIR__ . '/includes/auth.php';
$pageTitle = '登录 / 注册';

$error = '';
$success = '';
$mode = $_GET['mode'] ?? 'login';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!csrf_check()) {
        $error = '表单已过期，请重试';
    } elseif (isset($_POST['register'])) {
        $r = register_user($_POST['username'] ?? '', $_POST['email'] ?? '', $_POST['password'] ?? '');
        if ($r['ok']) {
            $login = login_user($_POST['username'], $_POST['password']);
            header('Location: index.php');
            exit;
        }
        $error = $r['msg'];
        $mode = 'register';
    } elseif (isset($_POST['login'])) {
        $login = login_user($_POST['login'] ?? '', $_POST['password'] ?? '');
        if ($login['ok']) {
            header('Location: index.php');
            exit;
        }
        $error = $login['msg'];
        $mode = 'login';
    }
}
?>
<?php require __DIR__ . '/includes/header.php'; ?>

  <div class="row justify-content-center">
    <div class="col-md-6">
      <ul class="nav nav-tabs mb-3">
        <li class="nav-item">
          <a class="nav-link <?= $mode === 'login' ? 'active' : '' ?>" href="login.php?mode=login">登录</a>
        </li>
        <li class="nav-item">
          <a class="nav-link <?= $mode === 'register' ? 'active' : '' ?>" href="login.php?mode=register">注册</a>
        </li>
      </ul>

      <?php if ($error): ?><div class="alert alert-danger"><?= htmlspecialchars($error) ?></div><?php endif; ?>

      <?php if ($mode === 'login'): ?>
        <form method="post">
          <?= csrf_input() ?>
          <div class="form-outline mb-3">
            <input type="text" name="login" class="form-control" required>
            <label class="form-label">用户名或邮箱</label>
          </div>
          <div class="form-outline mb-3">
            <input type="password" name="password" class="form-control" required>
            <label class="form-label">密码</label>
          </div>
          <button name="login" class="btn btn-primary btn-block" type="submit">登录</button>
        </form>
      <?php else: ?>
        <form method="post">
          <?= csrf_input() ?>
          <div class="form-outline mb-3">
            <input type="text" name="username" class="form-control" required minlength="3">
            <label class="form-label">用户名（≥3位）</label>
          </div>
          <div class="form-outline mb-3">
            <input type="email" name="email" class="form-control" required>
            <label class="form-label">邮箱</label>
          </div>
          <div class="form-outline mb-3">
            <input type="password" name="password" class="form-control" required minlength="8">
            <label class="form-label">密码（≥8位）</label>
          </div>
          <button name="register" class="btn btn-success btn-block" type="submit">注册并登录</button>
        </form>
      <?php endif; ?>
    </div>
  </div>

<?php require __DIR__ . '/includes/footer.php'; ?>
