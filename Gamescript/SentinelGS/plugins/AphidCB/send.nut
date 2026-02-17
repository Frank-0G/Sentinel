/**
 * AphidCB - send.nut (Patched for Sentinel)
 * Intercepts legacy SendAdmin calls and routes them to Sentinel Core.
 */

function SendAdmin(type, args)
{
    // 1. Log to Console (So you still see it in logs)
    local debug_str = "SendAdmin: " + type;
    foreach(val in args) {
        debug_str += ", " + val;
    }
    GSLog.Info(debug_str);

    // 2. Construct Data Packet for Sentinel
    local t = { id = type };
    
    // Helper to safely get arguments
    local get = function(idx) { 
        if (typeof args == "array" && idx < args.len()) return args[idx];
        return null;
    };

    // 3. Map Legacy Arguments to Sentinel Keys
    if (type == "citybuilder") {
        t.action <- get(0); // e.g. "claimed"
        
        if (t.action == "claimed") {
            // Log format: claimed, company_id, town_name, town_id, x, y
            t.company <- get(1);
            t.town <- get(2);
            t.townid <- get(3);
            t.x <- get(4);
            t.y <- get(5);
        }
        else if (t.action == "towndemands") {
            // Map demand info if available
            t.townid <- get(1);
            // Add other demand fields as needed
        }
    }
    
    // Pass raw args just in case
    t.args <- args;

    // 4. Send via Sentinel Admin Bridge
    Sentinel.SendAdmin(t);
}