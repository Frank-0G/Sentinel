PATH <- "plugins/ClassicCB/";

function LoadModule(filename) {
    try {
        require(filename);
        Sentinel.Log("Loaded module: " + filename);
    } catch(e) {
        try {
            require(PATH + filename);
            Sentinel.Log("Loaded module (with PATH): " + filename);
        } catch(e2) {
            Sentinel.Error("FAILED to load module: " + filename);
            Sentinel.Error("Error 1 (Relative): " + e);
            Sentinel.Error("Error 2 (Absolute): " + e2);
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

    constructor(api_ref) {
        this.impl = CityBuilder();
    }

    function Start() {
        Sentinel.Log("Starting CityBuilder Classic (ClassicCB)...");
        this.impl.Initialize();
        if ("SendGoalInfo" in this.impl) this.impl.SendGoalInfo();
    }

    function Run(ticks) {
        this.impl.Process();
    }

    function OnEvent(type, ev) {
        this.impl.ProcessEvent(ev);
    }

    function OnAdminEvent(data) {
        if (this.impl != null && "OnAdminEvent" in this.impl) {
            this.impl.OnAdminEvent(data);
        }
    }

    function SendGoalInfo() {
        if (this.impl != null && "SendGoalInfo" in this.impl) this.impl.SendGoalInfo();
    }
}
