/**
 * AphidCB - Sendstats.nut
 * Handles reporting of statistics, population, and goals to Sentinel Admin.
 */

// Report Cargo Progress for a specific company
function CityBuilder::SendStatistics(company, chat_func, suffix_func)
{
    if (!GSCompany.ResolveCompanyID(company)) return;

    // Get Company Data 
    if (!("GetTownID" in this)) return;

    local town_id = this.GetTownID(company);
    if (!GSTown.IsValidTown(town_id)) return;

    // Report Cargo Requirements
    // We check if GetReq exists to prevent crashes
    if ("GetReq" in this) {
        local req_list = this.GetReq(town_id); 
        // Note: Full logic to print cargo requirements would go here.
        // For now, we ensure it doesn't crash.
    }
}

// Report Population Progress (FIXED LOOP)
function CityBuilder::SendPopulation()
{
    // FIX: Used numeric loop instead of GSCompanyList() to prevent "index does not exist" error
    for (local company = GSCompany.COMPANY_FIRST; company <= GSCompany.COMPANY_LAST; company++) {
        
        if (GSCompany.ResolveCompanyID(company) != GSCompany.COMPANY_INVALID) {
            
            // Retrieve Pop
            if ("GetTownID" in this) {
                local tid = this.GetTownID(company);
                if (GSTown.IsValidTown(tid)) {
                    local pop = GSTown.GetPopulation(tid);
                    
                    // Send to Sentinel Core via Admin Packet
                    // 'Sentinel' static class is available because it was loaded in main.nut
                    Sentinel.SendAdmin({ 
                        event = "populationupdated", 
                        company = company, 
                        population = pop,
                        townid = tid
                    });
                }
            }
        }
    }
}

// Report Goal Info (Win Condition)
function CityBuilder::SendGoalInfo()
{
    local target_pop = 0;
    
    // Try to read 'goal' setting from GS settings
    if (GSGameSettings.GetValue("gamegoal") > 0) target_pop = GSGameSettings.GetValue("gamegoal");
    else if (GSGameSettings.GetValue("goal") > 0) target_pop = GSGameSettings.GetValue("goal");
    
    Sentinel.SendAdmin({ 
        event = "goaltypeinfo", 
        goalmastergame = 1, // 1 = CityBuilder
        target_pop = target_pop
    });
}