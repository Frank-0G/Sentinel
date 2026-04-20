/**
 * AntiCheat Plugin for SentinelGS
 * Prevents players from building illegal level crossings over other companies' infrastructure.
 */
class AntiCheat
{
    api = null;

    constructor(_api) {
        this.api = _api;
    }

    function GetName() { return "AntiCheat"; }
    function Start() { 
        this.api.Log("Plugin Anti-Cheat: Initialized"); 
    }

    function Run(ticks) {
        // No background cycle needed for this event-based plugin
    }

    function check_crossing(c_id_str, comp_id_str, tiles_array) {
        GSController.Sleep(1); // Wait 1 tick for map update
        local c_id = c_id_str.tointeger();
        local comp_id = comp_id_str.tointeger();

        if (tiles_array.len() == 0) return;

        local min_x = 999999;
        local max_x = 0;
        local min_y = 999999;
        local max_y = 0;

        foreach (t_id_str in tiles_array) {
            local t_id = t_id_str.tointeger();
            local x = GSMap.GetTileX(t_id);
            local y = GSMap.GetTileY(t_id);
            if (x < min_x) min_x = x;
            if (x > max_x) max_x = x;
            if (y < min_y) min_y = y;
            if (y > max_y) max_y = y;
        }

        local crossing_demolished = false;

        for (local x = min_x; x <= max_x; x++) {
            for (local y = min_y; y <= max_y; y++) {
                local t_id = GSMap.GetTileIndex(x, y);

                local has_road = GSRoad.IsRoadTile(t_id);
                local has_rail = GSRail.IsRailTile(t_id);
                local has_tram = false;
                try { has_tram = GSRoad.IsTramTile(t_id); } catch(e) { }

                // Check where road and rail coexist (Level Crossing)
                if ((has_road || has_tram) && has_rail) {
                    local rail_owner = GSTile.GetOwner(t_id);
                    local road_owner = 255;

                    local neighbors = [
                        GSMap.GetTileIndex(x + 1, y), GSMap.GetTileIndex(x - 1, y),
                        GSMap.GetTileIndex(x, y + 1), GSMap.GetTileIndex(x, y - 1)
                    ];

                    foreach (nt_id in neighbors) {
                        if (!GSMap.IsValidTile(nt_id)) continue;
                        if (GSRoad.IsRoadTile(nt_id) && !GSRail.IsRailTile(nt_id)) {
                            road_owner = GSTile.GetOwner(nt_id);
                            if (road_owner != 255) break;
                        }
                    }

                    // Fallback: If still 255, it might be a tram
                    if (road_owner == 255 && has_tram) {
                        foreach (nt_id in neighbors) {
                            if (!GSMap.IsValidTile(nt_id)) continue;
                            if (GSRoad.IsTramTile(nt_id) && !GSRail.IsRailTile(nt_id)) {
                                road_owner = GSTile.GetOwner(nt_id);
                                if (road_owner != 255) break;
                            }
                        }
                    }

                    local violation = false;
                    local to_remove = ""; // "rail", "road"
                    local original_owner = 255;

                    if (rail_owner == comp_id) {
                        // Builder is the rail owner. Check if it's over someone else's road.
                        if (road_owner != 255 && road_owner != comp_id) {
                            violation = true; to_remove = "rail"; original_owner = road_owner;
                        }
                    } else if (road_owner == comp_id) {
                        // Builder is the road owner. Check if it's over someone else's rail.
                        if (rail_owner != 255 && rail_owner != comp_id) {
                            violation = true; to_remove = "road"; original_owner = rail_owner;
                        }
                    }

                    if (violation) {
                         if (!crossing_demolished) {
                            this.api.Log("[AntiCheat] !!! VIOLATION DETECTED !!! Tile " + t_id + " - " + to_remove + " built by Co " + comp_id + " over Co " + original_owner);

                            local __mode = GSCompanyMode(comp_id);
                            local res = false;

                            if (to_remove == "rail") {
                                // For rail-over-road, we must act as the road owner to demolish the road overlay first
                                if (road_owner != 255 && road_owner != comp_id) {
                                    {
                                        local __tmp_mode = GSCompanyMode(road_owner);
                                        GSTile.DemolishTile(t_id); 
                                    }
                                    // Remove the violating rail
                                    {
                                        local __tmp_mode = GSCompanyMode(comp_id);
                                        res = GSTile.DemolishTile(t_id);
                                    }
                                    // Restore road as original owner
                                    if (road_owner != 255) {
                                        local __tmp_mode = GSCompanyMode(road_owner);
                                        GSCompany.ChangeBankBalance(road_owner, 2000, GSCompany.EXPENSES_OTHER, t_id);
                                        local road_neighbors = [];
                                        foreach (nt_id in neighbors) {
                                            if (GSMap.IsValidTile(nt_id) && GSRoad.IsRoadTile(nt_id)) road_neighbors.push(nt_id);
                                        }
                                        if (road_neighbors.len() >= 1) {
                                            GSController.Sleep(1);
                                            local r_type = has_tram ? GSRoad.ROADTYPE_TRAM : GSRoad.ROADTYPE_ROAD;
                                            GSRoad.SetCurrentRoadType(r_type);
                                            foreach (nt_id in road_neighbors) GSRoad.BuildRoad(t_id, nt_id);
                                        }
                                    }
                                } else {
                                    res = GSRail.RemoveRail(t_id, t_id, GSRail.GetRailType(t_id));
                                }
                            } else if (to_remove == "road") {
                                local rtype = has_tram ? GSRoad.ROADTYPE_TRAM : GSRoad.ROADTYPE_ROAD;
                                res = GSRoad.RemoveRoad(t_id, rtype);
                                if (!res) res = GSTile.DemolishTile(t_id);
                            }

                            this.api.ChatPrivate(c_id, "ILLEGAL CROSSING: You cannot build over another company's infrastructure! Use a bridge or tunnel.");
                            crossing_demolished = true;
                        }
                    }
                }
            }
        }
    }
}
