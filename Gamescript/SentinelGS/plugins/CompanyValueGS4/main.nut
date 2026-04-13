/*
	This is an edit of gamescript: Company Value GS v4 created by Xarick (https://www.tt-forums.net/viewtopic.php?f=65&t=82633).
	It implements a goal where players have to reach a certain company value to win the game.
	The script can also be used in a ranking mode, where it simply tracks the company values and rankings without a specific goal.

	Edited by Chucky for Sentinel Controller.
*/

class CompanyValueGS4
{
	//plugin defaults
	api=null;
	constructor(_api) {
        this.api = _api;
    }

	/* gamescriptcode starts here */
	companies = null;
	goal_mode = null;
	goal_reached = null;
	goal_value = null;

	goal_company = {
		c_id = null,
		goal_value = null,
		days_taken = null
	};
	rankings = null;

	best_value = 1;
	end_year = GSController.GetSetting("end_year");
	_restart = GSController.GetSetting("restart");

	announce = false;
	announce1 = false;
	announce2 = false;
	_unpaused = false;
	global_list = GSList();
	//scp = null;
	ping = 0;
	game_end_time = 0;

	//league table:
	League_ID1 = 1;
	League_ID2 = 1;
	League_element_ID = 0;
	rank_id=1;

	function Start();
	function Save();
	function Load(version, data);


	function GetName() { return "CompanyValueGS4"; }

	function OnMessage(info) {}

/*
	--- GOAL INFO & PROGRESS COMMUNICATION WITH CONTROLLER ---
	These functions are used to send information about the goal
	and the progress of the companies to the controller, which
	can then be used to display this information in a custom UI
	or for other purposes.
*/
	function SendGoalInfo() {
		this.api.Log("CompanyValueGS4: Sending goalinfo data to controller");
        this.api.SendToController({
            event = "goaltypeinfo",
            goalmastergame = 9, // ScriptGoal
            target_value = this.goal_value,
			target_mode = "companyvalue"
        });
	}

	function SendGoalProgress(company, value, progress) {
		this.api.Log("CompanyValueGS4: Sending update for company: " + company + " value: " + value + " progress: " + progress+" %");
		this.api.SendToController({
            event = "companyprogress",
            goalmastergame = 9, // ScriptGoal
            company = company,
			value = value,
            progress = progress
        });
	}

	function TriggerWin(company, amount) {
        local cName = GSCompany.GetName(company);

        //this.api.ChatPublic("Goal reached! " + cName + " has won this game with a company value of " + amount + " !!!");
		this.api.Log("CompanyValueGS4: Sending winner to controller");

        this.api.SendToController({
            event = "winner",
            company = company,
			amount = amount
        });
	}

	/* gamscript code continues here */
	function Save()
	{
		this.api.Log("CompanyValueGS4: GS is saving...");

		return {
			companies = this.companies,
			goal_mode = this.goal_mode,
			goal_reached = this.goal_reached,
			goal_company = this.goal_company,
			rankings = this.rankings
		};
	}

	function Load(version, data)
	{
		this.api.Log("CompanyValueGS4: GS is loading...");
		this.Initialize();

		this.companies = data.companies;
		this.goal_mode = data.goal_mode;
		this.goal_reached = data.goal_reached;
		this.goal_company = data.goal_company;
		this.rankings = data.rankings;
	}

	function Initialize()
	{
		this.api.Log("CompanyValueGS4: GS is (re)initializing...");
		if (this.companies == null) {
			this.companies = {};
			for (local c_id = GSCompany.COMPANY_FIRST; c_id < GSCompany.COMPANY_LAST; c_id++) {
				this.companies[c_id] <- null;
				this.companies[c_id] = {
				goal_id = null,
				inauguration_date = null
				};
			}
		}

		if (this.goal_mode == null) {
			this.goal_mode = GSController.GetSetting("goal_mode") == 1 ? true : false;
		}

		if (this.goal_value == null) {
			this.goal_value = GSController.GetSetting("goal_value") * 1000;
			this.api.Log("CompanyValueGS4: Initialized goal value = " + this.goal_value);
		}

		if (this.goal_reached == true) {
			this.TriggerWin(this.goal_company.c_id, this.goal_company.goal_value);
		}

		if (this.rankings == null) {
			this.rankings = {};
			for (local rank = GSCompany.COMPANY_FIRST + 1; rank <= GSCompany.COMPANY_LAST; rank++) {
				this.rankings[rank] <- null;
				this.rankings[rank] = {
					goal_id = null,
					c_id = null,
					c_value = null,
					c_progress = null,
				};
			}
		}
	}



	function CreateLeague()
	{
		GSLog.Info("Create league table(s) ...");
 /*
	//league table 0
	League_ID1 = GSLeagueTable.New("TOP-15 of current game","","");
	GSLog.Info("--- Leage table ID: "+League_ID1+" has been created.");

	local count=1;
	for (local company = GSCompany.COMPANY_FIRST; company <= GSCompany.COMPANY_LAST; company++){
		League_element_ID = company+1;
		if (count==16) break;
		local company_id = GSCompany.ResolveCompanyID(company);
		GSLog.Info("Create row for company: "+company_id);
		//League_element_ID = GSLeagueTable.NewElement( League_ID1, 1, company,"Score:",this.rankings[company].c_value,GSLeagueTable.LINK_NONE,0);
		//League_element_ID = GSLeagueTable.NewElement( League_ID1, count, GSCompany.COMPANY_INVALID,"Unknown Transport (Max Mustermann)",GSText(GSText.STR_POINTS,0),GSLeagueTable.LINK_NONE,0);
		League_element_ID = GSLeagueTable.NewElement( League_ID1, count, company_id,"Unknown Transport (Max Mustermann)",GSText(GSText.STR_POINTS,0),GSLeagueTable.LINK_NONE,0);
		GSLog.Info("Leage table: "+League_ID1+" element ID: "+League_element_ID+" created.");
		count++;
	}
	GSLog.Info("--- Leage table ID: "+League_ID1+" has been finished.");
 */

	//league table 1
		League_ID2 = GSLeagueTable.New("TOP-10 of this server","","");
		GSLog.Info("--- Leage table ID: "+League_ID2+" has been created.");

		rank_id = 1;
		for (rank_id; rank_id < 11; rank_id++){
			//local company_id = GSCompany.ResolveCompanyID(company);
			League_element_ID = GSLeagueTable.NewElement( League_ID2, rank_id, GSCompany.COMPANY_INVALID,"Unknown Transport (Max Mustermann)",GSText(GSText.STR_POINTS,0),GSLeagueTable.LINK_NONE,0);
			GSLog.Info("Leage table: "+League_ID2+" element ID: "+League_element_ID+" created.");

		}

		//League_element_ID = GSLeagueTable.NewElement( League_ID1, 0, ec_id,GSCompany.GetName(ec_id)+"  Score: ","0",GSLeagueTable.LINK_COMPANY,0);
		//GSLog.Info("Leage table element ID "+League_element_ID+" created.");

	}

	function UpdateTop10()
	{
		rank_id = 1;
		//local name = GSCompany.GetName(this.goal_company.c_id);
		//GSLeagueTable.UpdateElementData(rank_id, name ,0,0)
		//GSLeagueTable.UpdateElementScore( 1, 1, this.goal_company.goal_value);


		local name = GSCompany.GetName(this.rankings[rank_id].c_id);
		GSLeagueTable.UpdateElementData(9, GSCompany.COMPANY_INVALID,name ,0,0)
		local newscore = this.rankings[rank_id].c_value *2 / 1000;

		GSLeagueTable.UpdateElementScore( 9, 100, GSText(GSText.STR_POINTS,newscore));


		GSLog.Info("Update: "+newscore);
		GSController.Sleep(1000);


 		//GSGoal.Question(25, GSCompany.COMPANY_INVALID, GSText(GSText.STR_GOAL_REACHED, this.goal_company.days_taken, this.goal_company.c_id, this.goal_company.c_id, this.goal_company.goal_value), GSGoal.QT_INFORMATION, GSGoal.BUTTON_CONTINUE);
 		//GSLeagueTable.UpdateElementScore( 0,this.rankings[1].c_value,this.rankings[1].c_value);

	}

	function Run(ticks) {
        if (ticks % 75 == 0) {
            this.UpdateScoreboard();
			//this.api.Log("CompanyValueGS4: Tick...");
        }
    }

	function OnMessage(info) {
		//this.api.Log("CompanyValueGS4: Received message of type " + info.GetType());
    }

	function OnEvent(type,ev) {

			local eventType = type;
			//local e = GSEventController.GetNextEvent();
			//this.api.Log("CompanyValueGS4 received event of type " + eventType);
			if (eventType == GSEvent.ET_GOAL_QUESTION_ANSWER) {
				local ec = GSEventGoalQuestionAnswer.Convert(ev);
				local eq_id = ec.GetUniqueID();
				local ec_id = ec.GetCompany();
				if (this.goal_mode != false) {
					if (this.goal_reached == true) {
						if (eq_id == 25) {
							if (ec.GetButton() == GSGoal.BUTTON_CONTINUE) {
								GSGame.Unpause();
								local ec_num = ec_id + 1;
								GSLog.Warning("Game unpaused by " + GSCompany.GetName(ec_id) + " (Company " + ec_num + ").")
								GSGoal.CloseQuestion(eq_id);
								for (local c_id = GSCompany.COMPANY_FIRST; c_id < GSCompany.COMPANY_LAST; c_id++) {
									if (this.companies[c_id].goal_id != null) {
										GSGoal.Remove(this.companies[c_id].goal_id);
										this.companies[c_id].goal_id = null;
										this.companies[c_id].inauguration_date = null;
									}
								}
								this.goal_company.c_id = null;
								this.goal_company.goal_value = null;
								this.goal_company.days_taken = null;
								this.goal_reached = null;
								update_method = null;
								this.goal_mode = false;
								GSLog.Warning("Company Value GS has switched to Ranking mode.");
							}
							if (ec.GetButton() == GSGoal.BUTTON_OK) {
								GSGoal.CloseQuestion(eq_id);
							}
						}
					}
				}
			}

			if (eventType == GSEvent.ET_COMPANY_NEW) {
				local ec = GSEventCompanyNew.Convert(ev);
				local ec_id = ec.GetCompanyID();

				//League_element_ID = GSLeagueTable.NewElement( League_ID, 1, ec_id,"Score:","0",GSLeagueTable.LINK_NONE,0);
				//League_element_ID = GSLeagueTable.NewElement( League_ID, 0, ec_id,GSCompany.GetName(ec_id)+"  Score: ","0",GSLeagueTable.LINK_COMPANY,0);
				//GSLog.Info("Leage table element ID "+League_element_ID+" created.");

				if (this.goal_mode != false) {
					if (this.goal_reached == true) {
						this.goal_reached = GSGoal.Question(25, ec_id, GSText(GSText.STR_GOAL_REACHED, this.goal_company.days_taken, this.goal_company.c_id, this.goal_company.c_id, this.goal_company.goal_value), GSGoal.QT_INFORMATION, GSGoal.BUTTON_CONTINUE);
						local ec_num = ec_id + 1;
					} else {
						assert(this.companies[ec_id].inauguration_date == null);
						local inauguration_date = GSDate.GetCurrentDate();
						assert(this.companies[ec_id].goal_id == null);
						this.companies[ec_id].goal_id = GSGoal.New(ec_id, GSText(GSText.STR_COMPANY_GOAL, goal_value), GSGoal.GT_COMPANY, ec_id);
						this.companies[ec_id].inauguration_date = inauguration_date;
						GSGoal.Question(ec_id, ec_id, GSText(GSText.STR_COMPANY_GOAL, goal_value), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
					}
				}
				else {
					GSGoal.New(ec_id, GSText(GSText.STR_RANK,end_year), GSGoal.GT_NONE, 0);
					GSGoal.Question(ec_id, ec_id, GSText(GSText.STR_RANK, end_year), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
					if (GSGame.IsPaused()==true) GSGame.Unpause();
				}
			}

			if (eventType == GSEvent.ET_COMPANY_BANKRUPT) {
				local ec = GSEventCompanyBankrupt.Convert(ev);
				local ec_id = ec.GetCompanyID();
				if (this.goal_mode != false) {
					if (this.companies[ec_id].goal_id != null) {
						GSGoal.Remove(this.companies[ec_id].goal_id);
						this.companies[ec_id].goal_id = null;
						this.companies[ec_id].inauguration_date = null;
					}
					GSGoal.CloseQuestion(ec_id);
				}
			}

			if (eventType == GSEvent.ET_COMPANY_MERGER) {
				local ec = GSEventCompanyMerger.Convert(ev);
				local ec_id = ec.GetOldCompanyID();
				if (this.goal_mode != false) {
					if (this.companies[ec_id].goal_id != null) {
						GSGoal.Remove(this.companies[ec_id].goal_id);
						this.companies[ec_id].goal_id = null;
						this.companies[ec_id].inauguration_date = null;
					}
					GSGoal.CloseQuestion(ec_id);
				}
			}
	}

	function Start()
	{
		this.api.Log("Plugin CompanyValueGS4 is starting ...");
		this.Initialize();

		if (this.goal_mode != false) {
			this.api.Log("CompanyValueGS4 is in Goal mode.");
		} else {
		this.api.Log("CompanyValueGS4 is in Ranking mode.");
		}

		//this.CreateLeague(); //disable league table for now
		this.api.Log("CompanyValueGS4: Short break for controller...");
		//GSController.Sleep(1000); //wait for sentinel to be ready before sending goal info
		this.SendGoalInfo();
		this.UpdateScoreboard();
	}

	function UpdateScoreboard() {
		//this.api.Log("CompanyValueGS4: Tick...");
		ping++;
		//var
		local month = GSDate.GetMonth(GSDate.GetCurrentDate());
		local year = GSDate.GetYear(GSDate.GetCurrentDate());
		local day = GSDate.GetDayOfMonth(GSDate.GetCurrentDate());

		//logs
		//GSLog.Info("Current month / year: "+month+" / "+year);
		//GSLog.Info("Server end year: "+end_year);

		local update_method = false;

		if (this.goal_reached == null) {
			if (update_method != null) {
				update_method = false;
			} else {
				this.goal_mode = null;
			}

			/* update company values */
			for (local c_id = GSCompany.COMPANY_FIRST; c_id < GSCompany.COMPANY_LAST; c_id++) {
				if (GSCompany.ResolveCompanyID(c_id) != GSCompany.COMPANY_INVALID) {
					//local c_value = GSCompany.GetQuarterlyCompanyValue(c_id, GSCompany.CURRENT_QUARTER);
					/* always get the value of the first previous quarter */
					local c_value = GSCompany.GetQuarterlyCompanyValue(c_id, 1);
					if (this.global_list.HasItem(c_id)) {
						if (this.global_list.GetValue(c_id) != c_value) {
							this.global_list.SetValue(c_id, c_value);
							if (update_method != null) update_method = true;
						}
					} else {
						this.global_list.AddItem(c_id, c_value);
						update_method = null;
					}
				} else {
					if (this.global_list.HasItem(c_id)) {
						this.global_list.RemoveItem(c_id);
						if (update_method != null) update_method = true;
					}
				}
			}

			if (this.goal_mode != false) {
				if (this.best_value != goal_value) {
					this.best_value = goal_value;
					if (update_method != null) update_method = true;
				}
			}

			if (update_method != false) {
				//GSLog.Info("=====Starting goal computations=====")

				local rank = 0;
				if (this.global_list.Count() > 0) {
					this.global_list.Sort(GSList.SORT_BY_VALUE, GSList.SORT_DESCENDING);

					for (local c_id = this.global_list.Begin(); !this.global_list.IsEnd(); c_id = this.global_list.Next()) {
						rank++;

						local c_value = this.global_list.GetValue(c_id);
						if (this.goal_mode != true) {
							if (rank == 1) {
								this.best_value = c_value;
							}
						}

						if (this.rankings[rank].goal_id != null) {
							if (update_method == null && this.goal_mode != false) {
								GSGoal.Remove(this.rankings[rank].goal_id);
								this.rankings[rank].goal_id = null;
								this.rankings[rank].c_id = null;
								this.rankings[rank].c_value = null;
								this.rankings[rank].c_progress = null;
								this.rankings[rank].goal_id = GSGoal.New(GSCompany.COMPANY_INVALID, GSText(GSText.STR_RANK_COMPANY_NUM, rank, c_id, c_id), GSGoal.GT_NONE, 0);
								this.rankings[rank].c_id = c_id;
								this.rankings[rank].c_value = c_value;
							} else {
								if (this.rankings[rank].c_id != c_id) {
									GSGoal.SetText(this.rankings[rank].goal_id, GSText(GSText.STR_RANK_COMPANY_NUM, rank, c_id, c_id));
									if (this.rankings[rank].c_id != c_id) {
										this.rankings[rank].c_id = c_id;
									}
								}
							}
						} else {
							this.rankings[rank].goal_id = GSGoal.New(GSCompany.COMPANY_INVALID, GSText(GSText.STR_RANK_COMPANY_NUM, rank, c_id, c_id), GSGoal.GT_NONE, 0);
							this.rankings[rank].c_id = c_id;
							this.rankings[rank].c_value = c_value;
						}

						local c_progress = (c_value * 100) / this.best_value;
						if (this.goal_mode != false) {
							if (c_progress > 100) {
								c_progress = 100;
							}
						}

						/* update rankings progress */
						if (this.rankings[rank].c_value != c_value || this.rankings[rank].c_progress != c_progress) {
							GSGoal.SetProgress(this.rankings[rank].goal_id, GSText(GSText.STR_GOAL_PROGRESS, c_value, c_progress));
						}

						/* update company goals progress */
						if (this.goal_mode != false) {
							if (this.companies[c_id].goal_id != null) {
								if (GSGoal.IsValidGoal(this.companies[c_id].goal_id)) {
									if (this.rankings[rank].c_value != c_value || this.rankings[rank].c_progress != c_progress) {
										GSGoal.SetProgress(this.companies[c_id].goal_id, GSText(GSText.STR_GOAL_PROGRESS, c_value, c_progress));
										this.SendGoalProgress(c_id, c_value, c_progress);
									}
								}
							}
						}

						if (this.rankings[rank].c_value != c_value) {
							this.rankings[rank].c_value = c_value;
						}

						if (this.rankings[rank].c_progress != c_progress) {
							this.rankings[rank].c_progress = c_progress;
						}

						/* check for goal reached */
						if (this.goal_mode == true) {
							if (c_value >= goal_value) {
								if (this.goal_reached != true) {
									local days_taken = GSDate.GetCurrentDate() - this.companies[c_id].inauguration_date;
									local c_num = c_id + 1;
									this.goal_company.c_id = c_id;
									this.goal_company.goal_value = c_value; //use the actual value reached as the goal value to be able to show it in the goal reached message
									this.goal_company.days_taken = days_taken;
									this.goal_reached = true;
								}
							}
						}
					}
					if (this.goal_mode == null) {
						this.goal_mode = false;
					}
				}

				while (rank < GSCompany.COMPANY_LAST) {
					rank++;
					if (this.rankings[rank].goal_id != null) {
						GSGoal.Remove(this.rankings[rank].goal_id);
						this.rankings[rank].goal_id = null;
						this.rankings[rank].c_id = null;
						this.rankings[rank].c_value = null;
						this.rankings[rank].c_progress = null;
					}
				}


				//GSLog.Info("=====Ended goal computations=====");

				if (this.goal_reached == true) {
					for (local c_id = GSCompany.COMPANY_FIRST; c_id < GSCompany.COMPANY_LAST; c_id++) {
						if (GSCompany.ResolveCompanyID(c_id) != GSCompany.COMPANY_INVALID) {
							GSGoal.CloseQuestion(c_id);
						}
					}
					this.TriggerWin(this.goal_company.c_id, this.goal_company.goal_value);
					GSGoal.Question(25, GSCompany.COMPANY_INVALID, GSText(GSText.STR_GOAL_REACHED, this.goal_company.days_taken, this.goal_company.c_id, this.goal_company.c_id, this.goal_value), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
					//this.UpdateTop10();
					//GSGame.Pause();
					//GSLog.Warning("Game paused. Asking companies to continue...");
				}
			}
		}

		//announce last year
		if ((year == end_year) && (month == 1) && (day == 10) && (announce == false)){

			GSLog.Info("Info: Announce last year");
			GSGoal.Question(26, GSCompany.COMPANY_INVALID, GSText(GSText.STR_SERVER_INFO), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
			announce = true;
		}

		//announce restart soon
			if ((year == (_restart-1)) && (month == 12) && (day == 25) && (announce1 == false)){
				GSLog.Info("Info: Server restart soon ...");
				GSGoal.Question(27, GSCompany.COMPANY_INVALID, GSText(GSText.STR_RESTART), GSGoal.QT_WARNING, GSGoal.BUTTON_OK);
				announce1 = true;
			}
		/*
		//announce winner
		if ((year == end_year) && (month == 12) && (day == 30) && (announce2 == false)){

			GSLog.Info("Info: Announce winner");
			GSGoal.Question(28, GSCompany.COMPANY_INVALID, GSText(GSText.STR_WINNER,this.rankings[1].c_id,_restart), GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
			GSGame.Pause();
			announce2 = true;
		}
		*/
		//ping-pong server
		if (ping==10) {
			this.api.Log("CompanyValueGS4: <Ping>");
			//GSLeagueTable.UpdateElementScore( 0,this.rankings[1].c_value,this.rankings[1].c_value);
			ping=0;
		}
		/*
		//update top10
		if (day == 5){

			GSLog.Info("Update League table");
			this.UpdateTop10();
		}
		*/

	}

}