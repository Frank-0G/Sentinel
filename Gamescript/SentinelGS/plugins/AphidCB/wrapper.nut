// Define the folder prefix so we can load files from the correct directory
local PATH = "plugins/AphidCB/";

// Helper to safely load files with logging
function LoadModule(filename) {
    try {
        require(PATH + filename);
        Sentinel.Log("Loaded module: " + filename);
    } catch(e) {
        // Try loading from root as fallback
        try {
            require(filename);
            Sentinel.Log("Loaded module (from root): " + filename);
        } catch(e2) {
            Sentinel.Error("FAILED to load module: " + filename);
            Sentinel.Error("Error 1 (Path): " + e);
            Sentinel.Error("Error 2 (Root): " + e2);
            throw e; // Stop execution so we see the error immediately
        }
    }
}

// 1. Load the Main Class first
LoadModule("CityBuilder2.nut");

// 2. Load Dependencies explicitly
// These attach methods to the CityBuilder class.
local dependencies = [
    "Sendstats.nut",   // <--- Critical: Contains SendPopulation
    "Towngrowth.nut",
    "Citygrowth.nut",
    "send.nut",
    "IC.nut",
    "comp.nut",
    "Atomic.nut"
];

foreach (file in dependencies) {
    LoadModule(file);
}

class Sentinel_AphidCB {
    impl = null;
    last_month = -1;

    constructor(api_ref) {
        this.impl = CityBuilder(); 
    }

    function Start() {
        Sentinel.Log("Starting Aphid's CityBuilder...");
        
        if ("StoryStart" in this.impl) this.impl.StoryStart();
        if ("Start_Lib" in this.impl) this.impl.Start_Lib();
        if ("SendGoalInfo" in this.impl) this.impl.SendGoalInfo();
        
        Sentinel.SendAdmin({ commandreply = "citybuilder", enabled = true, name = this.impl.GetName() });
    }

    function Run(ticks) {
        // Run Main Logic
        this.impl.Manage();

        // Monthly Reporting
        local date = GSDate.GetCurrentDate();
        local month = GSDate.GetMonth(date);
        
        if (month != this.last_month) {
            this.last_month = month;
            
            // Callbacks for SendStatistics
            local chat_fnc = function(msg, cmp) { Sentinel.ChatTeam(cmp, msg); };
            local suffix_fnc = function(cargo_id) { return GSCargo.GetCargoLabel(cargo_id); };

            // Send Cargo Stats
            if ("SendStatistics" in this.impl) {
                for (local c = GSCompany.COMPANY_FIRST; c <= GSCompany.COMPANY_LAST; c++) {
                    if (GSCompany.ResolveCompanyID(c) != GSCompany.COMPANY_INVALID) {
                        try {
                            this.impl.SendStatistics(c, chat_fnc, suffix_fnc);
                        } catch(e) {}
                    }
                }
            }

            // Send Population & Goals
            if ("SendPopulation" in this.impl) {
                this.impl.SendPopulation();
            } else {
                Sentinel.Error("SendPopulation method missing! Check Sendstats.nut");
            }
            
            if ("SendGoalInfo" in this.impl) this.impl.SendGoalInfo();
        }
    }

    function OnEvent(type, ev) {}
    function OnAdminEvent(data) {}
}