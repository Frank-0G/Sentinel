PATH <- "plugins/ClassicCB/";

function LoadModule(filename) {
    try {
        require(filename);
        Sentinel.Log("[WRAPPER] Loaded module: " + filename);
    } catch(e) {
        try {
            require(PATH + filename);
            Sentinel.Log("[WRAPPER] Loaded module (with PATH): " + filename);
        } catch(e2) {
            Sentinel.Error("[WRAPPER] FAILED to load module: " + filename);
            Sentinel.Error("[WRAPPER] Error 1 (Relative): " + e);
            Sentinel.Error("[WRAPPER] Error 2 (Absolute): " + e2);
            throw e;
        }
    }
}

// 0. Load Constants
LoadModule("constants.nut");

// 1. Load Dependencies
LoadModule("RTDCache.nut");
LoadModule("town.nut");

// 2. Load Main Class
LoadModule("ClassicCB.nut");

class Sentinel_ClassicCB {
    impl = null;
    kernel = null;
    last_broadcast_tick = 0;

    constructor(_kernel) {
        this.kernel = _kernel;
        this.impl = CityBuilder(this);
    }

    function GetName() { return this.impl.GetName(); }

    function Start() {
        this.impl.Initialize();
        // Priority Sync: If the Kernel already received configuration from Sentinel, apply it now.
        if (this.kernel.goal_target > 0) {
            Sentinel.Log("[WRAPPER] Trace: Re-Syncing goal_value to " + this.kernel.goal_target + " post-initialization");
            this.UpdateGoalConfig({ population = this.kernel.goal_target });
        } else if (this.kernel.goal_target == 0) {
             // If user explicitly set 0 in XML, ensure we disable the goal
             this.UpdateGoalConfig({ population = 0 });
        }
        Sentinel.Log("[WRAPPER] Trace: Core SENTINEL_TARGET is " + (this.impl.SENTINEL_TARGET == null ? "null" : this.impl.SENTINEL_TARGET.tostring()) + " after sync sequence");

        // Push initial metadata to Kernel
        this.SyncMetadata();

        // Initialize broadcast timer
        this.last_broadcast_tick = GSController.GetTick();
    }

    function Run(ticks) {
        this.impl.Process();

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
        this.impl.ProcessEvent(type, ev);
    }

    function OnAdminEvent(data) {
        if ("command" in data && data.command == "requestinfo") {
            this.SyncMetadata();
        }
        if (this.impl != null && "OnAdminEvent" in this.impl) {
            this.impl.OnAdminEvent(data);
        }
    }

    // --- SHIM FOR expectations ---

    function Log(msg) { Sentinel.Log(msg); }

    function SendToController(data) {
        // Intercept progress updates to sync with Kernel state
        if ("event" in data) {
            if (data.event == "companyprogress") {
                this.kernel.UpdateCompanyProgress(data.company, data.value, data.progress);
            } else if (data.event == "goaltypeinfo") {
                this.kernel.UpdateGoalMetadata(1, data.target_value, "inhabitants", "");
            } else if (data.event == "winner") {
                this.kernel.HandleWinner(data);
            } else if (data.event == "town_claimed") {
                this.kernel.HandleTownClaimed(data);
            } else if (data.event == "town_unclaimed") {
                this.kernel.HandleTownUnclaimed(data);
            }
        }

        // Still send to Admin for Python-side awareness (Legacy)
        Sentinel.SendAdmin(data);
    }

    //for !gool trigger
    function SyncMetadata() {
        if ("goal_value" in this.impl) {
            this.kernel.UpdateGoalMetadata(1, this.impl.goal_value, "inhabitants", "");
        }
    }

    function UpdateGoalConfig(data) {
        if ("population" in data) {
            local val = data.population.tointeger();
            if (val > 0) {
                Sentinel.Log("[WRAPPER] Trace: Applying SYNC update for SENTINEL_TARGET -> " + val);
                this.impl.SENTINEL_TARGET = val;
                this.impl.goal_mode = true;
                //this.impl.SendGoalInfo();
                this.impl.RefreshGoals();
            }
            //else if (val == 0) {
            //    Sentinel.Log("[WRAPPER] Trace: Goal disabled via SYNC.");
            //    this.impl.SENTINEL_TARGET = 0;
            //    this.impl.goal_mode = false;
            //}
        }
    }
}
