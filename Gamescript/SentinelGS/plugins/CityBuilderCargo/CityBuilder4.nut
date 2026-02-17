require("version.nut");

require("RTDCache.nut");

/*
 CityBuilder by Knogle & Frank & Chucky
 ST2 added/modified: still looks weird that cargo values are sent as population (populationupdated) to plugins :S (modified now)
 - more cargo types: can be defined in the arrays. attention to number of cargos, because of :: local tmpcargo = GSBase.RandRange(12);
 - previous addition includes fund needed industry (if any) close claimed town (if possible and town dnt already have one of the kind)
 - can run in 4 climates (cb3.divcargo, set in openttd.cfg file) to support the possibility on BTPro random climates 
 - changed the way goal is set (cb3.cargogoal). now the cargo value is set in openttd.cfg
 - if cb3.divcargo is set to 0 (zero), no random. that means server will have fixed cargo, set in cb3.cargo
 - replaced "populationupdated" to "multigoalsupdated" in some SendAdmin's - Kept some "populationupdated" in SendPopulation (after all, towns are claimable)
 - That is a Cargo server is specified with SendAdmin( { event = "goaltypeinfo", goalmastergame = 0 } );     (main.nut)
 
 This script is inspired by, and/or may include parts from other scripts
  "Minimal GS" by Zuu
  "Neighbours are important" by Zuu
  "Realistic Town Dependencies" by Fanatik
  "Simple City Builder" by The_Dude
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
/* mapgen methods */
RANDOM <- 1;
SQUARE <- 2;
/* stop growing */ 

class CityBuilder
{
		_load_data = null;
		populations = null;
		claimed_towns = null;
		companyStartDate = null;
		signlist = null;
		sign = null;
		oldsign = null;
		whenwas = null;
		whenwas_last = 0;
		fromLoad = false;
		last_date = 0;
		fromSavegame = false;
		cache = RTDCache();
		maxpopulation = 800;
		protectionrange = 20;
		protectionsigns = false;
		_mapX = 0;
		_mapY = 0;
		pageid=0;
		
		CargoAmount=null;
		Goaltime=null;
		Page_id=null;
		TemperateCargos=null;
		ArcticCargos=null;
		DesertCargos=null;
		ToylandCargos=null;
		
		cargo=1;
		cargogoal=1;
		goaltime=0;
		goaldiv=0;
	
		page_id=0;
    //goaldiv = GSController.GetSetting("cb3.divcargo");
	
		constructor() {
			populations = GSList();
			companyStartDate = GSList();
			signlist = GSList();
			claimed_towns = GSList();

			CargoAmount = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
			Goaltime = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
			Page_id = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
			
			//acceptable cargo types arrays, by climate type - ORIGINAL SET
      //TemperateCargos = [0,1,2,3,4,5,6,7,8,9,0,0];
      //ArcticCargos =    [0,0,2,3,4,5,6,7,0,9,10,11];
      //DesertCargos =    [0,1,2,3,4,5,6,0,8,9,10,11];
      
			//acceptable cargo types arrays, by climate type
      TemperateCargos = [0,1,2,4,5,6,7,8,9,0,1,7];
      ArcticCargos =    [0,1,2,4,5,6,7,9,10,11,0,1];
      DesertCargos =    [0,2,4,5,6,9,10,11,0,9,10,11];
      ToylandCargos =   [0,1,2,3,4,5,6,7,8,9,10,11];
      
			// original place of GetSettings
			//cargo = GSController.GetSetting("cb3.cargo");
      cargogoal = GSController.GetSetting("cb3.cargogoal");
      goaltime = GSController.GetSetting("cb3.goaltime");
      //goaldiv = GSController.GetSetting("cb3.divcargo");
		}	
		story = []; //storypage ids
		function CreateTownList();
		function Storybook();
		function SendPopulation();
		function Tutorial();
		function SendGoalInfo();
	
}

function CityBuilder::GetName()			{ return "CityBuilder v3.141011"; }

function CityBuilder::SendGoalInfo()
{
  //local landi = GSGame.GetLandscape();
  local cargoG = GSController.GetSetting("cb3.cargogoal");

  //local textC = ("" + GSText(GSText.STR_UNIT_INFO2, cargo) + " delivered");
  //local textC = GSText(GSText.STR_UNIT_INFO2, cargo);
  //local textC = ("" + GSCargo.GetCargoLabel(cargo) + "");  // only with 4 characters (Cargo Label), but works - test
  local textC = GSCargo.GetCargoLabel(cargo);  // only with 4 characters (Cargo Label), but works

  local unitMessage = { event = "goalunitinfo", goalunitvaluetext = "a transported amount of", goalunitname = textC, goalunitnameplural = textC };

  //SendAdmin( { event = "goalunitinfo", goalunitvaluetext = "a transported amount of", goalunitname = textC, goalunitnameplural = textC } );
  SendAdmin(unitMessage);

	SendAdmin( { event = "goaltimewindow", goaltimewindow = goaltime } );
}

// Start function, this is where it all begins
function CityBuilder::Initialize()
{
  //cargo = GSController.GetSetting("cb3.cargo");
	//cargogoal = GSController.GetSetting("cb3.cargogoal");
	//goaltime = GSController.GetSetting("cb3.goaltime");
	goaldiv = GSController.GetSetting("cb3.divcargo");
	//local landi = GSGame.GetLandscape();
	
	if (goaldiv == 1) {
    local tmpcargo = GSBase.RandRange(12);
    if (GSGame.GetLandscape() == 0)
      cargo = TemperateCargos[tmpcargo];
    else if (GSGame.GetLandscape() == 1)
      cargo = ArcticCargos[tmpcargo];
    else if (GSGame.GetLandscape() == 2)
      cargo = DesertCargos[tmpcargo];
    else if (GSGame.GetLandscape() == 3)
      cargo = ToylandCargos[tmpcargo];
	} else if (goaldiv == 0) {
    cargo = GSController.GetSetting("cb3.cargo");
	}
	Sentinel.IrcPublicMessage("Cargo Chosen: " + cargo + ". Climate: " + GSGame.GetLandscape());	
	//this.SendGoalInfo();
	this.Storybook();

	Sentinel.InfoMessage("[CityBuilder] CityBuilder v3 (Cargo) is being started...");

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
	
	foreach(townid, _ in all_towns)
	{
		
		
		if (GSController.GetTick() > (lastdisplaytick + 100)) // show a status update roughly every 3 seconds
		{
			lastdisplaytick = GSController.GetTick();
			local percentage = ((currenttown * 100) / towncount);
			Sentinel.InfoMessage("[CityBuilder] (" + percentage + "%) Initializing town data...");
		}
		
		
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
	this.SendGoalInfo();  //New location?!

  //this.Process();
  /*while (true) {
    this.SendGoalInfo();  // to report Sentinel text to show, each second, to keep plugins tunned with it
    // Determine delta Ticks since last Call
    local date = GSDate.GetCurrentDate();
    local delta = date - this.last_date;
    this.last_date = date;

    // Stop, if already fired once this tick.
    if (delta == 0) return;

    // Resync Cache
    this.cache.SyncOnDemand(delta);
    
    CheckCargo();
    CheckMap();
    
    GSController.Sleep(31); // 31 ticks are about 1 second
	}*/
}




		//Industry info:
		//this.PlaceIndustry(0x01 , 0x01, 8, 10, RANDOM);//Power Plant
		//this.PlaceIndustry(0x02 , 0x07, 8, 10, RANDOM);//Saw Mill
		//this.PlaceIndustry(0x04 , 0x09, 10, 25, RANDOM);//Oil Refinery?
		//this.PlaceIndustry(0x05 , 0x09, 10, 25, RANDOM);//Oil Rig
		//this.PlaceIndustry(0x06 , 0x06, 8, 10, RANDOM);//Factory
		//this.PlaceIndustry(0x08 , 0x09, 8, 10, RANDOM);//Steel Mill
		//this.PlaceIndustry(0x0D , 0x09, 8, 10, RANDOM);//Food Factory
		//this.PlaceIndustry(0x09 , 0x09, 10, 25, RANDOM);//Farm
        //this.PlaceIndustry(0x12 , 0x09, 10, 25, RANDOM);//Iron Ore Mine
        //this.PlaceIndustry(0x0B , 0x09, 10, 25, RANDOM);//Oil Wells
		//this.PlaceIndustry(0x0C , 0x09, 10, 25, RANDOM);//Bank
		//this.PlaceIndustry(0x16 , 0x09, 1, 5, RANDOM);//Water Tower
		//this.PlaceIndustry(0x0E , 0x07, 6, 14, RANDOM,town_id);//Paper Mill
		//this.PlaceIndustry(0x07 , 0x09, 6, 14, RANDOM,town_id);//Printing Works

//PlaceIndustry from the_dude
function CityBuilder::PlaceIndustry(ind, cargo, distmin, distmax, method, town_id){
    //local xtownlist = GSList();
	local txy, tx, rx, ry, ty, rtile, n, success, built = 0, skip = 0, towncount = 0, ntotal = 0, isCity;
	local tile_area = [], xtile_area = [], rand;
  

	GSCompanyMode(GSCompany.COMPANY_INVALID); //since 1.3.0 we can use GAIA company

	if(method == SQUARE){
		for(local i = -distmax; i <= distmax; i++){
			for(local j = -distmax; j <= distmax; j++){
			  if(abs(i) + abs(j) < distmin) continue;
				tile_area.append([i, j]);
			}
		}
	}
	
	success = false;
	txy = GSTown.GetLocation(town_id);
	tx = GSMap.GetTileX(txy);
	ty = GSMap.GetTileY(txy);
	n = 0;
		
	DebugMessage("Mapgen try to build industry in " + GSTown.GetName(town_id));
    
	
	if(method == RANDOM){
		while(success != true && n < 127){
			rx = GSBase.RandRange(distmax * 2 + 1) - distmax;
			ry = GSBase.RandRange(2 * (distmax - abs(rx)) + 1) - (distmax - abs(rx));
			if(abs(rx) + abs(ry) < distmin) continue;
			rtile = GSMap.GetTileIndex(tx + rx, ty + ry);
			if(!GSMap.IsValidTile(rtile) || GSRoad.IsRoadTile(rtile)) continue;

			success = GSIndustryType.BuildIndustry(ind, rtile);
			if(success){
				built++;
			}
			n++;
		}
	}
	else if(method == SQUARE){
		xtile_area = clone tile_area;
		//seek through square
		for(local i = 0, size = xtile_area.len(); i < size; i++){
			rand = GSBase.RandRange(size - i);
			rx = tile_area[rand][0];
			ry = tile_area[rand][1];
			rtile = GSMap.GetTileIndex(tx + rx, ty + ry);
			xtile_area.remove(rand);

			if(!GSMap.IsValidTile(rtile) || GSRoad.IsRoadTile(rtile)) continue;
			success = GSIndustryType.BuildIndustry(ind, rtile);
			if(success){
				built++;
				break;
			}
			n++;
		}
	}
		
	DebugMessage("Mapgen has built " + built + " " + GSIndustryType.GetName(ind));
}


function CityBuilder::Process()
{
  this.SendGoalInfo();  // to report Sentinel text to show, each second, to keep plugins tunned with it
	// Determine delta Ticks since last Call
	local date = GSDate.GetCurrentDate();
	local delta = date - this.last_date;
	this.last_date = date;

	// Stop, if already fired once this tick.
	if (delta == 0) return;

	// Resync Cache
	this.cache.SyncOnDemand(delta);
	
	CheckCargo();
	CheckMap();
	
  //GSController.Sleep(31); // 31 ticks are about 1 second
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
		local log = GSController.GetSetting("log_level");
    	if ((log==2)||(log==3)) Sentinel.DebugMessage(message);
		if (log==3) Sentinel.IrcPublicMessage("DEBUG: " + message);
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
		
		local cargoG = GSController.GetSetting("cb3.cargogoal");
    GSGoal.Question(2, newcompany.GetCompanyID(), GSText(GSText.STR_CITYBUILDER_I_START_CB_CARGO, cargo, cargoG), GSGoal.QT_INFORMATION, GSGoal.BUTTON_GO);
    
		//Sentinel.TeamChat("-=[ Build your HQ in a town to claim it for game goal ]=-", newcompany.GetCompanyID());
		Sentinel.TeamChat("-=[ Build your HQ in a town to claim it for game goal ]=-", newcompany.GetCompanyID());
		claimed_towns.AddItem(newcompany.GetCompanyID(), CLAIM_NOT_CLAIMED);
		companyStartDate.AddItem(newcompany.GetCompanyID(), GSDate.GetCurrentDate());
		
		//create storybook
	    //this.Storybook(newcompany.GetCompanyID());
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
		//reset amount
		CargoAmount[company_id]=0;
	
	}
	// ### MERGE COMPANY ###
	if (eventType == GSEvent.ET_COMPANY_MERGER)
	{
		DebugMessage("Merge event detected");
		local merge = GSEventCompanyMerger.Convert(event);
		local oldcompanyid = merge.GetOldCompanyID();
		GSLog.Info("Caught company merge of company " + oldcompanyid + " into " + GSCompany.GetName(merge.GetNewCompanyID()));
		// Log the event to Sentinel
		DebugMessage("Caught company merge of company " + oldcompanyid + " into " + GSCompany.GetName(merge.GetNewCompanyID()));
		// Done Logging the event to Sentinel
		DebugMessage("Company has item in population:"+(populations.HasItem(oldcompanyid)));
		if (populations.HasItem(oldcompanyid))
			populations.RemoveItem(oldcompanyid);
			DebugMessage("Populations Item Removed");
		
		DebugMessage("Company has item in claimed towns:"+(claimed_towns.HasItem(oldcompanyid)));
		if (claimed_towns.HasItem(oldcompanyid))
		{
			if (GSTown.IsValidTown(claimed_towns.GetValue(oldcompanyid)))
			{
				local townlocation = GSTown.GetLocation(claimed_towns.GetValue(oldcompanyid));
				RemoveSign(townlocation);
				DebugMessage("Sign Removed");
				RemoveProtectionSigns(townlocation);
				DebugMessage("Protection signs Removed");
				SendAdmin( { event = "citybuilder", action = "unclaimed", company = oldcompanyid } );  //new location for this SendAdmin
			}
			claimed_towns.RemoveItem(oldcompanyid);
			DebugMessage("Claimed_towns item Removed");
			//SendAdmin( { event = "citybuilder", action = "unclaimed", company = oldcompanyid } );  //old location for this SendAdmin
			companyStartDate.RemoveItem(oldcompanyid);
			DebugMessage("CompanyStartDate item Removed");
		}
		//reset amount
		CargoAmount[oldcompanyid]=0;

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
		if (lasttown == GSTile.GetClosestTown(company_hq)) {
			return; // HQ was moved within the same town area, don't do anything
		} else {
      GSTown.SetText(lasttown, GSText(GSText.STR_EMPTY0)); // HQ was moved to another town area, clear text on the old town
		}
		DebugMessage(GSCompany.GetName(company_id) + " moved his HQ from " + GSTown.GetName(lasttown) + " to " + GSTown.GetName(GSTile.GetClosestTown(company_hq)));
		RemoveSign(townlocation);
		RemoveProtectionSigns(townlocation);
		claimed_towns.SetValue(company_id, CLAIM_NOT_CLAIMED);
	}
	
	// nothing more to do if no HQ is placed
	if (company_hq == GSMap.TILE_INVALID) return;
	
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
		//open story page
		//GSStoryPage.Show(company_id);
		DebugMessage(companyname + " claimed " + townname);
		Sentinel.ServerChat(companyname + " claimed " + townname);
		// CORAGEM //SendAdmin( { event = "citybuilder", action = "claimed", company = company_id, town = townname, population = (CargoAmount[company_id]), x = GSMap.GetTileX(GSTown.GetLocation(closesttown)), y = GSMap.GetTileY(GSTown.GetLocation(closesttown)) } );
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
	
	//DebugMessage("Checking Map");	
	foreach (company_id, town_id in claimed_towns)
	{   		
		if (whenwas > whenwas_last)
		{	
			switch (town_id)
			{
				case CLAIM_NOT_CLAIMED:
					GSLog.Info("Place your HQ");
					Sentinel.TeamChat("-=[ Build your HQ in a town to claim it for game goal ]=-", company_id);
					//show storybook if time elapsed
					if (whenwas - GSDate.GetMonth(companyStartDate.GetValue(company_id))>1) this.Tutorial(company_id);
					break;
				case CLAIM_TOO_BIG:
					Sentinel.TeamChat("Only towns smaller than " + maxpopulation + " can be claimed -- Please move your HQ to a smaller TOWN to participate in the game!", company_id);
					//show storybook if time elapsed
					if (whenwas - GSDate.GetMonth(companyStartDate.GetValue(company_id))>1) this.Tutorial(company_id);
					break;
				case CLAIM_CITY:
					Sentinel.TeamChat("You built your HQ in a CITY, which can't be claimed -- Please move your HQ to a TOWN to participate in the game!", company_id);
					//show storybook if time elapsed
					if (whenwas - GSDate.GetMonth(companyStartDate.GetValue(company_id))>1) this.Tutorial(company_id);
					break;
				case CLAIM_OWNED:
					Sentinel.TeamChat("You built your HQ in a town already claimed by someone else, please move it to participate in the game!", company_id);
					//show storybook if time elapsed
					if (whenwas - GSDate.GetMonth(companyStartDate.GetValue(company_id))>1) this.Tutorial(company_id);
					break;
				case CLAIM_OVERLAP:
					Sentinel.TeamChat("Your protected area would overlap with the area of someone else, you cannot claim this town, please relocate your HQ!", company_id);
					//show storybook if time elapsed
					if (whenwas - GSDate.GetMonth(companyStartDate.GetValue(company_id))>1) this.Tutorial(company_id);
					break;
			}
		}
		if (town_id >= 0)
		{
			//local inhabitants = GSTown.GetPopulation(town_id);
			local inhabitants = CargoAmount[company_id];
			if (populations.HasItem(company_id))
			{
				if (populations.GetValue(company_id) != inhabitants)
				{
					populations.SetValue(company_id, inhabitants);
					local cargoMessage = { event = "multigoalsupdated", company = company_id, cargo = inhabitants };
					//local populationMessage = { event = "populationupdated", company = company_id, population = inhabitants };
					//+1 geändert CORAGEM
					//local populationMessage = { event = "populationupdated", company = company_id+1, population = inhabitants, companyage = GSDate.GetCurrentDate() - companyStartDate.GetValue(company_id) };
					SendAdmin(cargoMessage);
				}
			}
			else
			{
				populations.AddItem(company_id, inhabitants);
				local cargoMessage = { event = "multigoalsupdated", company = company_id, cargo = inhabitants };
				//local populationMessage = { event = "populationupdated", company = company_id, population = inhabitants };
				//+1 geändert  CORAGEM
				//local populationMessage = { event = "populationupdated", company = company_id+1, population = inhabitants, companyage = GSDate.GetCurrentDate() - companyStartDate.GetValue(company_id) };
				SendAdmin(cargoMessage);
			}
		}
		else if ((populations.HasItem(company_id)) && (populations.GetValue(company_id) > 0))
		{
			populations.SetValue(company_id, -1);
			cargoMessage = { event = "multigoalsupdated", company = company_id, cargo = -1 };
			//local populationMessage = { event = "populationupdated", company = company_id, population = -1 };
			//+1 geändert CORAGEM
			//local populationMessage = { event = "populationupdated", company = company_id+1, population = -1, companyage = GSDate.GetCurrentDate() - companyStartDate.GetValue(company_id) };
			SendAdmin(cargoMessage);			
		}
	}
	whenwas_last = whenwas;
}


function CityBuilder::CheckCargo()
{
	local whenwas = GSDate.GetMonth(GSDate.GetCurrentDate());
	
	GSLog.Info("Checking Cargo");
	DebugMessage("Checking Cargo");
	
	
	//Get day of month
	local gameday=GSDate.GetDayOfMonth(GSDate.GetCurrentDate());

  // First, let's clear the table of demands for ALL companies!
	SendAdmin( { event = "citybuilder", action = "cleardemands" } );
	
	
	//read goal
	local goal=cargogoal;
	//Sentinel.IrcPublicMessage("Goal is: " + goal + "");	
	
	//send cargovalue to plugins  ## MOVED BELOW ##
	//if ((gameday==2) || (gameday==12) || (gameday==22)) SendPopulation();
	
	foreach (company_id, town_id in claimed_towns){

    // Send Town info
    SendAdmin( { event = "citybuilder", action = "townstats", company = company_id, townid = town_id, townname = GSTown.GetName(town_id), population = GSTown.GetPopulation(town_id), housecount = GSTown.GetHouseCount(town_id), growthrate = GSTown.GetGrowthRate(town_id), statue = GSTown.HasStatue(town_id), location = "" + GSMap.GetTileX(GSTown.GetLocation(town_id)) + "x" + GSMap.GetTileY(GSTown.GetLocation(town_id))} );

		local amount=GSCargoMonitor.GetTownDeliveryAmount(company_id, cargo, town_id, true);
		local amountbefore=CargoAmount[company_id];
		CargoAmount[company_id]=amount+amountbefore;
		if (CargoAmount[company_id]<0) CargoAmount[company_id]=0;
		local landi = GSGame.GetLandscape();

    //towngui
    if (goaltime>0) {
      GSTown.SetText(town_id,GSText(GSText.STR_TOWN4,(goaltime-Goaltime[company_id]),GSText(GSText.STR_TOWN_INFO,CargoAmount[company_id],cargo, goal)));
    } else {
      GSTown.SetText(town_id,GSText(GSText.STR_TOWN3,GSText(GSText.STR_TOWN_INFO,CargoAmount[company_id], cargo, goal)));
    }

    if (cargo==0) { // Passengers
      // nothing needed
    }

		if (cargo==1) { // Coal / Rubber / Sugar
      if ((landi == 0) || (landi == 1)) {
        //place a power plant next to claimed town
        this.PlaceIndustry(0x01 , 0x01, 6, 20, RANDOM,town_id);
      } else if (landi == 2) {
        //place a factory next to claimed town
        this.PlaceIndustry(0x17 , 0x01, 6, 25, RANDOM,town_id);
      } else if (landi == 3) {
        //place a sweet factory next to claimed town
        this.PlaceIndustry(0x1B , 0x01, 6, 25, RANDOM,town_id);
      }
		}
		if (cargo==2) { // Mail
			// nothing needed
		}
		if (cargo==3) { // Oil / Toys
      if ((landi == 0) || (landi == 1) || (landi == 2)) {
        //place oil refinery
        this.PlaceIndustry(0x04 , 0x03, 6, 25, RANDOM,town_id);
      } else if (landi == 3) {
        //place a toy shop next to claimed town
        this.PlaceIndustry(0x1E , 0x03, 6, 10, RANDOM,town_id);
      }
		}
		if (cargo==4) { // Livestock / Fruit / Batteries
      if (landi == 0) {
        //place a factory
        this.PlaceIndustry(0x06 , 0x04, 6, 20, RANDOM,town_id);
      } else if ((landi == 1) || (landi == 2)) {
        //place a food processing
        this.PlaceIndustry(0x0D , 0x04, 6, 20, RANDOM,town_id);
      } else if (landi == 3) {
        //place a toy factory
        this.PlaceIndustry(0x1F , 0x04, 6, 20, RANDOM,town_id);
      }
		}
		if (cargo==5) {  //Goods / Sweets
      // nothing needed
		}
		if (cargo==6) {  // Grain / Wheat / Maize / Toffee
      if (landi == 0) {
        //place a factory
        this.PlaceIndustry(0x06 , 0x06, 6, 20, RANDOM,town_id);
      } else if (landi == 1) {
        //place a food processing
        this.PlaceIndustry(0x0D , 0x06, 6, 20, RANDOM,town_id);
      } else if (landi == 2) {
        //place a food processing
        this.PlaceIndustry(0x0D , 0x06, 6, 20, RANDOM,town_id);
      } else if (landi == 3) {
        //place a sweet factory
        this.PlaceIndustry(0x1B , 0x06, 6, 20, RANDOM,town_id);
      }
		}
		if (cargo==7) {  // Wood / Cola
      if (landi == 0) {
        //place Sawmill
        this.PlaceIndustry(0x02 , 0x07, 6, 20, RANDOM,town_id);
      } else if (landi == 1) {
        //place Papermill
        this.PlaceIndustry(0x0E , 0x07, 6, 20, RANDOM,town_id);
      } else if (landi == 3) {
        //place a fizzy drink factory
        this.PlaceIndustry(0x21 , 0x07, 6, 20, RANDOM,town_id);
      }
		}
		if (cargo==8) { // Iron Ore / Copper Ore / Candyfloss
      if (landi == 0) {
        //place a Steelmill
        this.PlaceIndustry(0x08 , 0x08, 6, 20, RANDOM,town_id);
      } else if (landi == 2) {
        //place a factory
        this.PlaceIndustry(0x17 , 0x08, 6, 25, RANDOM,town_id);
      } else if (landi == 3) {
        //place a sweet factory
        this.PlaceIndustry(0x1B , 0x08, 6, 25, RANDOM,town_id);
      }
		}
		if (cargo==9) {  // Steel / Paper / Water / Bubbles
      if (landi == 0) {
        //place a factory
        this.PlaceIndustry(0x06 , 0x09, 6, 20, RANDOM,town_id);
      } else if (landi == 1) {
        //place a printing works
        this.PlaceIndustry(0x07 , 0x09, 6, 20, RANDOM,town_id);
      } else if (landi == 2) {
        //place a water tower
        this.PlaceIndustry(0x16 , 0x09, 2, 10, RANDOM,town_id);
      } else if (landi == 3) {
        //place a fizzy drinks factory
        this.PlaceIndustry(0x21 , 0x09, 6, 20, RANDOM,town_id);
      }
		}
		if (cargo==10) {  // Valuables / Gold / Diamonds / Plastic
      if (landi == 0) {
        //place a Bank
        this.PlaceIndustry(0x0C , 0x10, 2, 10, RANDOM,town_id);
      } else if (landi == 1) {
        //place a Bank
        this.PlaceIndustry(0x10 , 0x10, 2, 10, RANDOM,town_id);
      } else if (landi == 2) {
        //place a Bank
        this.PlaceIndustry(0x10 , 0x10, 2, 10, RANDOM,town_id);
      } else if (landi == 3) {
        //place a toy factory
        this.PlaceIndustry(0x1F , 0x10, 6, 20, RANDOM,town_id);
      }
		}
		if (cargo==11) {  // Food / Fizzy Drinks
      // nothing needed
		}
		
		//reset cargo amount if setting "goaltime" is more than 0 months
		if ((gameday==3) && (goaltime>0)) {
			Goaltime[company_id]++;
			if (Goaltime[company_id]==goaltime){
				Goaltime[company_id]=0;
				CargoAmount[company_id]=0;
			}
		
		}
					
	}
	//send cargovalue to plugins ## new location, after new cargos added
	if ((gameday==2) || (gameday==12) || (gameday==22)) SendPopulation();
}

/* OLD story page */
/*function CityBuilder::Storybook(company){
		
		//GSStoryPage.New(GSCompany.COMPANY_INVALID, (GSText(GSText.STR_STORY_HEAD,1))); 
		//GSStoryPage.NewElement(e,GSStoryPage.SPET_TEXT,0,GSText(GSText.STR_STORY_0));		
		
	Page_id[company] = GSStoryPage.New(company, GSText(GSText.STR_COMMUNITYURL));
	if (!GSStoryPage.IsValidStoryPage(Page_id[company])) {
		GSLog.Error("NewStoryPage: Failed to create page");
		return -1;
	}
	local pe = GSStoryPage.NewElement(Page_id[company],GSStoryPage.SPET_TEXT,0,GSText(GSText.STR_COMMUNITYURL));
	GSLog.Info("PE: " + pe);
	if (!GSStoryPage.IsValidStoryPageElement(pe)) {
			GSLog.Error("NewStoryPage: Failed to add element");
			GSStoryPage.Remove(Page_id[company]);
			return -1;
	}		
}*/

/* NEW story page */
function CityBuilder::Storybook() {
  local cargoG = GSController.GetSetting("cb3.cargogoal");
  local goalT = GSController.GetSetting("cb3.goaltime");
	this.story.append(GSStoryPage.New(GSCompany.COMPANY_INVALID, GSText(GSText.STR_STORY_CBC_TITLE))); //id0, yearly progress

  if(goalT > 0) {
    GSStoryPage.NewElement(this.story[0], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_CITYBUILDER_START_CB_CARGO, cargo, cargoG, goalT));
  } else {
    GSStoryPage.NewElement(this.story[0], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_CITYBUILDER_I_START_CB_CARGO, cargo, cargoG));
  }
  local tmz = 0;
  this.story.append(GSStoryPage.New(GSCompany.COMPANY_INVALID, GSText(GSText.STR_STORY_TITLE_LIM)));

  GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIM_TITLE));
  tmz = GSGameSettings.GetValue("game_creation.starting_year");
  GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIM_YEAR, tmz));
  tmz = GSGameSettings.GetValue("difficulty.max_loan");
  GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIM_LOAN, tmz));
  tmz = GSGameSettings.GetValue("vehicle.max_trains");
  GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIM_TRAINS, tmz));
  tmz = GSGameSettings.GetValue("vehicle.max_roadveh");
  GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIM_RVS, tmz));
  tmz = GSGameSettings.GetValue("vehicle.max_aircraft");
  GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIM_PLANES, tmz));
  tmz = GSGameSettings.GetValue("vehicle.max_ships");
  GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIM_SHIPS, tmz));
  tmz = GSGameSettings.GetValue("station.station_spread");
  GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIM_ST, tmz));

  GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_TITLE));
  if (GSController.GetSetting("shouldLimitations") == 1) {
    if (GSController.GetSetting("shouldRailDeposMore") == 0) {
      tmz = GSController.GetSetting("shouldRailDeposNum");
      GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_RAILDEPO, tmz));
    }
    if (GSController.GetSetting("shouldRoadDeposMore") == 0) {
      tmz = GSController.GetSetting("shouldRoadDeposNum");
      GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_ROADDEPO, tmz));
    }
    if (GSController.GetSetting("shouldWaterDeposMore") == 0) {
      tmz = GSController.GetSetting("shouldWaterDeposNum");
      GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_WATERDEPO, tmz));
    }
    if (GSController.GetSetting("shouldRailStationsMore") == 0) {
      tmz = GSController.GetSetting("shouldRailStationsNum");
      GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_RAILSTATIONS, tmz));
    }
    if (GSController.GetSetting("shouldTruckStopsMore") == 0) {
      tmz = GSController.GetSetting("shouldTruckStopsNum");
      GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_TRUCKSTATIONS, tmz));
    }
    if (GSController.GetSetting("shouldBusStopsMore") == 0) {
      tmz = GSController.GetSetting("shouldBusStopsNum");
      GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_BUSSTATIONS, tmz));
    }
    if (GSController.GetSetting("shouldWaterDocksMore") == 0) {
      tmz = GSController.GetSetting("shouldWaterDocksNum");
      GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_WATERDOCKS, tmz));
    }
    if (GSController.GetSetting("shouldAirPortsMore") == 0) {
      tmz = GSController.GetSetting("shouldAirPortsNum");
      GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_AIRPORTS, tmz));
    }
    if (GSController.GetSetting("shouldTruckVehiclesMore") == 0) {
      tmz = GSController.GetSetting("shouldTruckVehiclesNum");
      GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_TRUCKS, tmz));
    }
    if (GSController.GetSetting("shouldBusVehiclesMore") == 0) {
      tmz = GSController.GetSetting("shouldBusVehiclesNum");
      GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_BUSSES, tmz));
    }
  } else {
    GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_LIMS_DIS));
  }
  GSStoryPage.NewElement(this.story[1], GSStoryPage.SPET_TEXT, 0, GSText(GSText.STR_LIMITATIONS_RULES));
}

function CityBuilder::Tutorial(company){
	GSGoal.Question(company,company,GSText(GSText.STR_TUTORIAL), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
}



function CityBuilder::SendPopulation()
{
	GSLog.Info("Sending Population");
	foreach (company_id, townid in claimed_towns)
	{
		if (townid >= 0)
		{
			//send population
			local inhabitants = GSTown.GetPopulation(townid);
			local cargoP = CargoAmount[company_id];
			//local cargoP = populations.GetValue(company_id)  // to test later?!
			
			//send goalvalue instead of population
			//local inhabitants = CargoAmount[company_id];
			
			if (populations.HasItem(company_id))
			{ // CORAGEM
        local cargoMessage = { event = "multigoalsupdated", company = company_id, cargo = cargoP };
        SendAdmin(cargoMessage);
        local populationMessage = { event = "populationupdated", company = company_id, population = inhabitants };
				//local populationMessage = { event = "populationupdated", company = company_id+1, population = inhabitants, companyage = GSDate.GetCurrentDate() - companyStartDate.GetValue(company_id) };
				SendAdmin(populationMessage);
			}
		}
		else
		{ // CORAGEM
      local cargoMessage = { event = "multigoalsupdated", company = company_id, cargo = 0 };
      SendAdmin(cargoMessage);
			local populationMessage = { event = "populationupdated", company = company_id, population = -1 };
			//local populationMessage = { event = "populationupdated", company = company_id+1, population = 0, companyage = GSDate.GetCurrentDate() - companyStartDate.GetValue(company_id) };
			SendAdmin(populationMessage);
		}
	}
}

// Maybe SendAdmin's merged above
//function CityBuilder::SendDemands()

//not needed here?
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
} */

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
