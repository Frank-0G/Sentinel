# Sentinel Plugins

This directory contains the plugins that power the Sentinel OpenTTD Controller. Each file is a self-contained module that adds specific functionality to the server.

## 🛠 Core Infrastructure

These plugins provide essential services used by other plugins and the controller itself.

*   **`mysql.py`**: The central database service. It manages a threaded connection pool to the MySQL server, allowing other plugins to execute queries asynchronously without blocking the main server loop.
*   **`data_controller.py`**: Maintains a real-time state of the server. It tracks connected clients, active companies, and server statistics by listening to Admin Port update packets.
*   **`command_manager.py`**: The "brain" for chat commands. It parses messages starting with the trigger prefix (e.g., `!`), checks user permissions against `admins.json`, and routes the command to the appropriate plugin handler. Recent enhancements include:
    *   Advanced company reset commands with multiple player handling options (`!resetcompany`, `!resetcompanykick`, `!resetcompanyban`)
    *   Company reset timer system for delayed resets (`!resetcompanytimer`, `!cancelresetcompany`)
    *   Separated restart commands: `!restart` (game/map only) and `!restartserver` (full Sentinel restart)
*   **`admin_manager.py`**: Manages the connection lifecycle, protocol negotiation, and packet handling with the OpenTTD Admin Port.
*   **`geoip_service.py`**: Uses the MaxMind GeoIP database to resolve player IP addresses to country codes and names. Used for welcome messages and logging.

## 🛡 Administration & Security

Plugins focused on server management and protecting the game environment.

*   **`admin_login.py`**: Provides a secure login system. Admins can authenticate in-game using `!login <user> <pass>` or a token. Manages session validity.
*   **`anti_flood.py`**: Monitors chat frequency and command usage to prevent flooding. Can automatically mute or kick players who spam.
*   **`company_protection.py`**: Enforces password rules for companies. It can distinct between "protected" and "unprotected" companies and alert admins if a password is removed.
*   **`auto_restart.py`**: Checks the server uptime and triggers a graceful restart (via the `rcon quit` command) after a configured duration (e.g., every 24 hours).
*   **`auto_clean.py`**: Automatically resets or removes companies that have seemingly been abandoned or went bankrupt, keeping the server map fresh.

## 💬 Communication & Logging

Plugins that handle chat, logging, and external communication.

*   **`irc_bridge.py`**: Connects the server to an IRC channel. It relays in-game chat to IRC and IRC messages to the game (colored chat support). Also reports server events like joins, quits, and company updates.
*   **`discord_bridge.py`**: Full two-way Discord integration. Relays all in-game chat (including public player commands) to Discord and vice versa. Features include:
    *   Server status presence updates
    *   Rich embed notifications for game events
    *   Admin authentication via DM
    *   Multi-channel support
    *   Automatic admin role detection
*   **`chat_log_db.py`**: Logs **every** chat message (public, team, private, and admin) to the MySQL database for auditing and history purposes.
*   **`chat_logger.py`**: A simpler logger that outputs chat to the console or a flat file.
*   **`welcome_msg.py`**: Sends a customizable welcome message to players when they join. Supports public broadcasts and private messages with instructions/rules.

## 🎮 Gameplay & Community

Plugins that enhance the player experience or bridge the game with specific community features.

*   **`gamescript_connector.py`**: The bridge between Sentinel and the GameScript running inside OpenTTD. It uses `[SENTINEL]` tagged log messages to exchange JSON data, allowing Python to query game data or trigger GameScript events.
*   **`community.py`**: The main integration for the BTPro community. It handles:
    *   Syncing player stats (score, value) to the database.
    *   VIP recognition and expiration warnings.
    *   Sponsor announcements.
    *   Highscore commands (`!rank`).
    *   Name verification (checking if a nickname is registered).
*   **`vote_system.py`**: Implements a custom voting system (e.g., `!vote restart`), allowing players to trigger actions if a majority agrees.
*   **`goal_system.py`**: Manages game objectives. Players can check the current goal (`!goal`) or server status (`!cv`).
*   **`openttd_session.py`**: A helper service that abstracts sending private messages and managing specific user session data.

## 🔌 Legacy / Stubs

*   **`sentinel_gateway.py`**: Deprecated. Previous entry point for GameScript communication. Functionality has been moved to `gamescript_connector.py`. Kept as a stub for backward compatibility if needed.
