# OpenTTD Sentinel Controller

Sentinel is a powerful, modular, event-driven Python controller designed for OpenTTD servers. It interfaces with the OpenTTD Admin Port to provide advanced administration capabilities, automated tasks, database integration, and community feature synchronization.

It features a robust **Plugin Architecture**, allowing developers to easily extend functionality or disable unneeded features.

## 🚀 Features

Sentinel comes with a suite of built-in plugins covering a wide range of functionality:

### Core Administration
*   **Sentinel Core**: The micro-kernel that manages the Admin Port connection and plugin lifecycle.
*   **Command Manager**: Handles in-game commands (e.g., `!help`, `!reset`) with a permission system.
*   **Admin Login**: Secure login system for administrators using tokens or passwords.
*   **Data Controller**: Real-time tracking of clients, companies, and server stats.
*   **Auto Restart**: Automates server restarts on a schedule.
*   **Anti Flood**: Prevents chat spam and command flooding.

### Integration & Connectivity
*   **MySQL Service**: Centralized, threaded MySQL connection pooling for all plugins.
*   **IRC Bridge**: Two-way chat sync between the game server and IRC channels (with color support).
*   **GameScript Connector**: seamlessly communicates with the running GameScript for advanced game logic (JSON/SQL).
*   **Community**: Syncs player statistics, VIP statuses, and server info to a community website/database.
*   **GeoIP Service**: Resolves player IP addresses to countries for welcome messages.

### Gameplay Enhancements
*   **Goal System**: Manages game goals and objectives (e.g., `!goal`, `!cv`).
*   **Vote System**: Custom voting implementation for restarting games or other actions.
*   **Company Protection**: Manages company passwords and security.
*   **Welcome Message**: Sends customizable public and private welcome messages to joining players.
*   **Auto Clean**: Automated company cleanup logic.

### Logging
*   **Chat Log DB**: Logs all server chat (Public, Team, Private, IRC, Admin) to a MySQL database.
*   **Chat Logger**: Simple file/console logging.

## 🛠️ Requirements

*   **Python 3.8+**
*   **OpenTTD Server** (with Admin Port enabled)
*   Python Libraries:
    *   `mysql-connector-python`
    *   `geoip2` (optional, for GeoIP)

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/OpenTTD-Sentinel.git
    cd OpenTTD-Sentinel
    ```

2.  **Install dependencies:**
    ```bash
    pip install mysql-connector-python geoip2
    ```

3.  **Prepare Configuration:**
    *   Copy `controller_config.example.xml` to `controller_config.xml` and edit it with your server details (IP, Port, Admin Password, DB credentials).
    *   Copy `admins.example.json` to `admins.json` and configure your admin users.

4.  **Database Setup:**
    *   Ensure your MySQL database exists and the user has permissions.
    *   The `MySQL` and `ChatLogDB` plugins will automatically create/update necessary tables on first run.

## ⚙️ Configuration

### controller_config.xml
The main configuration file. Key sections:
*   `<admin_password>`: Must match `network.admin_password` in your `openttd.cfg`.
*   `<mysql_config>`: Central database credentials.
*   `<irc_enabled>`: Set to `true` to enable the bot.
*   `<launch_wait>`: Time to wait for the server to boot before connecting.

### admins.json
Defines user roles and permissions.
*   **Groups**: different permission sets (e.g., `scanner`, `operator`, `full-admin`).
*   **Users**: Maps usernames to groups.
*   **Inheritance**: Groups can inherit permissions from others.

## ▶️ How to Run

Run the main script:

```bash
python3 sentinel.py
```

It is recommended to run this inside a `screen` or `tmux` session, or as a systemd service, to keep it running in the background.

## 🧩 Plugin Development

To create a new plugin:
1.  Create a file in `plugins/`.
2.  Inherit from `IPlugin`.
3.  Implement `on_load`, `on_event`, `on_tick`, etc.
4.  The core will automatically discover and load it.

```python
from plugin_interface import IPlugin

class MyPlugin(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "MyPlugin"

    def on_load(self):
        self.client.log("MyPlugin Loaded!")
```
