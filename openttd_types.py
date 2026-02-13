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
    SERVER_CLIENT_INFO = 123
    SERVER_GAMESCRIPT = 124      # GameScript Event
    SERVER_CLIENT_UPDATE = 125
    SERVER_CLIENT_QUIT = 126
    SERVER_CMD_LOGGING = 127     # Main Build Event
    SERVER_NEWGAME = 128
    SERVER_RCON_END = 125 # This is a duplicate, keeping original value for now
    SERVER_PONG = 126 # This is a duplicate, keeping original value for now

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
