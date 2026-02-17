require("Sentinel.nut");

class SentinelCore extends GSController
{
    // FIX: Defined missing 'api' variable to prevent crash
    api = null; 
    active_plugin = null;
    ticks = 0;

    constructor() {
        GSLog.Info("SentinelGS: Kernel Initializing...");
    }

    function Start()
    {
        Sentinel.Log("Kernel Started. Version: " + Sentinel.VERSION);
        Sentinel.SendAdmin({ event = "gamescript_start", version = Sentinel.VERSION });

        // --- MODE SELECTION ---
        local mode = GSGameSettings.GetValue("game_mode");
        Sentinel.Log("Read 'game_mode' setting: " + mode);

        // Fallback for broken/missing config
        if (mode <= -1) { 
            Sentinel.Log("Warning: Config missing or corrupt (-1). Defaulting to Mode 2 (Aphid).");
            mode = 0; 
        }
        
        Sentinel.Log("Initializing Game Mode ID: " + mode);

        try {
            // FIX: We pass 'null' instead of 'this.api' because the wrappers 
            // now use the static 'Sentinel' class for communication.
            
            if (mode == 0) {
                require("plugins/CompanyValue/wrapper.nut");
                this.active_plugin = Sentinel_CompanyValue(null);
            }
            else if (mode == 1) {
                require("plugins/CityBuilder1/wrapper.nut");
                this.active_plugin = Sentinel_CB1(null);
            } 
            else if (mode == 2) {
                require("plugins/AphidCB/wrapper.nut");
                this.active_plugin = Sentinel_AphidCB(null);
            }
            else if (mode == 3) {
                require("plugins/CityBuilder3/wrapper.nut");
                this.active_plugin = Sentinel_CB3(null);
            }
            else if (mode == 4) {
                require("plugins/CityBuilderCargo/wrapper.nut");
                this.active_plugin = Sentinel_CBCargo(null);
            }
            else if (mode == 6) {
                require("plugins/BusyBee/wrapper.nut");
                this.active_plugin = Sentinel_BusyBee(null);
            }
            else if (mode == 7) {
                require("plugins/NovaCB/wrapper.nut");
                this.active_plugin = Sentinel_NovaCB(null);
            }
            else {
                Sentinel.Log("Mode " + mode + " is Company Value (Default)");
            }

            if (this.active_plugin != null) {
                Sentinel.Log("Starting Active Plugin...");
                this.active_plugin.Start();
            }
            
        } catch(e) {
            Sentinel.Error("CRITICAL INIT FAILURE: " + e);
        }

        this.RunLoop();
    }

    function RunLoop() {
        while(true) {
            this.HandleEvents();
            
            if (this.active_plugin != null) {
                try { 
                    this.active_plugin.Run(this.ticks);
                } catch(e) {
                    Sentinel.Error("Runtime Error: " + e);
                }
            }
            
            this.Sleep(1);
            this.ticks++;
        }
    }

    function HandleEvents() {
        while (GSEventController.IsEventWaiting()) {
            local ev = GSEventController.GetNextEvent();
            local type = ev.GetEventType();

            if (type == GSEvent.ET_ADMIN_PORT) {
                local data = GSEventAdminPort.Convert(ev).GetObject();
                if (this.active_plugin != null) this.active_plugin.OnAdminEvent(data);
            }

            if (this.active_plugin != null) {
                this.active_plugin.OnEvent(type, ev);
            }
        }
    }
}