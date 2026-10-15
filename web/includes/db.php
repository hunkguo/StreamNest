<?php
/**
 * PDO 数据库连接（单例）
 */
require_once __DIR__ . '/../config.php';

class DB
{
    private static ?PDO $pdo = null;

    public static function pdo(): PDO
    {
        if (self::$pdo === null) {
            $dsn = sprintf(
                'mysql:host=%s;dbname=%s;charset=%s',
                DB_HOST, DB_NAME, DB_CHARSET
            );
            $options = [
                PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES   => false,   // 真实预处理，防注入
                PDO::MYSQL_ATTR_FOUND_ROWS   => true,
            ];
            try {
                self::$pdo = new PDO($dsn, DB_USER, DB_PASS, $options);
            } catch (PDOException $e) {
                // 生产环境不要暴露真实错误信息
                http_response_code(500);
                error_log('DB connect failed: ' . $e->getMessage());
                die('数据库连接失败，请检查 web/config.php 中的数据库配置。');
            }
        }
        return self::$pdo;
    }
}
