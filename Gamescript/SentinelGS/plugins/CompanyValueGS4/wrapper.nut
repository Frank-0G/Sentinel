require("main.nut");
// No longer require api.nut here, as the Kernel provides Sentinel object

class Sentinel_CompanyValueGS4 {
    impl = null;
    kernel = null;
    last_broadcast_tick = 0;

    constructor(_kernel) {
        this.kernel = _kernel;
        // The implementation expected an API object. 
        // We'll provide a shim that talks directly to our Kernel.
        this.impl = CompanyValueGS4(this);
    }

    function GetName() { return this.impl.GetName(); }

    function Start() {
        this.impl.Start();
        
        // Priority Sync: If the Kernel already received configuration from Sentinel, apply it now.
        if (this.kernel.goal_target > 0) {
            Sentinel.Log("[WRAPPER] Trace: Re-Syncing goal_value to " + this.kernel.goal_target + " post-initialization");
            this.UpdateGoalConfig({ winlimit = this.kernel.goal_target });
        } else if (this.kernel.goal_target == 0) {
             // If user explicitly set 0 in XML, ensure we disable the goal
             this.UpdateGoalConfig({ winlimit = 0 });
        }
        Sentinel.Log("[WRAPPER] Trace: Core SENTINEL_TARGET is " + (this.impl.SENTINEL_TARGET == null ? "null" : this.impl.SENTINEL_TARGET.tostring()) + " after sync sequence");
        
        // Push initial metadata to Kernel
        this.SyncMetadata();

        // Initialize broadcast timer
        this.last_broadcast_tick = GSController.GetTick();
    }

    function Run(ticks) {
        this.impl.Run(ticks);
        
        // Automated Scoreboard Broadcast (Game-only)
        local now = GSController.GetTick();
        local interval = this.kernel.goal_announce_interval;
        if (interval > 0) {
            local interval_ticks = interval * 30; // OpenTTD uses 30 ticks per real-world second
            if (now - this.last_broadcast_tick >= interval_ticks) {
                 this.last_broadcast_tick = now;
                 Sentinel.Log("[WRAPPER] Triggering periodic scoreboard broadcast (Global)");
                 this.kernel.HandleGoalCmd({ source = "game", source_id = 0 });
            }
        }
    }

    function OnEvent(type, ev) {
        this.impl.OnEvent(type, ev);
    }

    function OnAdminEvent(data) {
        if ("command" in data && data.command == "requestinfo") {
            this.SyncMetadata();
        }
    }

    // --- SHIM FOR CompanyValueGS4 expectations ---
    
    function Log(msg) { Sentinel.Log(msg); }
    
    function SendToController(data) {
        // Intercept progress updates to sync with Kernel state
        if ("event" in data) {
            if (data.event == "companyprogress") {
                this.kernel.UpdateCompanyProgress(data.company, data.value, data.progress);
            } else if (data.event == "goaltypeinfo") {
                this.kernel.UpdateGoalMetadata(9, data.target_value, "EUR", "company value");
            } else if (data.event == "winner") {
                this.kernel.HandleWinner(data);
            }
        }
        
        // Still send to Admin for Python-side awareness (Legacy)
        Sentinel.SendAdmin(data);
    }

    function SyncMetadata() {
        if ("goal_value" in this.impl) {
            this.kernel.UpdateGoalMetadata(9, this.impl.goal_value, "EUR", "company value");
        }
    }

    function UpdateGoalConfig(data) {
        if ("winlimit" in data) {
            local val = data.winlimit.tointeger();
            if (val > 0) {
                Sentinel.Log("[WRAPPER] Trace: Applying SYNC update for SENTINEL_TARGET -> " + val);
                this.impl.SENTINEL_TARGET = val;
                this.impl.goal_mode = true;
                this.impl.RefreshGoals();
            } else if (val == 0) {
                Sentinel.Log("[WRAPPER] Trace: Goal disabled via SYNC.");
                this.impl.SENTINEL_TARGET = 0;
                this.impl.goal_mode = false;
            }
        }
    }
}
