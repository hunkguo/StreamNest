<?php
/**
 * 环境自检 —— 部署后直接访问 /check.php 查看 PHP 版本与扩展
 * 上线后请删除本文件，避免泄露环境信息。
 */
header('Content-Type: text/plain; charset=utf-8');
echo "PHP 版本: " . phpversion() . "  (PHP_VERSION_ID=" . PHP_VERSION_ID . ")\n";
echo "SAPI: " . php_sapi_name() . "\n";
echo "操作系统: " . PHP_OS . "\n";
echo "--- 关键扩展 ---\n";
foreach (['pdo_mysql', 'json', 'session', 'openssl', 'mbstring', 'gd'] as $ext) {
    echo str_pad($ext, 12) . (extension_loaded($ext) ? "OK" : "缺失!!!") . "\n";
}
echo "--- 目录可写性 ---\n";
echo "sys_get_temp_dir: " . sys_get_temp_dir() . " -> " . (is_writable(sys_get_temp_dir()) ? "可写" : "不可写") . "\n";
echo "--- 建议 ---\n";
echo "Serv00 面板中 PHP 版本可在 DevilWEB → WWW Websites → 域名 → Additional settings → PHP version 切换（推荐 8.3/8.4）。\n";
echo "本程序兼容 8.0~8.4，无需改动。\n";
