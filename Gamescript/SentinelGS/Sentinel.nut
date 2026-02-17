
/**
 * Sentinel Core Library
 * Replaces xShunter's static helper methods.
 */

class Sentinel
{
    // Configuration
    _storageKeys = [];
    _storageValues = [];
    
    // Static Version Info
    static VERSION = "1.0-SENTINEL";

    // --- ADMIN COMMUNICATION ---
    
    static function SendAdmin(table)
    {
        // Wrapper for GSAdmin.Send to ensure safe transmission
        if (!GSAdmin.Send(table)) {
            GSLog.Error("[Sentinel] Failed to send Admin Packet.");
        }
    }

    static function Log(message)
    {
        // Standard Logging
        GSLog.Info("[Sentinel] " + message);
        local packet = { command = "logmessage", type = "info", text = message };
        Sentinel.SendAdmin(packet);
    }

    static function Debug(message)
    {
        // Debug Logging
        GSLog.Info("[Sentinel DEBUG] " + message);
        local packet = { command = "logmessage", type = "debug", text = message };
        Sentinel.SendAdmin(packet);
    }

    static function Error(message)
    {
        // Error Logging
        GSLog.Error("[Sentinel ERROR] " + message);
        local packet = { command = "logmessage", type = "error", text = message };
        Sentinel.SendAdmin(packet);
    }

    // --- CHAT HELPERS ---

    static function ChatPublic(message)
    {
        local packet = { command = "chat", type = "public", text = message };
        Sentinel.SendAdmin(packet);
    }

    static function ChatTeam(company_id, message)
    {
        local packet = { command = "chat", type = "team", company = company_id, text = message };
        Sentinel.SendAdmin(packet);
    }

    static function ChatPrivate(client_id, message)
    {
        local packet = { command = "chat", type = "server", client = client_id, text = message };
        Sentinel.SendAdmin(packet);
    }

    static function IrcMsg(message)
    {
        // Sends message to IRC channel via Bridge
        local packet = { command = "ircmessage", type = "publicmessage", text = message };
        Sentinel.SendAdmin(packet);
    }

    // --- STORAGE HELPERS (Legacy Support) ---
    // Many xShunter scripts rely on this specific Key/Value storage implementation.
    
    function StorageSet(key, value)
    {
        // Helper for instances
        Sentinel.SetStorage(key, value);
    }
    
    static function SetStorage(storagekey, storagevalue)
    {
        local root = getroottable();
        if (!("SentinelStorage" in root)) root.SentinelStorage <- {};
        root.SentinelStorage[storagekey] <- storagevalue;
    }

    static function GetStorage(storagekey)
    {
        local root = getroottable();
        if (!("SentinelStorage" in root)) return null;
        if (storagekey in root.SentinelStorage) return root.SentinelStorage[storagekey];
        return null;
    }
}