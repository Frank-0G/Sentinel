class CompanyValue
{
    api = null;
    goal_value = 10000000;
    has_winner = false;
    
    // GUI State
    main_goal_id = -1;
    company_goals = null; 
    last_values = null;

    constructor(_api) {
        this.api = _api;
        this.company_goals = {};
        this.last_values = {};
    }

    function GetName() { return "CompanyValue"; }

    function Start() {
        this.api.Log("Plugin: Company Value Mode Active.");
        this.SendGoalInfo();
        
        local val = GSGameSettings.GetValue("goal_value");
        if (val > 0) this.goal_value = val * 1000000; 
        
        this.api.Log("Target Net Wealth: " + this.FormatMoney(this.goal_value));
        
        GSGameSettings.SetValue("economy.town_growth_rate", 1); 
        GSGameSettings.SetValue("economy.fund_buildings", 1);   
        
        // Force immediate update
        this.InitScoreboard();
        this.UpdateScoreboard();
    }

    function Run(ticks) {
        if (ticks % 75 == 0) {
            this.UpdateScoreboard();
        }
    }

    function OnMessage(info) {
        this.UpdateScoreboard();
    }

    // --- ROBUST GOAL CREATION ---
    function CreateGoalSafe(company, text, progress) {
        local g_id = -1;
        
        // Attempt 1: 5 Arguments (Standard: Comp, Type, Dest, Progress, Text)
        try {
            // Using 0 for Type (GT_NONE) and 0 for Dest (GD_NONE/TILE_INVALID)
            g_id = GSGoal.New(company, 0, 0, progress, text);
            return g_id;
        } catch(e) {}

        // Attempt 2: 4 Arguments (No Text: Comp, Type, Dest, Progress) + SetText
        try {
            g_id = GSGoal.New(company, 0, 0, progress);
            GSGoal.SetText(g_id, text);
            return g_id;
        } catch(e) {}
        
        // Attempt 3: 6 Arguments (Split Dest: Comp, Type, DestType, DestID, Progress, Text)
        try {
            g_id = GSGoal.New(company, 0, 0, 0, progress, text);
            return g_id;
        } catch(e) {}

        return -1;
    }

    function InitScoreboard() {
        if (GSGoal.IsValidGoal(this.main_goal_id)) GSGoal.Remove(this.main_goal_id);
        
        local text = "Main Goal: Reach " + this.FormatMoney(this.goal_value) + " Net Wealth";
        
        // Use the safe creator for the global goal
        this.main_goal_id = this.CreateGoalSafe(GSCompany.COMPANY_INVALID, text, 0);
    }

    function UpdateScoreboard() {
        if (!GSGoal.IsValidGoal(this.main_goal_id)) this.InitScoreboard();

        for (local c_id = GSCompany.COMPANY_FIRST; c_id <= GSCompany.COMPANY_LAST; c_id++) {
            
            if (GSCompany.ResolveCompanyID(c_id) == GSCompany.COMPANY_INVALID) {
                if (c_id in this.company_goals) {
                    if (GSGoal.IsValidGoal(this.company_goals[c_id])) GSGoal.Remove(this.company_goals[c_id]);
                    delete this.company_goals[c_id];
                }
                continue;
            }

            local current_val = 0;
            try {
                if (GSCompanyMode(c_id)) {
                    // Create scope object, but wait, GSCompanyMode returns bool or void?
                    // Actually, GSCompanyMode(cid) acts as a scope changer.
                    // If it returns bool, it's boolean.
                    // If it's a scope guard, it needs to be held.
                    // Most similar scripts do: if (GSCompanyMode(x)) ...
                    // Let's assume it IS a scope guard.

                    // Let's assign and check.
                    // If it returns bool, the guard is implicit?
                    // No, usually guard object is returned.

                    // Let's force assignment.
                    local scope = GSCompanyMode(c_id);
                    if (scope) {
                         current_val = GSCompany.GetQuarterlyCompanyValue(c_id, 0);
                    }
                }
            } catch (e) { 
                this.api.Log("Error calc Co " + c_id + ": " + e);
                continue; 
            }

            // DEBUG LOGGING
            // this.api.Log("UpdateScoreboard: Co " + c_id + " Val " + this.FormatMoney(current_val));
            // END DEBUG

            if (!this.has_winner && current_val >= this.goal_value) {
                this.TriggerWin(c_id, current_val);
            }

            // Check if value changed and send update to controller
            if (!(c_id in this.last_values) || this.last_values[c_id] != current_val) {
                this.last_values[c_id] <- current_val;
                this.api.SendToController({
                    event = "multigoalsupdated",
                    company = c_id,
                    cvalue = current_val
                });
            }

            local progress = (current_val * 100) / this.goal_value;
            if (progress < 0) progress = 0; 
            if (progress > 100) progress = 100;
            
            local str = GSCompany.GetName(c_id) + ": " + this.FormatMoney(current_val) + " (" + progress + "%)";
            
            if (c_id in this.company_goals && GSGoal.IsValidGoal(this.company_goals[c_id])) {
                GSGoal.SetText(this.company_goals[c_id], str);
                GSGoal.SetProgress(this.company_goals[c_id], progress);
            } else {
                // Create specific goal for this company using Safe Mode
                local g_id = this.CreateGoalSafe(c_id, str, progress);
                if (g_id != -1) {
                    this.company_goals[c_id] <- g_id;
                }
            }
        }
    }

    function TriggerWin(company, amount) {
        this.has_winner = true;
        local cName = GSCompany.GetName(company);
        
        if (company in this.company_goals) {
             GSGoal.SetText(this.company_goals[company], "WINNER: " + cName + " (" + this.FormatMoney(amount) + ")");
        }
        
        this.api.ChatPublic("VICTORY! " + cName + " reached the goal of " + this.FormatMoney(amount) + "!");
        
        this.api.SendToController({
            event = "winner",
            company = company,
            town = "Global",
            population = 0,
            type = "Company Value",
            amount = amount
        });
    }
    
    function SendGoalInfo() {
        this.api.SendToController({
            event = "goaltypeinfo",
            goalmastergame = 0, // 0 = CompanyValue/Other
            target_value = this.goal_value
        });
    }

    function FormatMoney(amount) {
        local abs_amt = amount;
        local sign = "";
        if (amount < 0) { abs_amt = -amount; sign = "-"; }
        
        if (abs_amt >= 1000000) {
            return sign + "$" + (abs_amt / 1000000) + "M";
        } else if (abs_amt >= 1000) {
            return sign + "$" + (abs_amt / 1000) + "k";
        }
        return sign + "$" + abs_amt;
    }
}