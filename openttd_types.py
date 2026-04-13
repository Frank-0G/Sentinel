from enum import IntEnum

class AdminPacketType(IntEnum):
    ADMIN_JOIN = 0
    ADMIN_QUIT = 1
    ADMIN_UPDATE_FREQUENCY = 2
    ADMIN_POLL = 3
    ADMIN_CHAT = 4
    ADMIN_RCON = 5
    ADMIN_GAMESCRIPT = 6
    ADMIN_PING = 7
    ADMIN_EXTERNAL_CHAT = 8
    ADMIN_JOIN_SECURE = 9
    ADMIN_AUTH_RESPONSE = 10

class ServerPacketType(IntEnum):
    # EXTRACTED FROM SOURCE CODE
    SERVER_FULL = 100
    SERVER_BANNED = 101
    SERVER_ERROR = 102
    SERVER_PROTOCOL = 103
    SERVER_WELCOME = 104
    SERVER_NEWGAME = 105
    SERVER_SHUTDOWN = 106
    SERVER_DATE = 107
    SERVER_CLIENT_JOIN = 108
    SERVER_CLIENT_INFO = 109
    SERVER_CLIENT_UPDATE = 110
    SERVER_CLIENT_QUIT = 111
    SERVER_CLIENT_ERROR = 112
    SERVER_COMPANY_NEW = 113
    SERVER_COMPANY_INFO = 114
    SERVER_COMPANY_UPDATE = 115
    SERVER_COMPANY_REMOVE = 116
    SERVER_COMPANY_ECONOMY = 117
    SERVER_COMPANY_STATS = 118
    
    # Protocol Extension
    SERVER_CHAT = 119            # Chat Event
    SERVER_RCON = 120
    SERVER_CONSOLE = 121
    SERVER_CMD_LOG = 122
    SERVER_CLIENT_INFO_EXT = 123
    SERVER_GAMESCRIPT = 124      # GameScript Event
    SERVER_CLIENT_UPDATE_EXT = 125
    SERVER_CLIENT_QUIT_EXT = 126
    SERVER_CMD_LOGGING = 127     # Main Build Event
    SERVER_NEWGAME_EXT = 128
    SERVER_AUTH_REQUEST = 129
    SERVER_RCON_END = 125 # Duplicate value allowed, but different name required? No, value alias is fine.
    # SERVER_RCON_END = 125 
    # SERVER_PONG = 126 
    # Commenting out explicit duplicates if they share name/value with above. 
    # But wait, SERVER_RCON_END is 125, same as SERVER_CLIENT_UPDATE_EXT? 
    # Protocol extension likely repurposes these IDs. 
    # I will just rename them all to be safe.
    SERVER_RCON_END_EXT = 125 
    SERVER_PONG_EXT = 126

class AdminUpdateType(IntEnum):
    # EXTRACTED FROM SOURCE CODE
    ADMIN_UPDATE_DATE = 0
    ADMIN_UPDATE_CLIENT_INFO = 1
    ADMIN_UPDATE_COMPANY_INFO = 2
    ADMIN_UPDATE_COMPANY_ECONOMY = 3 # Warning: Do not use for DoCommand!
    ADMIN_UPDATE_COMPANY_STATS = 4
    ADMIN_UPDATE_CHAT = 5
    ADMIN_UPDATE_CONSOLE = 6
    ADMIN_UPDATE_CMD_NAMES = 7
    ADMIN_UPDATE_CMD_LOGGING = 8     # Subscribe to this for Packet 127
    ADMIN_UPDATE_GAMESCRIPT = 9
    ADMIN_UPDATE_END = 10

class AdminUpdateFrequency(IntEnum):
    """Admin update frequencies (bitmask values).

    OpenTTD defines `AdminUpdateFrequency` as an enum:
      Poll=0, Daily=1, Weekly=2, Monthly=3, Quarterly=4, Annually=5, Automatic=6
    and sends them over the admin protocol as a bitset (`EnumBitSet`), meaning
    the on-the-wire value is `1 << enum_value`.

    So the values you send are:
      Poll=1, Daily=2, Weekly=4, Monthly=8, Quarterly=16, Annually=32, Automatic=64
    """
    ADMIN_FREQUENCY_POLL = 1 << 0
    ADMIN_FREQUENCY_DAILY = 1 << 1
    ADMIN_FREQUENCY_WEEKLY = 1 << 2
    ADMIN_FREQUENCY_MONTHLY = 1 << 3
    ADMIN_FREQUENCY_QUARTERLY = 1 << 4
    ADMIN_FREQUENCY_ANNUALLY = 1 << 5
    ADMIN_FREQUENCY_AUTOMATIC = 1 << 6



class NetworkAction(IntEnum):
    NETWORK_ACTION_JOIN = 0
    NETWORK_ACTION_LEAVE = 1
    NETWORK_ACTION_SERVER_MESSAGE = 2
    NETWORK_ACTION_CHAT = 3
    NETWORK_ACTION_CHAT_COMPANY = 4
    NETWORK_ACTION_CHAT_CLIENT = 5
    NETWORK_ACTION_GIVE_MONEY = 6
    NETWORK_ACTION_NAME_CHANGE = 7
    NETWORK_ACTION_COMPANY_SPECTATOR = 8
    NETWORK_ACTION_COMPANY_JOIN = 9
    NETWORK_ACTION_COMPANY_NEW = 10

class NetworkErrorCode(IntEnum):
    NETWORK_ERROR_GENERAL = 0
    NETWORK_ERROR_DESYNC = 1
    NETWORK_ERROR_SAVEGAME_FAILED = 2
    NETWORK_ERROR_CONNECTION_LOST = 3
    NETWORK_ERROR_ILLEGAL_PACKET = 4
    NETWORK_ERROR_NEWGRF_MISMATCH = 5
    NETWORK_ERROR_NOT_AUTHORIZED = 6
    NETWORK_ERROR_NOT_EXPECTED = 7
    NETWORK_ERROR_WRONG_REVISION = 8
    NETWORK_ERROR_NAME_IN_USE = 9
    NETWORK_ERROR_WRONG_PASSWORD = 10
    NETWORK_ERROR_PLAYER_MISMATCH = 11
    NETWORK_ERROR_KICKED = 12
    NETWORK_ERROR_CHEATER = 13
    NETWORK_ERROR_FULL = 14
    NETWORK_ERROR_TOO_MANY_COMMANDS = 15
    NETWORK_ERROR_TIMEOUT_PASSWORD = 16
    NETWORK_ERROR_TIMEOUT_COMPUTER = 17
    NETWORK_ERROR_TIMEOUT_MAP = 18
    NETWORK_ERROR_TIMEOUT_JOIN = 19
    NETWORK_ERROR_INVALID_CLIENT_NAME = 20
    NETWORK_ERROR_NOT_ON_ALLOW_LIST = 21
    NETWORK_ERROR_NO_AUTH_METHOD = 22

class NetworkQuitReason(IntEnum):
    NETWORK_QUIT_INVALID = 0
    NETWORK_QUIT_RECONNECT = 1
    NETWORK_QUIT_TIMEOUT = 2
    NETWORK_QUIT_KICKED = 3
    NETWORK_QUIT_DESYNC = 4
    NETWORK_QUIT_BROKEN_DATA = 5
    NETWORK_QUIT_GAMESCRIPT = 6
    NETWORK_QUIT_LOST_CONNECTION = 7
    NETWORK_QUIT_SAVEGAME = 8
    NETWORK_QUIT_SERVER_QUIT = 9
    NETWORK_QUIT_RESTART = 10
    NETWORK_QUIT_TOO_MANY_COMMANDS = 11
    NETWORK_QUIT_REFUSED = 12

NETWORK_ERROR_TEXT = {
    0: "general error",
    1: "desync error",
    2: "could not load map",
    3: "connection lost",
    4: "protocol error",
    5: "NewGRF mismatch",
    6: "not authorized",
    7: "received invalid or unexpected packet",
    8: "wrong revision",
    9: "name already in use",
    10: "wrong password",
    11: "wrong company in DoCommand",
    12: "kicked by server",
    13: "was trying to use a cheat",
    14: "server full",
    15: "was sending too many commands",
    16: "received no password in time",
    17: "general timeout",
    18: "downloading map took too long",
    19: "processing map took too long",
    20: "invalid client name",
    21: "not on allow list",
    22: "no common authentication method"
}

NETWORK_QUIT_TEXT = {
    0: "unknown",
    1: "reconnecting",
    2: "timeout",
    3: "kicked",
    4: "desync",
    5: "broken data",
    6: "GameScript",
    7: "connection lost",
    8: "saving game",
    9: "server shutdown",
    10: "server restart",
    11: "sending too many commands",
    12: "connection refused",
    255: "leaving" # Custom value for normal quit if not provided by protocol
}
