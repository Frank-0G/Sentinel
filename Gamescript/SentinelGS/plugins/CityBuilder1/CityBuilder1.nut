require("version.nut");
require("town.nut");
require("RTDCache.nut");

/*
 CityBuilder by Knogle & Frank
 This script is inspired by, and/or may include parts from other scripts
  "Minimal GS" by Zuu
  "Neighbours are important" by Zuu
  "Realistic Town Dependencies" by Fanatik
  etc.
 
 Special thanks goes to:
  The OTTD devs for the GameScript feature, inspiration, ideas and help.
  The_Dude for inspiration, ideas and help.
  Zuu for inspiration, ideas and help.
  etc.
   
*/
CLAIM_NOT_CLAIMED <- -1; // town not claimed
CLAIM_TOO_BIG <- -2; // claimed town is bigger than <maxpopulation>
CLAIM_CITY <- -3; // claimed town is a city
CLAIM_OWNED <- -4; // claimed town is already owned by someone else
CLAIM_OVERLAP <- -5; // protected area of claimed town would overlap with protected area of another company

class CityBuilder
{
		_load_data = null;
		populations = null;
		claimed_towns = null;
		companyStartDate = null;
		signlist = null;
		sign = null;
		towns = null;
		oldsign = null;
		whenwas = null;
		whenwas_last = 0;
		fromLoad = false;
		last_date = 0;
		fromSavegame = false;
		cache = RTDCache();
		townmanagedelay = 31;
		lasttownmanage = 0;
		lasttimetaken = 31;
		maxpopulation = 500;
		protectionrange = 20;
		protectionsigns = false;
		_mapX = 0;
		_mapY = 0;

		constructor() {
			populations = GSList();
			companyStartDate = GSList();
			signlist = GSList();
			claimed_towns = GSList();
			towns = null;
		}	
		function CreateTownList();
		story = []; //storypage ids
	
}

function CityBuilder::GetName()			{ return "CityBuilder v1 by Frank and Knogle"; }

function CityBuilder::SendGoalInfo()
{
	SendAdmin( { event = "goalunitinfo", goalunitvaluetext = "a population of", goalunitname = "inhabitant", goalunitnameplural = "inhabitants" } );
}

// Start function, this is where it all begins
function CityBuilder::Initialize()
{
	Sentinel.InfoMessage("[CityBuilder] CityBuilder by Knogle and Frank is being started...");

	local start_tick = GSController.GetTick();

	if (!this.fromLoad) {
		local now = GSDate.GetSystemTime();
		this.last_date = GSDate.GetCurrentDate();
	}	

	Sentinel.InfoMessage("[CityBuilder] Preparing the cache...");
	// Sync the Cache Initially
	this.cache.Sync();
	this.cache.Print();

	_mapX = GSMap.GetMapSizeX() - 2;
	_mapY = GSMap.GetMapSizeY() - 2;
	
	// Override Game Settings with custom values
	// - Disallow Funding of Buildings (default)
	GSGameSettings.SetValue("economy.fund_buildings", GSController.GetSetting("rtd.allow_city_funding"));
	// - Set Town Growth Rate to 2
	GSGameSettings.SetValue("economy.town_growth_rate", 2);

	this.last_date = GSDate.GetCurrentDate();

	Sentinel.InfoMessage("[CityBuilder] (0%) Initializing town data...");
	// Set initial time the towns will grow
	local lastdisplaytick = GSController.GetTick();
	local all_towns = GSTownList();
	local towncount = all_towns.Count();
	local citycount = 0;
	local currenttown = 0;
	this.towns = [];
	foreach(townid, _ in all_towns)
	{
		local town = Town(townid, this.cache);
		this.towns.append(town);
		if (GSController.GetTick() > (lastdisplaytick + 100)) // show a status update roughly every 3 seconds
		{
			lastdisplaytick = GSController.GetTick();
			local percentage = ((currenttown * 100) / towncount);
			Sentinel.InfoMessage("[CityBuilder] (" + percentage + "%) Initializing town data...");
		}
		town.check_timer = GSBase.RandRange(20) + 10;
		town.ManageTown(0);
		if (GSTown.IsCity(townid))
		{
			BuildSign(GSTown.GetLocation(townid), GSText(GSText.STR_CITY)); // add a sign to each city so that players know that the city is NOT claimable
			citycount++;
		}
		currenttown++;
	}
	Sentinel.InfoMessage("[CityBuilder] (100%) Initialized " + (towncount - citycount) + " towns and " + citycount + " cities.");

	local setup_duration = GSController.GetTick() - start_tick;

	GSLog.Info("Game setup done");
	GSLog.Info("Setup took " + setup_duration + " ticks");
	GSLog.Info("");

	GSLog.Info("Happy playing");

	// Log the event to Sentinel
	Sentinel.InfoMessage("[CityBuilder] CityBuilder has started. Setup took " + setup_duration + " ticks.");
}

function CityBuilder::Process()
{
	// Determine delta Ticks since last Call
	local date = GSDate.GetCurrentDate();
	local delta = date - this.last_date;
	this.last_date = date;

	// Stop, if already fired once this tick.

	if (delta == 0) return;

	// Resync Cache
	this.cache.SyncOnDemand(delta);

	CheckMap();

	if ((GSController.GetTick() - lasttownmanage) > townmanagedelay)
	{
		local manageticks = GSController.GetTick();
		// Loop All Towns
		foreach (town in this.towns) {
			town.ManageTownOnDemand(delta);
		}
		lasttownmanage = GSController.GetTick();
		local townmanagetimetaken = GSController.GetTick() - manageticks;
		DebugMessage("Town management took " + townmanagetimetaken + " ticks");
		
		local diff = (townmanagetimetaken - townmanagedelay);
		if (diff > 0) // generously increase when processing takes longer than the delay
			townmanagedelay = townmanagedelay + (diff * 0.3);
		if ((diff < (townmanagedelay * -0.1)) && (townmanagetimetaken <= lasttimetaken) && (townmanagetimetaken > 0)) // only decrease the delay under special circumstances
			townmanagedelay = townmanagedelay + (diff * 0.03);
		
		if (townmanagedelay < 31) // sanity check: never go lower than a second whatever happens
			townmanagedelay = 31;
		
		lasttimetaken = townmanagetimetaken;
		
		DebugMessage("Town management delay is now " + townmanagedelay + " ticks");
	}
	
}

function CityBuilder::Save()
{
	// Save TODO
	// - Cached Values
	// - Congested Cities
	// - City Growth Steps
	
	Log.Info("TRYING TO SAVE...", Log.LVL_INFO);

	return {};
}

function CityBuilder::Load(version, tbl)
{
	Log.Info("LOAD()", Log.LVL_INFO);
	
	// Remember that we did load from a savegame at some point
	// (unused for now, but might come in handy)
	this.fromSavegame = true;
}

function CityBuilder::DebugMessage(message)
{
    Sentinel.DebugMessage(message);
	//Sentinel.IrcPublicMessage("DEBUG: " + message);
}

function CityBuilder::ProcessEvent(event)
{
	local eventType = event.GetEventType();
	
	// ### NEW COMPANY ###
	if(eventType == GSEvent.ET_COMPANY_NEW)
	{
		GSLog.Info("Found new company!");
		// Log the event to Sentinel
		DebugMessage("Found new company!");
		// Done Logging the event to Sentinel
		local newcompany = GSEventCompanyNew.Convert(event);
		GSNews.Create(GSNews.NT_GENERAL, GSText(GSText.STR_PLACE_HQ), newcompany.GetCompanyID(), GSNews.NR_NONE, 0);
		Sentinel.TeamChat("-=[ Build your HQ in a town to claim it for city building ]=-", newcompany.GetCompanyID());
		claimed_towns.AddItem(newcompany.GetCompanyID(), CLAIM_NOT_CLAIMED);
		companyStartDate.AddItem(newcompany.GetCompanyID(), GSDate.GetCurrentDate());
	}
	// ### BANKRUPT COMPANY ###
	if (eventType == GSEvent.ET_COMPANY_BANKRUPT)
	{
		// Delete the company from the company pool
		GSLog.Info("Found bankrupt company!");
		// Log the event to Sentinel
		DebugMessage("Found bankrupt company!");
		// Done Logging the event to Sentinel
		local company_id = GSEventCompanyBankrupt.Convert(event).GetCompanyID();
		if (populations.HasItem(company_id))
			populations.RemoveItem(company_id);
		if (claimed_towns.HasItem(company_id))
		{
			if (GSTown.IsValidTown(claimed_towns.GetValue(company_id)))
			{
				local townlocation = GSTown.GetLocation(claimed_towns.GetValue(company_id));
				RemoveSign(townlocation);
				RemoveProtectionSigns(townlocation);
			}
			claimed_towns.RemoveItem(company_id);
			companyStartDate.RemoveItem(company_id);
		}
	}
	// ### MERGE COMPANY ###
	if (eventType == GSEvent.ET_COMPANY_MERGER)
	{
		local merge = GSEventCompanyMerger.Convert(event);
		local oldcompanyid = merge.GetOldCompanyID();
		GSLog.Info("Caught company merge of company " + oldcompanyid + " into " + GSCompany.GetName(merge.GetNewCompanyID()));
		// Log the event to Sentinel
		DebugMessage("Caught company merge of company " + oldcompanyid + " into " + GSCompany.GetName(merge.GetNewCompanyID()));
		// Done Logging the event to Sentinel
		if (populations.HasItem(oldcompanyid))
			populations.RemoveItem(oldcompanyid);
		if (claimed_towns.HasItem(oldcompanyid))
		{
			if (GSTown.IsValidTown(claimed_towns.GetValue(oldcompanyid)))
			{
				local townlocation = GSTown.GetLocation(claimed_towns.GetValue(oldcompanyid));
				RemoveSign(townlocation);
				RemoveProtectionSigns(townlocation);
				SendAdmin( { event = "citybuilder", action = "unclaimed", company = oldcompanyid } );  //new location for this SendAdmin
			}
			claimed_towns.RemoveItem(oldcompanyid);
			//SendAdmin( { event = "citybuilder", action = "unclaimed", company = oldcompanyid } );  //old location for this SendAdmin
			companyStartDate.RemoveItem(oldcompanyid);
		}

		// Merge the companies
	}
}

function CityBuilder::RemoveProtectionSigns(location)
{
	if ((protectionrange > 0) && (protectionsigns))
	{
		local locationX = GSMap.GetTileX(location);
		local locationY = GSMap.GetTileY(location);
		RemoveSign(GSMap.GetTileIndex(Max(locationX - protectionrange, 1), Max(locationY - protectionrange, 1)));
		RemoveSign(GSMap.GetTileIndex(Max(locationX - protectionrange, 1), Min(locationY + protectionrange, _mapY)));
		RemoveSign(GSMap.GetTileIndex(Min(locationX + protectionrange, _mapX), Min(locationY + protectionrange, _mapY)));
		RemoveSign(GSMap.GetTileIndex(Min(locationX + protectionrange, _mapX), Max(locationY - protectionrange, 1)));
	}
}

function CityBuilder::IsProtected(tile, range)
{
	// nothing is protected if the protection feature is disabled
	if (protectionrange <= 0)
		return false;
	
	local locationX = GSMap.GetTileX(tile);
	local locationY = GSMap.GetTileY(tile);
	foreach (company_id, town_id in claimed_towns)
	{
		if (!GSTown.IsValidTown(town_id))
			continue;
		local townlocation = GSTown.GetLocation(town_id);
		local areastart = GSMap.GetTileIndex(GSMap.GetTileX(townlocation) - range, GSMap.GetTileY(townlocation) - range);
		local areaend = GSMap.GetTileIndex(GSMap.GetTileX(townlocation) + range, GSMap.GetTileY(townlocation) + range);
		if ((locationX >= GSMap.GetTileX(areastart)) && (locationY >= GSMap.GetTileY(areastart)) && (locationX <= GSMap.GetTileX(areaend)) && (locationY <= GSMap.GetTileY(areaend)))
			return true;
	}
	return false;
}

function CityBuilder::HandleHQBuilt(company_id)
{
	local company_hq = GSCompany.GetCompanyHQ(company_id);
	// check if HQ already existed and has been relocated
	if (claimed_towns.HasItem(company_id) && GSTown.IsValidTown(claimed_towns.GetValue(company_id)))
	{
		local lasttown = claimed_towns.GetValue(company_id);
		local townlocation = GSTown.GetLocation(lasttown);
		if (lasttown == GSTile.GetClosestTown(company_hq))
			return; // HQ was moved within the same town area, don't do anything
		DebugMessage(GSCompany.GetName(company_id) + " moved his HQ from " + GSTown.GetName(lasttown) + " to " + GSTown.GetName(GSTile.GetClosestTown(company_hq)));
		RemoveSign(townlocation);
		RemoveProtectionSigns(townlocation);
		claimed_towns.SetValue(company_id, CLAIM_NOT_CLAIMED);
	}
	
	// nothing more to do if no HQ is placed
	if (company_hq == GSMap.TILE_INVALID)
		return;
	
	// check HQ placement
	local closesttown = GSTile.GetClosestTown(company_hq);
	if (!CheckTown(company_id, closesttown))
	{
		local companyname = GSCompany.GetName(company_id);
		local townname = GSTown.GetName(closesttown);
		// check whether town is too big for getting claimed
		if (GSTown.GetPopulation(closesttown) > maxpopulation)
		{
			GSLog.Info(companyname + " tried to claim " + townname + ", only towns < " + maxpopulation + " can be claimed");
			DebugMessage(companyname + " tried to claim " + townname + ", only towns < " + maxpopulation + " can be claimed");
			Sentinel.TeamChat("Only towns smaller than " + maxpopulation + " can be claimed -- Please move your HQ to a smaller TOWN to participate in the game!", company_id);
			claimed_towns.SetValue(company_id, CLAIM_TOO_BIG);
			return;
		}
		
		local townlocation = GSTown.GetLocation(closesttown);
		if (IsProtected(townlocation, protectionrange * 2)) // check for doubled protection area (existing claimed town + new claimed town shouldn't overlap)
		{
			DebugMessage(companyname + " tried to claim " + townname + ", which is overlapping with an existing claimed town area.");
			Sentinel.TeamChat("Your protected area would overlap with the area of someone else, you cannot claim this town, please relocate your HQ!", company_id);
			claimed_towns.SetValue(company_id, CLAIM_OVERLAP);
			return;
		}
		claimed_towns.SetValue(company_id, closesttown);
		GSLog.Info(companyname + " claimed " + townname);
		BuildSign(townlocation, GSText(GSText.STR_HQCITY, company_id));
		GSNews.Create(GSNews.NT_GENERAL, GSText(GSText.STR_NEW_HQ, company_id, closesttown), GSCompany.COMPANY_INVALID, GSNews.NR_TOWN, closesttown);
		DebugMessage(companyname + " claimed " + townname);
		Sentinel.ServerChat(companyname + " claimed " + townname);
		SendAdmin( { event = "citybuilder", action = "claimed", company = company_id, town = townname, population = GSTown.GetPopulation(closesttown), x = GSMap.GetTileX(GSTown.GetLocation(closesttown)), y = GSMap.GetTileY(GSTown.GetLocation(closesttown)) } );
		if (protectionrange > 0)
		{
			local locationX = GSMap.GetTileX(townlocation);
			local locationY = GSMap.GetTileY(townlocation);
			local areastart = GSMap.GetTileIndex(Max(locationX - protectionrange, 1), Max(locationY - protectionrange, 1));
			local areaend = GSMap.GetTileIndex(Min(locationX + protectionrange, _mapX), Min(locationY + protectionrange, _mapY));
			local exceptioncompanies = CompaniesInArea(areastart, areaend);
			foreach (exceptioncompanyid, _ in exceptioncompanies)
			{
				if (exceptioncompanyid != company_id)
					SendAdmin( { event = "citybuilder", action = "protectionexception", company = company_id, exceptioncompany = exceptioncompanyid } );
			}
			if (protectionsigns)
			{
				BuildSign(areastart, GSText(GSText.STR_HQAREA_TOP, company_id));
				BuildSign(areaend, GSText(GSText.STR_HQAREA_BOTTOM, company_id));
				BuildSign(GSMap.GetTileIndex(Max(locationX - protectionrange, 1), Min(locationY + protectionrange, _mapY)), GSText(GSText.STR_HQAREA_RIGHT, company_id));
				BuildSign(GSMap.GetTileIndex(Min(locationX + protectionrange, _mapX), Max(locationY - protectionrange, 1)), GSText(GSText.STR_HQAREA_LEFT, company_id));
			}
		}
		SendDemands();
	}
	else if (CheckTown(company_id, closesttown) == "CITY" )
	{
		claimed_towns.SetValue(company_id, CLAIM_CITY);
		//Show error message/chat message/anything that HQ's aren't meant to be built in cities, and they'd have to move it
		GSLog.Info(GSCompany.GetName(company_id) + " tried to claim a CITY, tell them they can't!");
		DebugMessage(GSCompany.GetName(company_id) + " tried to claim a CITY, telling them they can't!");
		Sentinel.TeamChat("You built your HQ in a CITY, which can't be claimed -- Please move your HQ to a TOWN to participate in the game!", company_id);
	}
	else if (CheckTown(company_id, closesttown) == "OWNED")
	{
		claimed_towns.SetValue(company_id, CLAIM_OWNED);
		//Show error message/chat message/anything that town was already claimed, and they'd have to move their HQ
		GSLog.Info(GSCompany.GetName(company_id) + " tried to claim a town already claimed by someone else, tell them they can't!");
		DebugMessage(GSCompany.GetName(company_id) + " tried to claim a town already claimed by someone else, telling them they can't!");
		Sentinel.TeamChat("You built your HQ in a town already claimed by someone else, please move it to participate in the game!", company_id);
	}
}

function CityBuilder::Min(val1, val2)
{
	if (val1 <= val2)
		return val1;
	if (val2 < val1)
		return val2;
}

function CityBuilder::Max(val1, val2)
{
	if (val1 >= val2)
		return val1;
	if (val2 > val1)
		return val2;
}

function CityBuilder::CompaniesInArea(startTile, endTile)
{
	local companylist = GSList();
	local xTile = GSMap.GetTileX(startTile);
	local yTile = GSMap.GetTileY(startTile);
	local xSpread = (GSMap.GetTileX(endTile) - GSMap.GetTileX(startTile));
	local ySpread = (GSMap.GetTileY(endTile) - GSMap.GetTileY(startTile));
	local xSpreadCur = 0;
	local ySpreadCur = 0;
	local xModifier = (xSpread >= 0) ? 1 : -1;
	local yModifier = (ySpread >= 0) ? 1 : -1;
	if (xSpread < 0)
		xSpread = (xSpread * -1);
	if (ySpread < 0)
		ySpread = (ySpread * -1);
		
	local tileCount = 0;
	local xCoord = xTile;
	local yCoord = yTile;
	while (xSpreadCur <= xSpread)
	{
		ySpreadCur = 0;
		yCoord = yTile;
		while (ySpreadCur <= ySpread)
		{
			local tileowner = GSTile.GetOwner(GSMap.GetTileIndex(xCoord, yCoord));
			if (tileowner != GSCompany.COMPANY_INVALID)
			{
				if (!companylist.HasItem(tileowner))
					companylist.AddItem(tileowner, 0);
			}
			tileCount++;
			yCoord = (yCoord + yModifier);
			ySpreadCur++;
		}
		xCoord = (xCoord + xModifier);
		xSpreadCur++;
	}
	return companylist;
}

function CityBuilder::CheckMap()
{
	local whenwas = GSDate.GetMonth(GSDate.GetCurrentDate());
	GSLog.Info("Checking Map");
	foreach (company_id, town_id in claimed_towns)
	{
		if (whenwas > whenwas_last)
		{
			switch (town_id)
			{
				case CLAIM_NOT_CLAIMED:
					GSLog.Info("Place your HQ");
					Sentinel.TeamChat("-=[ Build your HQ in a town to claim it for city building ]=-", company_id);
					break;
				case CLAIM_TOO_BIG:
					Sentinel.TeamChat("Only towns smaller than " + maxpopulation + " can be claimed -- Please move your HQ to a smaller TOWN to participate in the game!", company_id);
					break;
				case CLAIM_CITY:
					Sentinel.TeamChat("You built your HQ in a CITY, which can't be claimed -- Please move your HQ to a TOWN to participate in the game!", company_id);
					break;
				case CLAIM_OWNED:
					Sentinel.TeamChat("You built your HQ in a town already claimed by someone else, please move it to participate in the game!", company_id);
					break;
				case CLAIM_OVERLAP:
					Sentinel.TeamChat("Your protected area would overlap with the area of someone else, you cannot claim this town, please relocate your HQ!", company_id);
					break;
			}

			SendDemands()
			
		}
		
		if (town_id >= 0)
		{
			local inhabitants = GSTown.GetPopulation(town_id);
			if (populations.HasItem(company_id))
			{
				if (populations.GetValue(company_id) != inhabitants)
				{
					populations.SetValue(company_id, inhabitants);
					local populationMessage = { event = "populationupdated", company = company_id, population = inhabitants };
					//local populationMessage = { event = "populationupdated", company = company_id+1, population = inhabitants, companyage = GSDate.GetCurrentDate() - companyStartDate.GetValue(company_id) };
					SendAdmin(populationMessage);
				}
			}
			else
			{
				populations.AddItem(company_id, inhabitants);
				local populationMessage = { event = "populationupdated", company = company_id, population = inhabitants };
				//local populationMessage = { event = "populationupdated", company = company_id+1, population = inhabitants, companyage = GSDate.GetCurrentDate() - companyStartDate.GetValue(company_id) };
				SendAdmin(populationMessage);
			}
		}
		else if ((populations.HasItem(company_id)) && (populations.GetValue(company_id) > 0))
		{
			populations.SetValue(company_id, -1);
			local populationMessage = { event = "populationupdated", company = company_id, population = -1 };
			//local populationMessage = { event = "populationupdated", company = company_id+1, population = -1, companyage = GSDate.GetCurrentDate() - companyStartDate.GetValue(company_id) };
			SendAdmin(populationMessage);
		}
		
	}
	whenwas_last = whenwas;
}

function CityBuilder::SendPopulation()
{
  GSLog.Info("Sending Population");
	foreach (company_id, townid in claimed_towns)
	{
		if (townid >= 0)
		{
			local inhabitants = GSTown.GetPopulation(townid);
			if (populations.HasItem(company_id))
			{
				local populationMessage = { event = "populationupdated", company = company_id, population = inhabitants };
				//local populationMessage = { event = "populationupdated", company = company_id+1, population = inhabitants, companyage = GSDate.GetCurrentDate() - companyStartDate.GetValue(company_id) };
				SendAdmin(populationMessage);
			}
		}
		else
		{
			local populationMessage = { event = "populationupdated", company = company_id, population = -1 };
			//local populationMessage = { event = "populationupdated", company = company_id+1, population = -1, companyage = GSDate.GetCurrentDate() - companyStartDate.GetValue(company_id) };
			SendAdmin(populationMessage);
		}
	}
}

function CityBuilder::SendDemands()
{
	// First, let's clear the table of demands for ALL companies!
	SendAdmin( { event = "citybuilder", action = "cleardemands" } );

	// Now, let's fill the table / dictionary again with all demands for ALL claimed towns!
	foreach (company_id, townid in claimed_towns)
	{
		if (townid >= 0)
		{
			
			SendAdmin( { event = "citybuilder", action = "townstats", company = company_id, townid = townid, townname = GSTown.GetName(townid), population = GSTown.GetPopulation(townid), housecount = GSTown.GetHouseCount(townid), growthrate = GSTown.GetGrowthRate(townid), statue = GSTown.HasStatue(townid), location = "" + GSMap.GetTileX(GSTown.GetLocation(townid)) + "x" + GSMap.GetTileY(GSTown.GetLocation(townid))} );
						
			if (populations.HasItem(company_id))
			{
				if (GSTown.GetCargoGoal(townid, GSCargo.TE_PASSENGERS) != 0) 
				{
          local tmcargo = Sentinel.GetCargoName(0);
					SendAdmin( { event = "citybuilder", action = "towndemands", townid = townid, cargo_suffix = tmcargo, cargo_supply = GSTown.GetLastMonthReceived(townid, GSCargo.TE_PASSENGERS), cargo_goal = GSTown.GetCargoGoal(townid, GSCargo.TE_PASSENGERS), cargo_stocked = 0 } );
					//SendAdmin( { event = "citybuilder", action = "towndemands", townid = townid, cargo_suffix = "Passengers", cargo_supply = GSTown.GetLastMonthReceived(townid, GSCargo.TE_PASSENGERS), cargo_goal = GSTown.GetCargoGoal(townid, GSCargo.TE_PASSENGERS), cargo_stocked = 0 } );
				}
				if (GSTown.GetCargoGoal(townid, GSCargo.TE_MAIL) != 0) {
          local tmcargo = Sentinel.GetCargoName(2);
					SendAdmin( { event = "citybuilder", action = "towndemands", townid = townid, cargo_suffix = tmcargo, cargo_supply = GSTown.GetLastMonthReceived(townid, GSCargo.TE_MAIL), cargo_goal = GSTown.GetCargoGoal(townid, GSCargo.TE_MAIL), cargo_stocked = 0 } );
					//SendAdmin( { event = "citybuilder", action = "towndemands", townid = townid, cargo_suffix = "Mail", cargo_supply = GSTown.GetLastMonthReceived(townid, GSCargo.TE_MAIL), cargo_goal = GSTown.GetCargoGoal(townid, GSCargo.TE_MAIL), cargo_stocked = 0 } );
				}
				if (GSTown.GetCargoGoal(townid, GSCargo.TE_WATER) != 0) {
          local tmcargo = Sentinel.GetCargoName(9);
					SendAdmin( { event = "citybuilder", action = "towndemands", townid = townid, cargo_suffix = tmcargo, cargo_supply = GSTown.GetLastMonthReceived(townid, GSCargo.TE_WATER), cargo_goal = GSTown.GetCargoGoal(townid, GSCargo.TE_WATER), cargo_stocked = 0 } );
					//SendAdmin( { event = "citybuilder", action = "towndemands", townid = townid, cargo_suffix = "Water", cargo_supply = GSTown.GetLastMonthReceived(townid, GSCargo.TE_WATER), cargo_goal = GSTown.GetCargoGoal(townid, GSCargo.TE_WATER), cargo_stocked = 0 } );
				}
				if (GSTown.GetCargoGoal(townid, GSCargo.TE_GOODS) != 0) {
          local tmcargo = Sentinel.GetCargoName(5);
					SendAdmin( { event = "citybuilder", action = "towndemands", townid = townid, cargo_suffix = tmcargo, cargo_supply = GSTown.GetLastMonthReceived(townid, GSCargo.TE_GOODS), cargo_goal = GSTown.GetCargoGoal(townid, GSCargo.TE_GOODS), cargo_stocked = 0 } );
					//SendAdmin( { event = "citybuilder", action = "towndemands", townid = townid, cargo_suffix = "Goods", cargo_supply = GSTown.GetLastMonthReceived(townid, GSCargo.TE_GOODS), cargo_goal = GSTown.GetCargoGoal(townid, GSCargo.TE_GOODS), cargo_stocked = 0 } );
				}
				if (GSTown.GetCargoGoal(townid, GSCargo.TE_FOOD) != 0) {
          local tmcargo = Sentinel.GetCargoName(11);
					SendAdmin( { event = "citybuilder", action = "towndemands", townid = townid, cargo_suffix = tmcargo, cargo_supply = GSTown.GetLastMonthReceived(townid, GSCargo.TE_FOOD), cargo_goal = GSTown.GetCargoGoal(townid, GSCargo.TE_FOOD), cargo_stocked = 0 } );
					//SendAdmin( { event = "citybuilder", action = "towndemands", townid = townid, cargo_suffix = "Food", cargo_supply = GSTown.GetLastMonthReceived(townid, GSCargo.TE_FOOD), cargo_goal = GSTown.GetCargoGoal(townid, GSCargo.TE_FOOD), cargo_stocked = 0 } );
				}
			}
		}
	}
}

// SendStatistics and SendStatisticsIRC disabled... maybe used in other way
/*function CityBuilder::SendStatistics(playerid, companystats)
{
	if (claimed_towns.HasItem(companystats))
	{
		if (GSTown.IsValidTown(claimed_towns.GetValue(companystats)))
		{
			local townid = claimed_towns.GetValue(companystats);
			local companyname = GSCompany.GetName(companystats);
			local townname = GSTown.GetName(townid);
			local inhabitants = GSTown.GetPopulation(townid);
			local houses = GSTown.GetHouseCount(townid);
			
			if (populations.HasItem(companystats))
			{
				Sentinel.TeamChat("-= Town Info =-", companystats);
				Sentinel.TeamChat("Town Name: " + townname + "", companystats);
				Sentinel.TeamChat("Inhabitants: " + inhabitants + "", companystats);
				Sentinel.TeamChat("No. of Houses: " + houses + "", companystats);
				Sentinel.TeamChat(" ", companystats);
				Sentinel.TeamChat("-= Cargo Information =-", companystats);
				if (GSTown.GetCargoGoal(townid, GSCargo.TE_PASSENGERS) != 0) {
					if (GSTown.GetLastMonthReceived(townid, GSCargo.TE_PASSENGERS) <= GSTown.GetCargoGoal(townid, GSCargo.TE_PASSENGERS)) {
					Sentinel.TeamChat("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_PASSENGERS) + "/" + GSTown.GetCargoGoal(townid, GSCargo.TE_PASSENGERS) + " Passengers (Still Required)", companystats);
					}
					else
					{
					Sentinel.TeamChat("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_PASSENGERS) + "/" + GSTown.GetCargoGoal(townid, GSCargo.TE_PASSENGERS) + " Passengers (Delivered)", companystats);
					}
				}
				if (GSTown.GetCargoGoal(townid, GSCargo.TE_MAIL) != 0) {
					if (GSTown.GetLastMonthReceived(townid, GSCargo.TE_MAIL) <= GSTown.GetCargoGoal(townid, GSCargo.TE_MAIL)) {
					Sentinel.TeamChat("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_MAIL) + "/" + GSTown.GetCargoGoal(townid, GSCargo.TE_MAIL) + " bags of Mail (Still Required)", companystats);
					}
					else
					{
					Sentinel.TeamChat("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_MAIL) + "/" + GSTown.GetCargoGoal(townid, GSCargo.TE_MAIL) + " bags of Mail (Delivered)", companystats);
					}
				}
				if (GSTown.GetCargoGoal(townid, GSCargo.TE_WATER) != 0) {
					if (GSTown.GetLastMonthReceived(townid, GSCargo.TE_WATER) <= GSTown.GetCargoGoal(townid, GSCargo.TE_WATER)) {
					Sentinel.TeamChat("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_WATER) + ".000/" + GSTown.GetCargoGoal(townid, GSCargo.TE_WATER) + ".000 liters of Water (Still Required)", companystats);
					}
					else
					{
					Sentinel.TeamChat("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_WATER) + ".000/" + GSTown.GetCargoGoal(townid, GSCargo.TE_WATER) + ".000 liters of Water (Delivered)", companystats);
					}
				}
				if (GSTown.GetCargoGoal(townid, GSCargo.TE_GOODS) != 0) {
					if (GSTown.GetLastMonthReceived(townid, GSCargo.TE_GOODS) <= GSTown.GetCargoGoal(townid, GSCargo.TE_GOODS)) {
					Sentinel.TeamChat("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_GOODS) + "/" + GSTown.GetCargoGoal(townid, GSCargo.TE_GOODS) + " crates of Goods (Still Required)", companystats);
					}
					else
					{
					Sentinel.TeamChat("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_GOODS) + "/" + GSTown.GetCargoGoal(townid, GSCargo.TE_GOODS) + " crates of Goods (Delivered)", companystats);
					}
				}
				if (GSTown.GetCargoGoal(townid, GSCargo.TE_FOOD) != 0) {
					if (GSTown.GetLastMonthReceived(townid, GSCargo.TE_FOOD) <= GSTown.GetCargoGoal(townid, GSCargo.TE_FOOD)) {
					Sentinel.TeamChat("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_FOOD) + "/" + GSTown.GetCargoGoal(townid, GSCargo.TE_FOOD) + " tonnes of Food (Still Required)", companystats);
					}
					else
					{
					Sentinel.TeamChat("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_FOOD) + "/" + GSTown.GetCargoGoal(townid, GSCargo.TE_FOOD) + " tonnes of Food (Delivered)", companystats);
					}
				}
			}
		}
		else
		{
		Sentinel.TeamChat("You didn't claim a (suitable) town yet. No statistics available!", companystats);
		}
	}
	else
	{
	Sentinel.TeamChat("The Company you specified doesn't exist!", companystats);
	}
}

function CityBuilder::SendStatisticsIRC(companystats)
{
	if (claimed_towns.HasItem(companystats))
	{
		if (GSTown.IsValidTown(claimed_towns.GetValue(companystats)))
		{
			local townid = claimed_towns.GetValue(companystats);
			local companyname = GSCompany.GetName(companystats);
			local townname = GSTown.GetName(townid);
			local inhabitants = GSTown.GetPopulation(townid);
			local houses = GSTown.GetHouseCount(townid);
			
			if (populations.HasItem(companystats))
			{
				Sentinel.IrcPublicMessage("Company: " + companyname);
				Sentinel.IrcPublicMessage(" ");
				Sentinel.IrcPublicMessage("-= Town Info =-");
				Sentinel.IrcPublicMessage("Town Name: " + townname + "");
				Sentinel.IrcPublicMessage("Inhabitants: " + inhabitants + "");
				Sentinel.IrcPublicMessage("No. of Houses: " + houses + "");
				Sentinel.IrcPublicMessage(" ");
				Sentinel.IrcPublicMessage("-= Cargo Information =-");
				if (GSTown.GetCargoGoal(townid, GSCargo.TE_PASSENGERS) != 0) {
					if (GSTown.GetLastMonthReceived(townid, GSCargo.TE_PASSENGERS) <= GSTown.GetCargoGoal(townid, GSCargo.TE_PASSENGERS)) {
					Sentinel.IrcPublicMessage("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_PASSENGERS) + "/" + GSTown.GetCargoGoal(townid, GSCargo.TE_PASSENGERS) + " Passengers (Still Required)");
					}
					else
					{
					Sentinel.IrcPublicMessage("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_PASSENGERS) + "/" + GSTown.GetCargoGoal(townid, GSCargo.TE_PASSENGERS) + " Passengers (Delivered)");
					}
				}
				if (GSTown.GetCargoGoal(townid, GSCargo.TE_MAIL) != 0) {
					if (GSTown.GetLastMonthReceived(townid, GSCargo.TE_MAIL) <= GSTown.GetCargoGoal(townid, GSCargo.TE_MAIL)) {
					Sentinel.IrcPublicMessage("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_MAIL) + "/" + GSTown.GetCargoGoal(townid, GSCargo.TE_MAIL) + " bags of Mail (Still Required)");
					}
					else
					{
					Sentinel.IrcPublicMessage("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_MAIL) + "/" + GSTown.GetCargoGoal(townid, GSCargo.TE_MAIL) + " bags of Mail (Delivered)");
					}
				}
				if (GSTown.GetCargoGoal(townid, GSCargo.TE_WATER) != 0) {
					if (GSTown.GetLastMonthReceived(townid, GSCargo.TE_WATER) <= GSTown.GetCargoGoal(townid, GSCargo.TE_WATER)) {
					Sentinel.IrcPublicMessage("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_WATER) + ".000/" + GSTown.GetCargoGoal(townid, GSCargo.TE_WATER) + ".000 liters of Water (Still Required)");
					}
					else
					{
					Sentinel.IrcPublicMessage("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_WATER) + ".000/" + GSTown.GetCargoGoal(townid, GSCargo.TE_WATER) + ".000 liters of Water (Delivered)");
					}
				}
				if (GSTown.GetCargoGoal(townid, GSCargo.TE_GOODS) != 0) {
					if (GSTown.GetLastMonthReceived(townid, GSCargo.TE_GOODS) <= GSTown.GetCargoGoal(townid, GSCargo.TE_GOODS)) {
					Sentinel.IrcPublicMessage("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_GOODS) + "/" + GSTown.GetCargoGoal(townid, GSCargo.TE_GOODS) + " crates of Goods (Still Required)");
					}
					else
					{
					Sentinel.IrcPublicMessage("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_GOODS) + "/" + GSTown.GetCargoGoal(townid, GSCargo.TE_GOODS) + " crates of Goods (Delivered)");
					}
				}
				if (GSTown.GetCargoGoal(townid, GSCargo.TE_FOOD) != 0) {
					if (GSTown.GetLastMonthReceived(townid, GSCargo.TE_FOOD) <= GSTown.GetCargoGoal(townid, GSCargo.TE_FOOD)) {
					Sentinel.IrcPublicMessage("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_FOOD) + "/" + GSTown.GetCargoGoal(townid, GSCargo.TE_FOOD) + " tonnes of Food (Still Required)");
					}
					else
					{
					Sentinel.IrcPublicMessage("" + GSTown.GetLastMonthReceived(townid, GSCargo.TE_FOOD) + "/" + GSTown.GetCargoGoal(townid, GSCargo.TE_FOOD) + " tonnes of Food (Delivered)");
					}
				}
			}
		}
		else
		{
		Sentinel.IrcPublicMessage("The Company you specified didn't claim a (suitable) town yet. No statistics available!");
		}
	}
	else
	{
	Sentinel.IrcPublicMessage("The Company you specified doesn't exist!");
	}
}*/

function CityBuilder::CheckTown(mycompany, mytown)
{
	// Checks if the town is a City and returns CITY
	if (GSTown.IsCity(mytown)) {
		return "CITY";
	}
	for (local c = GSCompany.COMPANY_FIRST; c <= GSCompany.COMPANY_LAST; c++)
	{
		if(GSCompany.ResolveCompanyID(c) != GSCompany.COMPANY_INVALID)
		{
			// Checks if another company already claimed the town and returns OWNED 
			if (GSTile.GetClosestTown(GSCompany.GetCompanyHQ(GSCompany.ResolveCompanyID(c))) == mytown && GSCompany.ResolveCompanyID(c) != mycompany)
				return "OWNED";
		}
	}
	return false;
}

function CityBuilder::BuildSign(tileIndex, text)
{
	local signid = GSSign.BuildSign(tileIndex, text);
	if (GSSign.IsValidSign(signid))
		signlist.AddItem(signid, tileIndex);
}

function CityBuilder::RemoveSign(tileIndex)
{
	local removedsigns = 0;
	foreach (signid, signtile in signlist)
	{
		if (signtile == tileIndex)
		{
			signlist.RemoveItem(signid);
			GSSign.RemoveSign(signid);
			removedsigns++;
		}
	}
	return removedsigns;
}

/* story page */
function CityBuilder::StoryStart(){
	this.story.append(GSStoryPage.New(GSCompany.COMPANY_INVALID, GSText(GSText.STR_STORY_TITLE))); //id0, yearly progress

	this.story.append(GSStoryPage.New(GSCompany.COMPANY_INVALID, GSText(GSText.STR_STORY_TITLE_REQ))); //id 1, cargo requirements

  //local max_claim = 500; // to change if a GS variable is added ---- currently using "maxpopulation" defined at Class
  //local game_goal = 8000; // NOT used, but to change if a GS variable is added
  //GSStoryPage.NewElement(this.story[0],	GSStoryPage.SPET_TEXT, 0,	GSText(GSText.STR_GOAL_START));
  GSStoryPage.NewElement(this.story[0],	GSStoryPage.SPET_TEXT, 0,	GSText(GSText.STR_GOAL_START_CITYBUILDER, maxpopulation));


  // Factors
  // - Difficulty:
  local difficulty = GSController.GetSetting("rtd.congestion.difficulty");
  local factor = ( 1 + difficulty ) * 0.25;




  //local d_factor = Town.cache.Get(CACHE_CARGOGOAL_DIFFICULTY_FACTOR);
  //local population = GSTown.GetPopulation(this.id);  // no idea how to get this info :S

  // Combined Factor
  //local factor = d_factor;
  //if ((factor == lastfactor) && (population == lastpopulation))
    //return;
  //lastfactor = factor;

  // Set start demands pop
  local minPassenger = 5;
  local minMail = 20;
  local minWater = 1000;
  local minFood = 500;
  local minGoods = 1500;

  // Sets the divider
  local divPassenger = 5;
  local divMail = 20;
  local divWater = 10;
  local divFood = 10;
  local divGoods = 10;

  // Compute Goals
  //local reqPassenger = (population / 5) * factor;
  //local reqMail = (population / 20) * factor;
  //local reqWater = population > 1000 ? (population / 10) * factor : 0;			// Water
  //local reqFood = population > 500 ? (population / 10) * factor : 0;		// Food
  //local reqGoods = population > 1500 ? (population / 10) * factor : 0;	// Goods


  GSStoryPage.NewElement(this.story[1],	GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CLAIMED_RES)); // KEEP this


  // Add locals to read settings, if available, to get wich cargos are needed and amount
  // to be used below. Now some values are hardcoded
  // the below GSStoryPage.NewElement lines, check the STR used.
  // Some are commented to show test examples

  local tmp_val = 0;

  if (GSController.GetSetting("rtd.cargogoal.compatibility") == 1)
		{
			// Show amounts wanted/needed and population when it starts the demand
			// ( With FIRS we dont need to adjust for different Landscapes )
			
			tmp_val = (1000 / divPassenger) * factor;
      GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 0, minPassenger.tointeger()));
      tmp_val = (1000 / divMail) * factor;
      GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 2, minMail.tointeger()));
      tmp_val = (1000 / divFood) * factor;
      GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 11, minFood.tointeger()));
      tmp_val = (1000 / divWater) * factor;
      GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 9, minWater.tointeger()));
      tmp_val = (1000 / divGoods) * factor;
      GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 5, minGoods.tointeger()));
		}
		else
		{
			switch (GSGame.GetLandscape()) {
				case GSGame.LT_TEMPERATE:
          tmp_val = (1000 / divPassenger) * factor;
          GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 0, minPassenger.tointeger()));
          tmp_val = (1000 / divMail) * factor;
          GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 2, minMail.tointeger()));
          tmp_val = (1000 / divGoods) * factor;
          GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 5, minGoods.tointeger()));
					break;

        case GSGame.LT_ARCTIC:
          tmp_val = (1000 / divPassenger) * factor;
          GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 0, minPassenger.tointeger()));
          tmp_val = (1000 / divMail) * factor;
          GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 2, minMail.tointeger()));
          tmp_val = (1000 / divFood) * factor;
          GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 11, minFood.tointeger()));
          tmp_val = (1000 / divGoods) * factor;
          GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 5, minGoods.tointeger()));
					break;

				case GSGame.LT_TROPIC:
					tmp_val = (1000 / divPassenger) * factor;
          GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 0, minPassenger.tointeger()));
          tmp_val = (1000 / divMail) * factor;
          GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 2, minMail.tointeger()));
          tmp_val = (1000 / divFood) * factor;
          GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 11, minFood.tointeger()));
          tmp_val = (1000 / divWater) * factor;
          GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 9, minWater.tointeger()));
          tmp_val = (1000 / divGoods) * factor;
          GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 5, minGoods.tointeger()));
					break;

				case GSGame.LT_TOYLAND:
          tmp_val = (1000 / divPassenger) * factor;
          GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 0, minPassenger.tointeger()));
          tmp_val = ((1000 / divMail) * factor) / 2;
          GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 2, minMail.tointeger()));
          // Toyland is weird, minFood and minGoods are exchanged (testing) - have attention on this
          tmp_val = (1000 / divFood) * factor;
          GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 11, minGoods.tointeger()));
          tmp_val = (1000 / divGoods) * factor;
          GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_TOWN_CARGOS_NEEDED_CB_B, tmp_val.tointeger(), 1 << 5, minFood.tointeger()));
					break;
			}
		}
		local tmz = 0;
		this.story.append(GSStoryPage.New(GSCompany.COMPANY_INVALID, GSText(GSText.STR_STORY_TITLE_LIM)));

    GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIM_TITLE));
    tmz = GSGameSettings.GetValue("game_creation.starting_year");
    GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIM_YEAR, tmz));
    tmz = GSGameSettings.GetValue("difficulty.max_loan");
    GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIM_LOAN, tmz));
    tmz = GSGameSettings.GetValue("vehicle.max_trains");
    GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIM_TRAINS, tmz));
    tmz = GSGameSettings.GetValue("vehicle.max_roadveh");
    GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIM_RVS, tmz));
    tmz = GSGameSettings.GetValue("vehicle.max_aircraft");
    GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIM_PLANES, tmz));
    tmz = GSGameSettings.GetValue("vehicle.max_ships");
    GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIM_SHIPS, tmz));
    tmz = GSGameSettings.GetValue("station.station_spread");
    GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIM_ST, tmz));

    GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_TITLE));
  if (GSController.GetSetting("shouldLimitations") == 1) {
      if (GSController.GetSetting("shouldRailDeposMore") == 0) {
        tmz = GSController.GetSetting("shouldRailDeposNum");
        GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_RAILDEPO, tmz));
      }
      if (GSController.GetSetting("shouldRoadDeposMore") == 0) {
        tmz = GSController.GetSetting("shouldRoadDeposNum");
        GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_ROADDEPO, tmz));
      }
      if (GSController.GetSetting("shouldWaterDeposMore") == 0) {
        tmz = GSController.GetSetting("shouldWaterDeposNum");
        GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_WATERDEPO, tmz));
      }
      if (GSController.GetSetting("shouldRailStationsMore") == 0) {
        tmz = GSController.GetSetting("shouldRailStationsNum");
        GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_RAILSTATIONS, tmz));
      }
      if (GSController.GetSetting("shouldTruckStopsMore") == 0) {
        tmz = GSController.GetSetting("shouldTruckStopsNum");
        GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_TRUCKSTATIONS, tmz));
      }
      if (GSController.GetSetting("shouldBusStopsMore") == 0) {
        tmz = GSController.GetSetting("shouldBusStopsNum");
        GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_BUSSTATIONS, tmz));
      }
      if (GSController.GetSetting("shouldWaterDocksMore") == 0) {
        tmz = GSController.GetSetting("shouldWaterDocksNum");
        GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_WATERDOCKS, tmz));
      }
      if (GSController.GetSetting("shouldAirPortsMore") == 0) {
        tmz = GSController.GetSetting("shouldAirPortsNum");
        GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_AIRPORTS, tmz));
      }
      if (GSController.GetSetting("shouldTruckVehiclesMore") == 0) {
        tmz = GSController.GetSetting("shouldTruckVehiclesNum");
        GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_TRUCKS, tmz));
      }
      if (GSController.GetSetting("shouldBusVehiclesMore") == 0) {
        tmz = GSController.GetSetting("shouldBusVehiclesNum");
        GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_BUSSES, tmz));
      }
    } else {
      GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_DIS));
    }
    GSStoryPage.NewElement(this.story[2], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_RULES));
}

function CityBuilder::SendAdmin(message)
{
	if (GSAdmin.Send(message))
	{
		// GSLog.Info("Admin send OK");
	}
	else
	{
		GSLog.Error("Error sending to admin interface!");
	}
}
