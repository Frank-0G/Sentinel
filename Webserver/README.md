# OpenTTD Chat Log Interface

This directory contains the web-based chat log viewer for OpenTTD Sentinel, allowing server administrators to search and filter chat history, including integrated Discord messages.

## Features

- **Multi-Source Support:** View chat from In-Game, IRC, Admin Console, and **Discord**.
- **Search & Filter:** Filter by Server ID, Player Name, Message Type (Public/Team/Private), Message Content, IP Address, and Company Name.
- **Date Range:** Select specific timeframes for investigation.
- **Export:** Download filtered logs as a text file for offline review.
- **Styling:** Color-coded badges for different sources (Discord in blue/purple) and message types.

## Installation & Configuration

1.  **Database Connection:**
    -   Rename `db_config.example.php` to `db_config.php`.
    -   Edit `db_config.php` and enter your MySQL database credentials:
        ```php
        $db_host = '127.0.0.1';
        $db_name = 'your_db_name';
        $db_user = 'your_db_user';
        $db_pass = 'your_db_password';
        ```

2.  **Web Server Setup:**
    -   Ensure this directory (`Sentinel/Webserver/`) is accessible by your web server (e.g., Apache, Nginx).
    -   Verify that your web server has read access to `db_config.php` and `chat_log_interface.php`.

3.  **Usage:**
    -   Navigate to `http://your-server/path/to/chat_log_interface.php` in your browser.
    -   Use the dropdown menus to filter chats. Specifically for Discord, select **Discord** under the "Source" dropdown.
