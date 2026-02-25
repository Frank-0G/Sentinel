/**
 * AphidCB - Sendstats.nut
 * Handles reporting of statistics, population, and goals to Sentinel Admin.
 */

// Report Cargo Progress for a specific company
// Called by wrapper.nut during Monthly Reporting
function CityBuilder::SendStatistics(company, chat_func, suffix_func)
{
    if (!("companies" in this) || this.companies == null) return;
    
    local my_town = -1;
    foreach(comp in this.companies) {
        if (comp.id == company) {
            my_town = comp.my_town;
            break;
        }
    }
    
    if (my_town >= 0 && GSTown.IsValidTown(my_town)) {
        // Send Town Statistics payload
        local loc = GSTown.GetLocation(my_town);
        Sentinel.SendAdmin({ 
            event = "citybuilder", 
            action = "townstats", 
            company = company, 
            townid = my_town, 
            townname = GSTown.GetName(my_town), 
            population = GSTown.GetPopulation(my_town), 
            housecount = GSTown.GetHouseCount(my_town), 
            growthrate = GSTown.GetGrowthRate(my_town), 
            statue = GSTown.HasStatue(my_town), 
            location = "" + GSMap.GetTileX(loc) + "x" + GSMap.GetTileY(loc)
        });
        
        // Output Cargo Demands if possible
        if (my_town in this.towns && this.towns[my_town] != null) {
            local townObj = this.towns[my_town];
            if ("econ" in townObj && townObj.econ != null) {
                local num_cargos = townObj.econ.num_cargos;
                for (local i = 0; i < num_cargos; ++i) {
                    local goal = townObj.goal_cargo[i];
                    if (goal > 0) {
                        local cid = townObj.econ.enable_order[i];
                        local sup_c = townObj.supply_cargo[i];
                        local stk_c = townObj.stocked_cargo[i];
                        local suffix = suffix_func(cid);
                        
                        Sentinel.SendAdmin({
                            event = "citybuilder",
                            action = "towndemands",
                            townid = my_town,
                            cargo_suffix = suffix,
                            cargo_supply = sup_c,
                            cargo_goal = goal,
                            cargo_stocked = stk_c
                        });
                    }
                }
            }
        }
    }
}

// Report Population Progress
// Called by wrapper.nut during Monthly Reporting
function CityBuilder::SendPopulation()
{
    if (!("companies" in this) || this.companies == null) return;

    foreach(comp in this.companies) {
        local tid = comp.my_town;
        if (tid >= 0 && GSTown.IsValidTown(tid)) {
            local pop = GSTown.GetPopulation(tid);
            Sentinel.SendAdmin({ 
                event = "populationupdated", 
                company = comp.id, 
                population = pop,
                townid = tid
            });
        } else {
            Sentinel.SendAdmin({ 
                event = "populationupdated", 
                company = comp.id, 
                population = -1 
            });
        }
    }
}

// Report Goal Info (Win Condition)
function CityBuilder::SendGoalInfo()
{
    local target_pop = 0;
    
    // Try to read 'goal' setting from GS settings
    if (GSController.GetSetting("gamegoal") > 0) target_pop = GSController.GetSetting("gamegoal");
    else if (GSController.GetSetting("goal") > 0) target_pop = GSController.GetSetting("goal");
    
    Sentinel.SendAdmin({ 
        event = "goaltypeinfo", 
        goalmastergame = 1, // 1 = CityBuilder
        target_pop = target_pop
    });
}