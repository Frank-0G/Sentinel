# OpenTTD Sentinel Controller

Sentinel is a powerful, modular, event-driven Python controller designed for OpenTTD servers. It interfaces with the OpenTTD Admin Port to provide advanced administration capabilities, automated tasks, database integration, and community feature synchronization.

This project is a joint development initiative of the **BTPro OpenTTD Community** (https://openttd.btpro.nl) and the **N-Ice OpenTTD Community** (http://www.n-ice.org/openttd/). We invite everyone to make pull requests to this repository to improve Sentinel further together! Please check the [AntiGravity Development Manual](ANTIGRAVITY_DEV_MANUAL.md) for more information.

It features a robust **Plugin Architecture**, allowing developers to easily extend functionality or disable unneeded features.

## 🎁 Support Development

If you find Sentinel useful and would like to support its continued development, consider making a donation:

[![Donate with PayPal](https://www.paypalobjects.com/en_US/i/btn/btn_donate_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=GFRA27HF7A3VS)

## 🚀 Features

Sentinel comes with a suite of built-in plugins covering a wide range of functionality:

### Core Administration
*   **Sentinel Core**: The micro-kernel that manages the Admin Port connection and plugin lifecycle. Features **IPv4/IPv6 Dual-Stack support** and **Robust Reconnection**.
*   **Core Services**: Provides foundational infrastructure including a centralized **StateManager** (source of truth for players/companies), **SubscriptionManager** (deduplicated Admin Port updates), and a **CommandRouter**.
*   **Dynamic Command Parsing**: Uses `DoCommands.xml` to dynamically parse Admin Port command logging (Packet 127), providing detailed command parameters to plugins.
*   **Advanced Automation**: Intelligent server restarts with **Dual-Timeout** support, **Spectator Safety**, and **Graceful Process Termination**.
*   **Command Manager**: Handles in-game commands with a comprehensive permission system.
*   **Admin Login**: Secure login system for administrators using tokens or passwords.
*   **Data Controller**: Real-time tracking of clients, companies, and server stats.
*   **Auto Restart**: Automates server restarts on a schedule.
*   **Anti Flood**: Prevents chat spam and command flooding.

### Integration & Connectivity
*   **MySQL Service**: Centralized, threaded MySQL connection pooling for all plugins.
*   **IRC Bridge**: Two-way chat sync with **Nickserv Authentication** support and extensive event formatting.
*   **Discord Bridge**: Full two-way chat sync, server status presence, and rich embed notifications.
*   **GameScript Bridge**: A generic JSON-based bridge for exchanging events and commands with the in-game GameScript.
*   **GameScript Connector**: Seamlessly communicates with the running GameScript for advanced game logic (JSON/SQL).
*   **GeoIP Service**: Resolves player IP addresses to countries for welcome messages.

### Gameplay Enhancements
*   **Anti-Cheat**: Prevents players from building level crossings over other companies' infrastructure.
*   **Statistics Recorder**: Detailed recording of exhaustive company statistics to MySQL for external analysis.
*   **Goal System**: Manages game goals and objectives (e.g., `!goal`, `!cv`).
*   **Vote System**: Custom voting implementation for restarting games or other actions.
*   **Company Protection**: Manages company passwords and security.
*   **Welcome Message**: Sends customizable public and private welcome messages to joining players.
*   **Auto Clean**: Automated company cleanup logic.

### Optional Services
*   **GeoIP Server**: A standalone HTTP service (`geoip_server.py`) for looking up IP addresses in the MaxMind database.

### Logging
*   **Chat Log DB**: Logs all server chat (Public, Team, Private, IRC, Admin) to a MySQL database.
    > [!IMPORTANT]
    > To log **TEAM** chats, a custom patch is required in the OpenTTD source code, as the default Admin Port does not advertise team-only messages.
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
    git clone https://github.com/Frank-0G/Sentinel.git
    cd Sentinel
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
*   `<discord_enabled>`: Set to `true` to enable the Discord bot.
*   `<discord_token>`: Your Discord Bot Token.
*   `<discord_channel_id>`: The Channel ID where the bot should operate.
*   `<launch_wait>`: Time to wait for the server to boot before connecting.

### admins.json
Defines user roles and permissions.
*   **Groups**: different permission sets (e.g., `scanner`, `operator`, `full-admin`).
*   **Users**: Maps usernames to groups.
*   **Users**: Maps usernames to groups.
*   **Inheritance**: Groups can inherit permissions from others.
*   **Discord IDs**: Map Discord User IDs to admin usernames for auto-login.
    ```json
    "discord_ids": {
        "123456789012345678": "admin_username"
    }
    ```

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

## 🎮 In-Game Commands

### Server Control (Admin Only)
*   `!restart`: Restart the game/map (players stay connected)
*   `!restartserver`: Restart the Sentinel controller (full restart)
*   `!shutdown [now]`: Shut down the server

### Company Management (Admin)
*   `!reset <id>`: Reset a company (move players to spectators, then reset)
*   `!emptycompany <id>`: Move all players in a company to spectators
*   `!resetcompany <id>`: Standard reset (only works if empty)
*   `!resetcompanyspec <id>`: Move players to spectators, then reset
*   `!resetcompanykick <id>`: Reset company and kick all players
*   `!resetcompanyban <id> [minutes]`: Reset company and ban all players
*   `!resetcompanytimer <id> <minutes>`: Schedule a company reset
*   `!cancelresetcompany <id>`: Cancel a scheduled reset
*   `!lockcompany <id>`: Lock a company
*   `!unlockcompany <id>`: Unlock a company

### Gameplay & Tools
*   `!gsalive`: Check if the GameScript is active and responding
*   `!goal`: Show current scoreboard and goal progress
*   `!progress`: Display visual progress bar of the leading company
*   `!townstats <id>`: Display requirements for a specific company (CityBuilder)
*   `!claimed`: List all currently claimed towns
*   `!screenshot <tile_id>`: Take a screenshot at the specified location

### Player Commands
*   `!alogin <user> <pass>`: Login as an administrator
*   `!alogout`: Logout from admin account
*   `!help`: List available commands
*   `!name <newname>`: Rename yourself (synced to Discord/IRC)
*   `!status`: Show server information
*   `!seed`: Shows the random seed of the current map

## 🎮 Discord Commands

The Discord bot supports several commands. You can use these in the configured channel or via **Direct Message (DM)** to the bot (recommended for admin login).

*   `!help`: List available commands.
*   `!alogin <username> <password>`: Authenticate as an admin.
*   `!alogout`: Log out.
*   `!kick <id> [reason]`: Kick a player (requires admin).
*   `!ban <id> [reason]`: Ban a player (requires admin).
*   `!force_update`: (Admin) Force company data refresh.
*   `!debug_company <id>`: (Admin) Inspect company data.


