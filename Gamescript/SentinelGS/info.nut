class SentinelGS extends GSInfo
{
    function GetAuthor()        { return "Sentinel Team"; }
    function GetName()          { return "SentinelGS"; }
    function GetDescription()   { return "Modular GameScript Controller for OpenTTD."; }
    function GetVersion()       { return 1; }
    function GetDate()          { return "2026-04-10"; }
    function CreateInstance()   { return "SentinelCore"; }
    function GetShortName()     { return "SNTL"; }
    function GetAPIVersion()    { return "15"; }
    function GetUrl()           { return ""; }

    function GetSettings()
    {
        // --- GENERAL ---
        this.AddCategory("general", "--- General ---", false);

        this.AddSetting({
            name = "log_level", description = "Log Level",
            easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1,
            flags = CONFIG_INGAME, min_value = 0, max_value = 1
        });
        this.AddLabels("log_level", {_0 = "No logs", _1 = "All logs"});

        // Main Game Mode Switch
        this.AddSetting({
            name = "game_mode", description = "Game Mode Selection",
            easy_value = 0, medium_value = 1, hard_value = 2, custom_value = 0,
            flags = CONFIG_INGAME, min_value = 0, max_value = 9
        });

        this.AddLabels("game_mode", {
            _0 = "Mode 0: Company Value", _1 = "Mode 1: CityBuilder Classic", _9 = "Mode 9: Company Value GS4"
        });

        // --- COMPANY VALUE SETTINGS (for CompanyValueGS4 too) ---
        this.AddCategory("companyvalue", "--- Company Value Settings ---");

        AddSetting({
            name = "goal_mode", description = "Goal mode", min_value = 0, max_value = 1,
            easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1, step_size = 1,
            flags = CONFIG_NONE
        });
        AddLabels("goal_mode", {
            _0 = "Only rank companies by their values",
            _1 = "Reach target company value below"
        });

        AddSetting({
            name = "goal_value", description = "Target company value (in thousand £)",
            min_value = 250, max_value = 999999999,
            easy_value = 500, medium_value = 2500, hard_value = 5000,
            custom_value = 250,
            step_size = 250,
            flags = CONFIG_INGAME
        });

        AddSetting({
            name = "end_year",
            description = "Target end year (must be as same as in openttd.cfg)",
            min_value = 1950,
            max_value = 2300,
            easy_value = 1950,
            medium_value = 1950,
            hard_value = 1950,
            custom_value = 1950,
            flags = CONFIG_INGAME
        });

        AddSetting({
            name = "restart",
            description = "Target for restart (must be as same as in openttd.cfg)",
            min_value = 1950,
            max_value = 2300,
            easy_value = 1950,
            medium_value = 1950,
            hard_value = 1950,
            custom_value = 1950,
            flags = CONFIG_INGAME
        });

        // --- CITYBUILDER SETTINGS ---
        this.AddCategory("cargogoals", "--- CityBuilder Settings ---");

        this.AddSetting({
            name = "maxpopulation", description = "Max population allowed to claim",
            easy_value = 500, medium_value = 500, hard_value = 500, custom_value = 500,
            flags = CONFIG_INGAME, min_value = 0, max_value = 10000, step_size = 50
        });

        this.AddSetting({
            name = "rtd.cargogoal.difficulty", description = "Cargo Goal Difficulty",
            easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1,
            flags = CONFIG_INGAME, min_value = 0, max_value = 2
        });
        this.AddLabels("rtd.cargogoal.difficulty", {_0 = "Easy", _1 = "Normal", _2 = "Hard"});

        this.AddSetting({
            name = "rtd.congestion.difficulty", description = "Congestion Difficulty",
            easy_value = 1, medium_value = 1, hard_value = 1, custom_value = 1,
            flags = CONFIG_INGAME, min_value = 0, max_value = 6
        });
        this.AddLabels("rtd.congestion.difficulty", {
            _0 = "Very Easy", _1 = "Easy", _2 = "Normal", _3 = "Hard", _4 = "Very Hard", _5 = "Insane", _6 = "Disastrous"
        });

        this.AddSetting({
            name = "rtd.congestion.effect", description = "Congestion Effect",
            easy_value = 4, medium_value = 4, hard_value = 4, custom_value = 4,
            flags = CONFIG_INGAME, min_value = 1, max_value = 4
        });
        this.AddLabels("rtd.congestion.effect", {
            _1 = "Off", _2 = "Somewhat", _3 = "Moderate", _4 = "Entirely"
        });

        this.AddSetting({
            name = "rtd.town.periodical_expansion.rate", description = "Automated Growth Rate",
            easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
            flags = CONFIG_INGAME, min_value = 0, max_value = 4
        });
        this.AddLabels("rtd.town.periodical_expansion.rate", {
            _0 = "Never", _1 = "Rarely", _2 = "Uncommon", _3 = "Common", _4 = "Often"
        });

        this.AddSetting({
            name = "rtd.town.periodical_expansion.citybonus", description = "City Expansion Bonus",
            easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
            flags = CONFIG_INGAME, min_value = 0, max_value = 2
        });
        this.AddLabels("rtd.town.periodical_expansion.citybonus", {
            _0 = "None", _1 = "Double", _2 = "Triple"
        });

        this.AddSetting({
            name = "rtd.cargogoal.compatibility", description = "NewGRF Compatibility",
            easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
            flags = CONFIG_INGAME, min_value = 0, max_value = 1
        });
        this.AddLabels("rtd.cargogoal.compatibility", {_0 = "Default", _1 = "FIRS"});

        this.AddSetting({
            name = "shouldLimitations", description = "Enable Game Limits",
            easy_value = 0, medium_value = 0, hard_value = 0, custom_value = 0,
            flags = CONFIG_INGAME, min_value = 0, max_value = 1
        });
        this.AddLabels("shouldLimitations", {_0 = "Off", _1 = "On"});
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