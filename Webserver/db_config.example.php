<?php
// db_config.php

$db_host = '127.0.0.1';
$db_name = 'openttd_logs'; // Your database name
$db_user = 'openttd_user'; // Your database user
$db_pass = 'your_password_here'; // Your password

try {
    $pdo = new PDO("mysql:host=$db_host;dbname=$db_name;charset=utf8mb4", $db_user, $db_pass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
}
catch (PDOException $e) {
    die("Database Connection Failed: " . $e->getMessage());
}
?>