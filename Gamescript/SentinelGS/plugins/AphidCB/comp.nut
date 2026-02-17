/*
 * This file is part of CityBuilder, which is a GameScript for OpenTTD
 *
 * CityBuilder is free software; you can redistribute it and/or modify it 
 * under the terms of the GNU General Public License as published by
 * the Free Software Foundation; version 2 of the License
 *
 * CityBuilder is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with CityBuilder; If not, see <http://www.gnu.org/licenses/> or
 * write to the Free Software Foundation, Inc., 51 Franklin Street, 
 * Fifth Floor, Boston, MA 02110-1301 USA.
 *
 */

 // Contributors:
 
require ("Towngrowth.nut");
require ("QSort.nut");

NEIGHBOUR_DISTANCE_MAX <- 2500; //50 tiles (square)
CLAIM_NOT_CLAIMED <- -1; // town not claimed

class Company{
towns = 0;
townAccess = 0;
claim_news = 0;
label_sign_id = -1;
label_sign_id_top = -1;
label_sign_id_bottom = -1;
label_sign_id_right = -1;
label_sign_id_left = -1;
num_towns = 1;
townsign = -1;
multiplier = GSController.GetSetting("mgrpct");
tzgt = [0,0,0,0,0,0];
tzgtwns = [0,0,0,0,0,0];
tzgamts = [0,0,0,0,0,0];
tzgtgoalid = [-1,-1,-1,-1,-1,-1,-1,-1];
id = 0;
my_town = -1;
gametype = 0;
score = 0;
score_quarter = 0;
hq = 0;
myhq = 0;
mapX = 0;
mapY = 0;
townarea = 0;
company_name = 0;
static cargo_promilles = [
GSController.GetSetting("cargo0"),
GSController.GetSetting("cargo1"),
GSController.GetSetting("cargo2"),
GSController.GetSetting("cargo3"),
GSController.GetSetting("cargo4"),
GSController.GetSetting("cargo5"),
GSController.GetSetting("cargo6"),
GSController.GetSetting("cargo7"),
                                  
GSController.GetSetting("cargo8"),
GSController.GetSetting("cargo9"),
GSController.GetSetting("cargo10"),
GSController.GetSetting("cargo11"),
GSController.GetSetting("cargo12"),
GSController.GetSetting("cargo13"),
GSController.GetSetting("cargo14"),
GSController.GetSetting("cargo15"),
                                  
GSController.GetSetting("cargo16"),
GSController.GetSetting("cargo17"),
GSController.GetSetting("cargo18"),
GSController.GetSetting("cargo19"),
GSController.GetSetting("cargo20"),
GSController.GetSetting("cargo21"),
GSController.GetSetting("cargo22"),
GSController.GetSetting("cargo23"),
                                  
GSController.GetSetting("cargo24"),
GSController.GetSetting("cargo25"),
GSController.GetSetting("cargo26"),
GSController.GetSetting("cargo27"),
GSController.GetSetting("cargo28"),
GSController.GetSetting("cargo29"),
GSController.GetSetting("cargo30"),
GSController.GetSetting("cargo31"),
];

constructor(company_id, twns, twnAccess) {
	this.towns = twns;	
	this.townAccess = twnAccess;
	claim_news = 0;
	local temp = GSTownList();
	num_towns = temp.Count();
	score_quarter = GSDate.GetMonth(GSDate.GetCurrentDate())/3;
	this.id = company_id;
	this.mapX = GSMap.GetMapSizeX() - 2;
	this.mapY = GSMap.GetMapSizeY() - 2;
	this.townarea = GSController.GetSetting("townarea");
	this.gametype = GSController.GetSetting("gametype");
	if(this.gametype == 0){SetScore_type0_initial();}
	}
	
function Set(new_tzgt, new_tzgtwns, new_id, new_my_town, new_gametype, new_score, new_score_quarter, new_hq, new_town_sign, new_company_name);
function ManageDaily();
function ManageMonthly();
function MoveHQ(tile);
function MoveHQ_type0(tile);
function MoveHQ_type1(tile);
function RateMe_type0(max);
function RateMe_type1(max);
function RateMe_type2(coop);
function SetScore();
function SetRawScore(sc);
function SetScore_type0();
function SetScore_type1();
function SetScore_type2();
function SetScore_type3();
function ReloadTown();

function OnDestroy();
};

function Company::Set(new_tzgt, new_tzgtwns, new_id, new_my_town, new_gametype, new_score, new_score_quarter, new_hq, new_town_sign, new_company_name){
	tzgt=new_tzgt;
	tzgtwns=new_tzgtwns;
	id=new_id;
	my_town=new_my_town;
	gametype=new_gametype;
	score=new_score;
	score_quarter=new_score_quarter;
	hq=new_hq;
	townsign = new_town_sign;
	company_name=new_company_name;
}

function Company::ReloadTown(){
if(my_town != -1){
((towns)[my_town]).company = this.id;	}
}

function Company::ManageDaily(){
// daily process here.
//GSTown.SetText(my_town,"Owner: " + GSCompany.GetName(this.id));
// register the Company Name
  if(GSCompany.GetName(this.id) != company_name) {
    company_name = GSCompany.GetName(this.id)
    if(hq != GSMap.TILE_INVALID) {
      if (this.my_town != -1) {
        if(GSController.GetSetting("Town_Labels")) {
          if(GSSign.IsValidSign(label_sign_id)) {
            GSSign.SetName(label_sign_id, GSText(GSText.STR_CITYBUILDER_TOWNOWNER_SIGN, this.id));
            GSSign.SetName(label_sign_id_top, GSText(GSText.STR_HQAREA_TOP, this.id));
            GSSign.SetName(label_sign_id_bottom, GSText(GSText.STR_HQAREA_BOTTOM, this.id));
            GSSign.SetName(label_sign_id_right, GSText(GSText.STR_HQAREA_RIGHT, this.id));
            GSSign.SetName(label_sign_id_left, GSText(GSText.STR_HQAREA_LEFT, this.id));
          }
        }
      }
    }
  }
  //local teste = GSCompany.GetName(this.id);
	//Log.Info("Company name:"+teste+" .",Log.LVL_INFO);
// register the HQ
	if(GSCompany.GetCompanyHQ(this.id) != hq)
		{
		hq = GSCompany.GetCompanyHQ(this.id);
		if(hq != GSMap.TILE_INVALID)
			{
			MoveHQ(hq);
// set the town's text
			GSTown.SetText(my_town,GSText(GSText.STR_CITYBUILDER_TOWNOWNER, this.id));
			if (this.my_town != -1)
        {
          if(GSController.GetSetting("Town_Labels"))
            {
            local tile = GSTown.GetLocation(my_town);
            local X = GSMap.GetTileX(tile);
            local Y = GSMap.GetTileY(tile);
            local xtop	 = max(X - this.townarea, 1);
            local xbot	 = min(X + this.townarea, this.mapX);
            local yleft	 = max(Y - this.townarea, 1);
            local yright = min(Y + this.townarea, this.mapY);
            if(label_sign_id == -1)
              {
              label_sign_id = GSSign.BuildSign(GSMap.GetTileIndex(X,Y), GSText(GSText.STR_CITYBUILDER_TOWNOWNER_SIGN, this.id));
              label_sign_id_top = GSSign.BuildSign(GSMap.GetTileIndex(xtop, yleft),	GSText(GSText.STR_HQAREA_TOP, this.id));
              label_sign_id_bottom = GSSign.BuildSign(GSMap.GetTileIndex(xbot, yright),	GSText(GSText.STR_HQAREA_BOTTOM, this.id));
              label_sign_id_right = GSSign.BuildSign(GSMap.GetTileIndex(xtop, yright),	GSText(GSText.STR_HQAREA_RIGHT, this.id));
              label_sign_id_left = GSSign.BuildSign(GSMap.GetTileIndex(xbot, yleft),	GSText(GSText.STR_HQAREA_LEFT, this.id));
              }
              else	
              {
              if(GSSign.IsValidSign(label_sign_id))
                {
                GSSign.SetName(label_sign_id, GSText(GSText.STR_CITYBUILDER_TOWNOWNER_SIGN, this.id));
                GSSign.SetName(label_sign_id_top, GSText(GSText.STR_HQAREA_TOP, this.id));
                GSSign.SetName(label_sign_id_bottom, GSText(GSText.STR_HQAREA_BOTTOM, this.id));
                GSSign.SetName(label_sign_id_right, GSText(GSText.STR_HQAREA_RIGHT, this.id));
                GSSign.SetName(label_sign_id_left, GSText(GSText.STR_HQAREA_LEFT, this.id));
                }
              else	
                {
                label_sign_id = GSSign.BuildSign(GSMap.GetTileIndex(X,Y), GSText(GSText.STR_CITYBUILDER_TOWNOWNER_SIGN, this.id));
                label_sign_id_top = GSSign.BuildSign(GSMap.GetTileIndex(xtop, yleft),	GSText(GSText.STR_HQAREA_TOP, this.id));
                label_sign_id_bottom = GSSign.BuildSign(GSMap.GetTileIndex(xbot, yright),	GSText(GSText.STR_HQAREA_BOTTOM, this.id));
                label_sign_id_right = GSSign.BuildSign(GSMap.GetTileIndex(xtop, yright),	GSText(GSText.STR_HQAREA_RIGHT, this.id));
                label_sign_id_left = GSSign.BuildSign(GSMap.GetTileIndex(xbot, yleft),	GSText(GSText.STR_HQAREA_LEFT, this.id));
                }
              }
            }
        } else {
          OnDestroy();
        }
			}
		}
	}

function Company::ManageMonthly(){
this.SetScore();
}

function Company::MoveHQ(tile){


switch(this.gametype)
{
case(0):
this.MoveHQ_type0(tile);
break;
case(1):
this.MoveHQ_type1(tile);
break;
case(2):
this.MoveHQ_type1(tile);
break;
case(3):
this.MoveHQ_type1(tile);
break;
}
}
// FreeBuilder
function Company::MoveHQ_type0(tile){
// In freebuilder, the HQ has no effect.
}
// CityBuilder
function Company::MoveHQ_type1(tile){
local current_town = -1;
if(this.my_town != -1)
	{
	current_town = my_town;
	GSTown.SetText(my_town,""); 
	((this.towns)[my_town]).clearGoal();
	((this.towns)[my_town]).company = -1;
	}
this.my_town = -1;
if(GSSign.IsValidSign(label_sign_id)) 
	{
	GSSign.RemoveSign(label_sign_id);
	GSSign.RemoveSign(label_sign_id_top);
	GSSign.RemoveSign(label_sign_id_bottom);
	GSSign.RemoveSign(label_sign_id_right);
	GSSign.RemoveSign(label_sign_id_left);
	}
// In default CB mode, we claim a town with the HQ.
// Other companies can't build near this town. << Not yet implemented.
local possible_town = GSTile.GetClosestTown(tile);
local max_distance = GSController.GetSetting("hqmaxdist");
local max_claimable = GSController.GetSetting("maxclaimsize");
local tile_possible_town = GSTown.GetLocation(possible_town);
if(GSTown.GetDistanceManhattanToTile(possible_town, tile) <= max_distance)
	{
	local tile = GSTown.GetLocation(my_town);
	Log.Info("Company claiming town: " + GSTown.GetName(possible_town) +" (" + GSTown.GetPopulation(possible_town)+")", Log.LVL_INFO);
	// we might claim the town.
		if(GSTown.IsCity(possible_town)){
			GSGoal.Question(8018, this.id, GSText(GSText.STR_CITYBUILDER_CLAIM_CITY), GSGoal.QT_WARNING, GSGoal.BUTTON_OK);
			return;
			}	
		if(GSTown.GetPopulation(possible_town) > GSController.GetSetting("maxclaimsize") && GSController.GetSetting("maxclaimsize") > 0 && possible_town != current_town)
			{
			GSGoal.Question(8007, this.id, GSText(GSText.STR_CITYBUILDER_TOOLARGE, GSController.GetSetting("maxclaimsize")), GSGoal.QT_WARNING, GSGoal.BUTTON_OK);
			return;
			}
		if(((this.towns)[possible_town]).company != -1)
			{
			GSGoal.Question(8017, this.id, GSText(GSText.STR_CITYBUILDER_ALREADY_CLAIMED, ((this.towns)[possible_town]).company), GSGoal.QT_WARNING, GSGoal.BUTTON_OK);
			return;
			}	
		// #########
		if((((this.towns)[possible_town]).company == -1) && (possible_town != current_town)) //&& current_town != -1 && my_town != -1) // lots to refine here :D
    {
			
			for (local cidhq = GSCompany.COMPANY_FIRST; cidhq <= GSCompany.COMPANY_LAST; cidhq++)
			{
				if (GSCompany.ResolveCompanyID(cidhq) != GSCompany.COMPANY_INVALID)
				{
				local hqloc = GSCompany.GetCompanyHQ(cidhq);
          //myhq = GSCompany.GetCompanyHQ(this.id);
          //Log.Info("cidhq:"+cidhq+" this.id:"+this.id+" HQloc:"+hqloc+" .",Log.LVL_INFO);
          if((hqloc != GSMap.TILE_INVALID) && (this.id != cidhq)) {
          //if((hqloc != -1) && (this.id != cidhq)) {
            local tmpA = GSTile.GetClosestTown(hqloc);
            local tileA = GSTown.GetLocation(tmpA);
            local tileB = GSTown.GetLocation(possible_town);
            //Log.Info("TileA:"+tileA+" TileB:"+tileB+" .",Log.LVL_INFO);
            if(GSTile.GetDistanceSquareToTile(tileA, tileB) < NEIGHBOUR_DISTANCE_MAX)
            //if(GSTile.GetDistanceManhattanToTile(tileA, tileB) < NEIGHBOUR_DISTANCE_MAX) 
            {
              GSGoal.Question(8007, this.id, GSText(GSText.STR_CITYBUILDER_CLOSE_CLAIMED), GSGoal.QT_WARNING, GSGoal.BUTTON_OK);
              return;
            }
          }
				}
			}
		}
    // #########
      OnDestroy();
      this.my_town = possible_town;
      if(possible_town != current_town) {
        GSGoal.Question(8019, this.id, GSText(GSText.STR_CITYBUILDER_TOWN_CLAIM_POPUP, possible_town), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
        Log.Info("The town "+GSTown.GetName(possible_town)+" has been claimed.",Log.LVL_INFO);
        //xShunter.IrcPublicMessage("Claimed town: " + GSTown.GetName(possible_town) + ". By company: " + this.id + ".");
        for (local cid = GSCompany.COMPANY_FIRST; cid <= GSCompany.COMPANY_LAST; cid++)
        {
          if (GSCompany.ResolveCompanyID(cid) != GSCompany.COMPANY_INVALID)
          {
            GSNews.Create(GSNews.NT_GENERAL, GSText(GSText.STR_CITYBUILDER_TOWN_CLAIM, possible_town, this.id) ,cid, GSNews.NR_TOWN, possible_town);
          }
        }
      } else {
        GSGoal.Question(8019, this.id, GSText(GSText.STR_CITYBUILDER_TOWN_CLAIM_SAME, possible_town), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
        Log.Info("The town "+GSTown.GetName(possible_town)+" was the same!",Log.LVL_INFO);
      }
		((this.towns)[possible_town]).company = this.id;	
		local townname = GSTown.GetName(possible_town);
		Log.Info("SendAdmin: citybuilder, claimed, "+this.id+", "+townname+", "+GSTown.GetPopulation(possible_town)+", "+GSMap.GetTileX(GSTown.GetLocation(possible_town))+", "+GSMap.GetTileY(GSTown.GetLocation(possible_town))+".",Log.LVL_INFO);
		CityBuilder.SendAdmin( { event = "citybuilder", action = "claimed", company = this.id, town = townname, population = GSTown.GetPopulation(possible_town), x = GSMap.GetTileX(GSTown.GetLocation(possible_town)), y = GSMap.GetTileY(GSTown.GetLocation(possible_town)) } );
		//xShunter.IrcPublicMessage("Claimed town: " + townname + ". By company: " + this.id);
		//Log.Info("Claimed town?ref:"+((towns.ref())[possible_town]).company+" .",Log.LVL_INFO);

	}
else{
	GSGoal.Question(8016, this.id, GSText(GSText.STR_CITYBUILDER_TOOFAR, GSController.GetSetting("hqmaxdist")), GSGoal.QT_WARNING, GSGoal.BUTTON_OK);	}	
	return;
}

function Company::SetScore(){
switch(this.gametype)
{
case(0):
this.SetScore_type0();
break;
case(1):
this.SetScore_type1();
break;
case(2):
//this.SetScore_type2(); << does nothing
break;
case(3):
//this.SetScore_type3(); << does nothing
break;
} 
}
//////////////////////////////////////////////////////
// Note: this function is quite hacky
// Work in progress.
///////////////////////////////////////////////////
function Company::SetScore_type0_initial(){
	for(local i = 0; i <= 5; ++i) {		
		this.tzgtwns[i] = -1;
		this.tzgtgoalid[i] = -1;
		this.tzgt[i] = -1;
		this.tzgamts[i] = -1
	}
	SetScore_type0_randomizePart(0);
	SetScore_type0_randomizePart(1);
	SetScore_type0_randomizePart(2);
}

function Company::SetScore_type0_randomizePart(i) {
	local j = 0;
	local x = 0;
	
	do {
		++j;
		// Grab a random town
		x = GSBase.RandRange(this.townAccess.len());
		this.tzgtwns[i] = this.townAccess[x];
		this.tzgt[i] = GSBase.RandRange(this.towns[this.townAccess[x]].econ.num_cargos);
		local rMul = GSBase.RandRange(this.multiplier) + 1000.0;
		this.tzgamts[i] = (this.towns[tzgtwns[i]].goal_cargo[this.tzgt[i]] * rMul / 1000).tointeger();
		GSLog.Info("NAME: " + GSTown.GetName(this.townAccess[x]) + "GOAL: " + this.towns[this.townAccess[x]].goal_cargo[this.tzgt[i]] + " SUPPLY:  "  + this.towns[this.townAccess[x]].supply_cargo[this.tzgt[i]] + " STOCK: " + this.towns[this.townAccess[x]].stocked_cargo[this.tzgt[i]]  );
	}
	while((this.towns[this.townAccess[x]].goal_cargo[this.tzgt[i]] <= 
	this.towns[this.townAccess[x]].supply_cargo[this.tzgt[i]] + 
	this.towns[this.townAccess[x]].stocked_cargo[this.tzgt[i]] 
	|| this.towns[this.townAccess[x]].goal_cargo[this.tzgt[i]] == 0) && j < 1000);
}

function Company::SetScore_type0_goal(i, str, mrem) {
	if(this.tzgtgoalid[i] != -1) {
		GSGoal.Remove(tzgtgoalid[i]);
	}		
	if(this.tzgamts[i] > 0) {
		tzgtgoalid[i] = GSGoal.New(this.id,GSText(str, tzgtwns[i], tzgt[i], tzgamts[i], mrem),GSGoal.GT_NONE,0);
	}
}

function Company::AddPickupAmountTypeZero(u) {
	if(tzgamts[u] > 0) {
		local sta = min(this.towns[tzgtwns[u]].supply_cargo[tzgt[u]],tzgamts[u]);
		if(sta >= 1) {
			// Transported. award log[x] points. 
			return log(sta);
		} else {
			// Nothing transported, no points. 
			return 0;
		}
	} else {
		// requirement doesn't exist
		return 0;
	}
}

function Company::SetScore_type0_Quarterly() {
	local month = GSDate.GetMonth(GSDate.GetCurrentDate());
	local qt = month / 3;
	local nwsmsg = "";
	local x; 
	score_quarter++;
	score_quarter %= 4;
	local income = GSCompany.GetQuarterlyIncome(this.id, GSCompany.CURRENT_QUARTER);
	local deliv = GSCompany.GetQuarterlyCargoDelivered(this.id,  GSCompany.CURRENT_QUARTER);
	if(income >= 1) {
		score += log(income);
	}
	if(deliv >= 1) {
		score += log(deliv);	
	}
		local hasbuild = false;
	// and now for the real sneaky one.
	// rating based on 'challenges'
	// Random town each 3 months, random cargo type.
	// Then take Logarithm.
		GSCargoMonitor.GetTownPickupAmount (this.id, tzgt[3], tzgtwns[3], true);	
		qt = tzgtwns[5];
		for(local i = 4; i >= 0; --i) {
			tzgt[i+1] = tzgt[i]; tzgtwns[i+1] = tzgtwns[i]; this.tzgamts[i+1] = this.tzgamts[i];
		}
		this.SetScore_type0_randomizePart(0);
//		Log.Info("Current score: "+score, Log.LVL_INFO);
		if(qt > 0) {
			GSGoal.Remove(tzgtgoalid[6]);
			tzgtgoalid[6] = GSGoal.New(this.id,GSText(GSText.STR_CITYBUILDER_SUBSIDY_2, qt),GSGoal.GT_NONE,0);
		}
}

function Company::SetScore_type0(){
	local month = GSDate.GetMonth(GSDate.GetCurrentDate());
	local qt = month / 3;
	local nwsmsg = "";
	local x;
	if(month % 3 == 0){
		this.SetScore_type0_Quarterly();
	} 
	local addscore = 0;
	addscore += this.AddPickupAmountTypeZero(3);
	addscore += this.AddPickupAmountTypeZero(4);
	addscore += this.AddPickupAmountTypeZero(5);
	score += addscore;	
	GSNews.Create(GSNews.NT_GENERAL, GSText(GSText.STR_CITYBUILDER_SUBSIDY_SCORE, addscore.tointeger()) ,this.id);
	this.SetScore_type0_goal(5, GSText.STR_CITYBUILDER_SUBSIDY_3, 3 - month % 3);
	this.SetScore_type0_goal(4, GSText.STR_CITYBUILDER_SUBSIDY_3, 6 - month % 3);
	this.SetScore_type0_goal(3, GSText.STR_CITYBUILDER_SUBSIDY_3, 9 - month % 3);
	this.SetScore_type0_goal(2, GSText.STR_CITYBUILDER_SUBSIDY_6, 3 - month % 3);
	this.SetScore_type0_goal(1, GSText.STR_CITYBUILDER_SUBSIDY_6, 6 - month % 3);
	this.SetScore_type0_goal(0, GSText.STR_CITYBUILDER_SUBSIDY_6, 9 - month % 3);
}
// DEPRECATED
function Company::SetScore_type1(){
	if(my_town != -1){
		this.score = GSTown.GetPopulation(this.my_town);
	}
}
// set a raw score computed somewhere else.
function Company::SetRawScore(sc){
	this.score = sc;
	return sc;
}

function Company::SetScore_type2(){
// for now, we don't use this function.
// when coop games scores are refined do here.
// I'm skeptical of company-specific scores for coop though.
// for now, all companies get the same score.
return;
}

function Company::SetScore_type3(){
// for now, we don't use this function.
// when coop games scores are refined do it here.
// I'm skeptical of company-specific scores for coop though.
// for now, all companies get the same score.
return;
}

///////////////////////////////////////////
// rate the company according to its score.
// margins of 100-80-50-20-5.
///////////////////////////////////////////
function Company::RateMe_type1(max){

// win
if(score == max){
	GSGoal.Question(8002, this.id, GSText(GSText.STR_CITYBUILDER_WON, score.tointeger()), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
}
// near-win (>80%)
else if(score * 100 > max * 80){
	GSGoal.Question(8003, this.id, GSText(GSText.STR_CITYBUILDER_CLOSE, score.tointeger()), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
}
// good (>50%)
else if(score * 100 > max * 50){
	GSGoal.Question(8004, this.id, GSText(GSText.STR_CITYBUILDER_GOOD, score.tointeger()), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
}
// decent(>20%)
else if(score * 100 > max * 20){
	GSGoal.Question(8005, this.id, GSText(GSText.STR_CITYBUILDER_OKAY, score.tointeger()), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
}

// poor (>5%)
else if(score * 100 > max * 5){
	GSGoal.Question(8006, this.id, GSText(GSText.STR_CITYBUILDER_LOST, score.tointeger()), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
}

// bad. (<5%)
else{
	GSGoal.Question(8007, this.id, GSText(GSText.STR_CITYBUILDER_DESTROYED), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
}
}

///////////////////////////////////////////
// rate the company according to its score. freebuilder version
// freebuilder tends to have greater score variation.
// whence the margins are a bit more tolerant at 100-70-40-10-2
///////////////////////////////////////////
function Company::RateMe_type0(max){

// win
if(score == max){
	GSGoal.Question(8009, this.id, GSText(GSText.STR_CITYBUILDER_WON, score.tointeger()), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
}
// near-win (>70%)
else if(score * 100 > max * 70){
	GSGoal.Question(8010, this.id, GSText(GSText.STR_CITYBUILDER_CLOSE, score.tointeger()), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
}
// good (>40%)
else if(score * 100 > max * 40){
	GSGoal.Question(8011, this.id, GSText(GSText.STR_CITYBUILDER_GOOD, score.tointeger()), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
}
// decent(>10%)
else if(score * 100 > max * 10){
	GSGoal.Question(8012, this.id, GSText(GSText.STR_CITYBUILDER_OKAY, score.tointeger()), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
}

// poor (>2%)
else if(score * 100 > max * 2){
	GSGoal.Question(8013, this.id, GSText(GSText.STR_CITYBUILDER_LOST, score.tointeger()), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
}

// bad. (<2%)
else{
	GSGoal.Question(8014, this.id, GSText(GSText.STR_CITYBUILDER_DESTROYED), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
}
}
// coop rating is simple.
function Company::RateMe_type2(coop){
GSGoal.Question(8008, this.id, GSText(GSText.STR_CITYBUILDER_COOP_FINISH, coop), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
}
//
// Call when the company ceases to exist, then destroy object.
//
function Company::OnDestroy(){
// if we have a town, set the text off. 
if(my_town != -1){GSTown.SetText(my_town,"");}
if(label_sign_id != -1)
{
  GSSign.RemoveSign(label_sign_id);
  GSSign.RemoveSign(label_sign_id_top);
  GSSign.RemoveSign(label_sign_id_bottom);
  GSSign.RemoveSign(label_sign_id_right);
  GSSign.RemoveSign(label_sign_id_left);
  CityBuilder.SendAdmin( { event = "citybuilder", action = "unclaimed", company = this.id } );
}
Log.Info("Company sign reset", Log.LVL_INFO);
}

// SendAdmin Function for CityBuilder


class SList {

goals = [];
//scores = [];
//nums = [];
goalslist = null;
popvalue = 0;

constructor(){
  goalslist = GSList();
}
function Manage(companies);
function GetCompanyByID(companies, id);
};

function SList::GetCompanyByID(companies, id){
	foreach(company in companies) {
		if(id == company.id) return company;
	}
	return null;
}

function SList::Manage(companies){
  local game_goal = GSController.GetSetting("gamegoal");
  local max_claim = GSController.GetSetting("maxclaimsize");
  goalslist.Clear();
  foreach(goal in goals)
    {
    GSGoal.Remove(goal);
    }
  //scores = [];
  //nums = [];
  //goals = [];
  //local i = 0;
  foreach(company in companies)
    {
      if (company.my_town != -1) {
        goalslist.AddItem(company.id, company.score.tointeger());
        //scores.append(company.score.tointeger());
        //nums.append(i);
        //i++;
      } else {
        goalslist.AddItem(company.id, -1);
      }
    }

  local game_time = GSController.GetSetting("gametime");
  if(game_time > 0) {
    local date = GSDate.GetCurrentDate();
    local game_year = GSDate.GetYear(date);
    local game_month = GSDate.GetMonth(date);
    local startyear = GSGameSettings.GetValue("starting_year");
    local rem_years = game_time - (game_year - startyear) - 1;
    local rem_months = 12 - game_month;
    //GSLog.Info("Duration: " + game_time + "; Year:" + game_year + "; Month: " + game_month + "; Rem_years: " + rem_years + "; Rem_Months: " + rem_months);
    goals.push(GSGoal.New(GSCompany.COMPANY_INVALID, GSText(GSText.STR_CITYBUILDER_SCORELIST_TIME_LEFT, rem_years, rem_months), GSGoal.GT_NONE, 0));
  } else {
    //goals.push(GSGoal.New(GSCompany.COMPANY_INVALID, GSText(GSText.STR_CITYBUILDER_SCORELIST_LINE, game_goal), GSGoal.GT_NONE, 0));
  }
  //goals.push(GSGoal.New(GSCompany.COMPANY_INVALID, GSText(GSText.STR_CITYBUILDER_GW_START_COMPANY_GOALS), GSGoal.GT_NONE, 0));
  
  //goals.push(GSGoal.New(GSCompany.COMPANY_INVALID, GSText(GSText.STR_CITYBUILDER_GW_START_COMPANY_GOALS), GSGoal.GT_NONE, 0))
  //goals.push(GSGoal.New(GSCompany.COMPANY_INVALID, GSText(GSText.STR_CITYBUILDER_SCORELIST_LINE, game_goal), GSGoal.GT_NONE, 0));

  goalslist.Sort(GSList.SORT_BY_VALUE, GSList.SORT_DESCENDING);
  //QSort(scores, nums);
  //for(local j = 0; j < companies.len(); ++j){
  local rank = 1;
  local pass = false;
  local company;
  foreach(companyid, _ in goalslist) {
    company = GetCompanyByID(companies, companyid);
    //if(!company || company.hq == GSMap.TILE_INVALID || company.town_id == INVALID_TOWN) continue;
    if(!company) continue;
      if (company.my_town != -1) {
        popvalue = goalslist.GetValue(companyid);
        if(game_time > 0) {
          goals.push(GSGoal.New(GSCompany.COMPANY_INVALID, GSText(GSText.STR_CITYBUILDER_SCORELIST_TIMED, rank, company.id, company.my_town, popvalue), GSGoal.GT_TOWN, company.my_town));
        } else {
          goals.push(GSGoal.New(GSCompany.COMPANY_INVALID, GSText(GSText.STR_CITYBUILDER_SCORELIST, rank, company.id, (100 * popvalue / game_goal), company.my_town, popvalue), GSGoal.GT_TOWN, company.my_town));
        }
        rank++;
      } else {
        //GSLog.Info(companies[company].id + ": Score: 0");
        GSGoal.Question(0, company.id, GSText(GSText.STR_CITYBUILDER_HQ_PLACE_INFO, max_claim), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
        goals.push(GSGoal.New(GSCompany.COMPANY_INVALID, GSText(GSText.STR_CITYBUILDER_SCORELIST_NOTOWN, rank, company.id), GSGoal.GT_NONE, 0));
        rank++;
      }
  }
}
