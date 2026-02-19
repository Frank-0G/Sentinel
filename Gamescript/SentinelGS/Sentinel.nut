
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

    // --- STATISTICS HELPERS ---

    static function GetCargoSuffix(cargo_id)
    {
        local label = GSCargo.GetCargoLabel(cargo_id);
        
        // FIRS/ECS/YETI detection logic from legacy GetCargoName
        if (GSCargo.GetCargoLabel(24) == "RCYC") { // FIRS
             switch(cargo_id) {
                case 0: return " bags of grain";
                case 1: return " tonnes of coal";
                case 2: return " tonnes of iron ore";
                case 3: return " tonnes of steel";
                case 4: return " crates of livestock";
                case 5: return " tonnes of wood";
                case 6: return " bags of sugar";
                case 7: return " cans of food";
                case 8: return " buckets of water";
                case 9: return " tonnes of paper";
                case 10: return " tonnes of copper ore";
                case 11: return " bags of coffee";
                case 12: return " tonnes of fruit";
                case 13: return " tonnes of rubber";
                case 14: return " kilolitres of oil";
                default: return " units";
             }
        }
        
        // Default labels
        switch(label) {
            case "PASS": return " passengers";
            case "COAL": return " tonnes of coal";
            case "MAIL": return " bags of mail";
            case "IORE": return " tonnes of iron ore";
            case "GOOD": return " tonnes of goods";
            case "GRAI": return " bags of grain";
            case "LVST": return " crates of livestock";
            case "WOOD": return " tonnes of wood";
            case "OIL_": return " kilolitres of oil";
            case "STEL": return " tonnes of steel";
            case "VALU": return " bags of valuables";
            default: return " units";
        }
    }

    static function PushTownStats()
    {
        local townList = GSTownList();
        // Clear demands first as per legacy behavior
        Sentinel.SendAdmin({ event = "citybuilder", action = "cleardemands" });

        foreach (town_id, _ in townList) {
            local location = GSTown.GetLocation(town_id);
            local packet = {
                event = "citybuilder",
                action = "townstats",
                townid = town_id,
                townname = GSTown.GetName(town_id),
                population = GSTown.GetPopulation(town_id),
                housecount = GSTown.GetHouseCount(town_id),
                growthrate = GSTown.GetGrowthRate(town_id),
                statue = GSTown.HasStatue(town_id),
                location = GSMap.GetTileX(location) + "x" + GSMap.GetTileY(location)
            };
            
            // Check for owner if CityBuilder is active and has matching structures
            // For now we just push general stats as this is 'default' behavior.
            Sentinel.SendAdmin(packet);
        }
    }

    static function PushCompanyStats()
    {
        for (local i = GSCompany.COMPANY_FIRST; i <= GSCompany.COMPANY_LAST; i++) {
            local cid = GSCompany.ResolveCompanyID(i);
            if (cid == GSCompany.COMPANY_INVALID) continue;
            
            // We'll let plugins handle their own population if they have claims,
            // but we can send a general pulse.
            local packet = { event = "populationupdated", company = cid, population = -1 };
            Sentinel.SendAdmin(packet);
        }
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