class SentinelGS extends GSInfo 
{
    function GetAuthor()        { return "Sentinel Team"; }
    function GetName()          { return "SentinelGS"; }
    function GetDescription()   { return "Modular GameScript Controller for OpenTTD (xShunter Clone)."; }
    function GetVersion()       { return 1; }
    function GetDate()          { return "2026-02-02"; }
    function CreateInstance()   { return "SentinelCore"; }
    function GetShortName()     { return "SNTL"; }
    function GetAPIVersion()    { return "1.6"; }
    function GetUrl()           { return ""; }

    function GetSettings() 
    {
        // --- GENERAL ---
        this.AddCategory("general", "--- General ---", false);
        
        this.AddSetting({
            name = "log_level", description = "Debug: Log level", 
            easy_value = 2, medium_value = 2, hard_value = 2, custom_value = 2, 
            flags = CONFIG_INGAME, min_value = 1, max_value = 3
        });

        // Main Game Mode Switch
        this.AddSetting({
            name = "game_mode", description = "Game Mode Selection",
            easy_value = 0, medium_value = 1, hard_value = 2, custom_value = 0,
            flags = CONFIG_INGAME, min_value = 0, max_value = 8
        });
        
        this.AddLabels("game_mode", {
            _0 = "Mode 0: Company Value", _1 = "Mode 1: CityBuilder Classic", _2 = "Mode 2: Aphid's CityBuilder",
            _3 = "Mode 3: CityBuilder v2", _4 = "Mode 4: CityBuilder Cargo", _5 = "Mode 5: Multi Goal",
            _6 = "Mode 6: Busy Bee Goals", _7 = "Mode 7: Nova's CityBuilder", _8 = "Mode 8: CargoBee"
        });

        // --- APHID / CITYBUILDER SHARED ---
        this.AddCategory("cargogoals", "--- CityBuilder Settings ---");

        this.AddSetting({name = "gamegoal", description = "Goal Target", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags= CONFIG_INGAME, min_value = 0, max_value = 10000000, step_size = 500});
        this.AddSetting({name = "gametime", description = "Game Length (Years)", easy_value = 4, medium_value = 8, hard_value = 12, custom_value = 16, flags= CONFIG_INGAME, min_value = 0, max_value = 1000});
        
        // Legacy 'gametype' for Aphid's internal logic
        this.AddSetting({name = "gametype", description = "CB Type (Legacy)", easy_value = 0, medium_value = 1, hard_value = 1, custom_value = 1, flags = CONFIG_INGAME, min_value = 0, max_value = 3});
        this.AddLabels("gametype", {_0 = "FreeBuilder", _1 = "CityBuilder", _2 = "CityBuilder Co-Op", _3 = "Metropolis"});

        this.AddSetting({name = "hqmaxdist", description = "Max HQ claim dist", easy_value = 20, medium_value = 15, hard_value = 12, custom_value = 32, flags=0, min_value = 5, max_value = 32});
        this.AddSetting({name = "townarea", description = "Town Sign Radius", easy_value = 20, medium_value = 15, hard_value = 10, custom_value = 15, flags = CONFIG_NONE, min_value = 0, max_value = 50});
        this.AddSetting({name = "maxclaimsize", description = "Max claim pop", easy_value = 750, medium_value = 500, hard_value = 250, custom_value = 200, flags = CONFIG_INGAME, min_value = 0, max_value = 4000, step_size = 25});
        this.AddSetting({name = "Town_Labels", description = "Show Owner Label", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_INGAME, min_value = 0, max_value = 1});
        this.AddLabels("Town_Labels", {_0 = "Off", _1 = "On"});

        // --- APHID SPECIFIC (CRITICAL FOR MODE 2) ---
        this.AddCategory("Aphid", "--- Aphid Specific ---");
        
        this.AddSetting({name = "econ_custom", description = "Use custom Economy", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_BOOLEAN});
        this.AddSetting({name = "tutor", description = "Enable Tutor", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_INGAME, min_value = 0, max_value = 1});
        this.AddSetting({name = "value", description = "Difficulty Level", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_INGAME, min_value = 0, max_value = 3});
        this.AddSetting({name = "game", description = "Climate Type", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_INGAME, min_value = 0, max_value = 5});

        this.AddSetting({name = "Industry_Density", description = "Ind. Density (Primary)", easy_value = 1024, medium_value = 800, hard_value = 512, custom_value = 800, flags = CONFIG_INGAME, min_value = 63, max_value = 65536, step_size = 1});
        this.AddSetting({name = "Industry_S_Density", description = "Ind. Density (Secondary)", easy_value = 4096, medium_value = 4096, hard_value = 4096, custom_value = 4096, flags = CONFIG_INGAME, min_value = 63, max_value = 65536, step_size = 1});
        this.AddSetting({name = "Industry_Water", description = "Ind. on Water", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_INGAME, min_value = 0, max_value = 1});
        this.AddSetting({name = "Industry_Town", description = "Ind. in Town", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_INGAME, min_value = 0, max_value = 1000, step_size = 1});
        this.AddSetting({name = "point_to_goal", description = "Point to goal", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_INGAME, min_value = 0, max_value = 1});

        // --- MECHANICS ---
        this.AddCategory("Mechanics", "--- Mechanics ---");
        this.AddSetting({name = "metro_cgg", description = "Metropolis transport req", easy_value = 50, medium_value = 65, hard_value = 75, custom_value = 10, flags = CONFIG_INGAME, min_value = 1, max_value = 98});
        this.AddSetting({name = "min_size_max_growth", description = "Linear growth limit", easy_value = 1200, medium_value = 800, hard_value = 600, custom_value = 400, flags = CONFIG_INGAME, min_value = 50, max_value = 8000, step_size = 25});
        this.AddSetting({name = "min_size_tr", description = "Growth start pop", easy_value = 150, medium_value = 125, hard_value = 100, custom_value = 100, flags = CONFIG_INGAME, min_value = 50, max_value = 40000, step_size = 25});
        this.AddSetting({name = "slow_factor", description = "Slow factor", easy_value = 60, medium_value = 60, hard_value = 60, custom_value = 60, flags = CONFIG_INGAME, min_value = 10, max_value = 1000});
        this.AddSetting({name = "storefactor", description = "Warehouse size", easy_value = 8, medium_value = 6, hard_value = 4, custom_value = 2, flags=0, min_value = 0, max_value = 360});
        this.AddSetting({name = "town_regrow", description = "Regrow %", easy_value = 140, medium_value = 120, hard_value = 120, custom_value = 120, flags=0, min_value = 100, step_size = 10, max_value = 300});
        this.AddSetting({name = "cities_setting", description = "City Behaviour", easy_value = 0, medium_value = 0, hard_value = 6, custom_value = 0, flags = CONFIG_INGAME, min_value = 0, max_value = 6});
        this.AddSetting({name = "injection", description = "Enable Freeze", easy_value = 0, medium_value = 0, hard_value = 1, custom_value = 0, flags = CONFIG_INGAME, min_value = 0, max_value = 1});
        this.AddSetting({name = "paxcargo_istownind", description = "Pax is Town Ind", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_INGAME | CONFIG_BOOLEAN});
        this.AddSetting({name = "lowcargo", description = "Reduced shrink", easy_value = 360, medium_value = 180, hard_value = 20, custom_value = 200, flags = CONFIG_INGAME, min_value = 0, max_value = 1000, step_size = 20});

        // --- CARGO SETTINGS ---
        for(local i = 0; i < 32; i++){
            this.AddSetting({name = "cat"+i, description = "Cargo "+i, easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1, flags = CONFIG_BOOLEAN});
            this.AddSetting({name = "cargo_dlv["+i+"]", description = "Req", min_value = 0, max_value = 10000, easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_NONE | CONFIG_INGAME});
            this.AddSetting({name = "cargo_int["+i+"]", description = "Intro", min_value = 0, max_value = 1000000, easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_NONE | CONFIG_INGAME});
            this.AddSetting({name = "cargo_max["+i+"]", description = "Max", min_value = 250, max_value = 1000000, easy_value = 500, medium_value = 500, hard_value = 500, custom_value = 500, flags = CONFIG_NONE | CONFIG_INGAME});
            this.AddSetting({name = "cargo_dcr["+i+"]", description = "Decay", min_value = 20, max_value = 1000, easy_value = 50, medium_value = 50, hard_value = 50, custom_value = 50, flags = CONFIG_NONE | CONFIG_INGAME});
            this.AddSetting({name = "cargo_sup["+i+"]", description = "Supply", min_value = 0, max_value = 1, easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_NONE | CONFIG_INGAME});
        }
        
        // --- DIVERSE/MISC ---
        this.AddCategory("diverse", "--- Diverse ---");
        this.AddSetting({ name = "allcargos", description = "Count ALL", easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1, flags = CONFIG_INGAME | CONFIG_BOOLEAN });
        this.AddSetting({ name = "randcargo", description = "Random Cargo", easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1, flags = CONFIG_INGAME | CONFIG_BOOLEAN });
        this.AddSetting({ name = "speccargo", description = "Specific Cargo", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_INGAME, min_value = 0, max_value = 31, step_size = 1 });
        this.AddSetting({ name = "quartercargo", description = "Quarterly", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_INGAME | CONFIG_BOOLEAN });
        this.AddSetting({ name = "divgoal", description = "Random Goals", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_INGAME, min_value = 0, max_value = 2, step_size = 1 });
        
        // Legacy category spacers to match your config
        this.AddCategory("xshunter", "--- Legacy ---", false);
        this.AddSetting({name = "rtd.category.CityBuilder", description = "Legacy Cat", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_NONE, min_value = 0, max_value = 0});
    }

    function AddCategory(code, title, spacer = true) 
    {
        local catname = "rtd.category." + code;
        if (spacer) {
            this.AddSetting({ name = catname + ".spacer", description = " ", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_NONE, min_value = 0, max_value = 0 });
            this.AddLabels(catname + ".spacer", { _0 = " " });
        }
        this.AddSetting({ name = catname, description = " ", easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0, flags = CONFIG_NONE, min_value = 0, max_value = 0 });
        this.AddLabels(catname, { _0 = title });
    }
}

RegisterGS(SentinelGS());