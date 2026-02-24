from plugin_interface import IPlugin

class AntiCheat(IPlugin):
    """
    Prevents players from building level crossings over railways or roads owned by other companies.
    Delegates the coordinate check to GameScript.
    """
    def __init__(self, client):
        super().__init__(client)
        self.name = "AntiCheat"
        self.version = "1.0"

    def on_load(self):
        self.client.log(f"[{self.name}] Loaded v{self.version}")

    def on_do_command(self, client_id, cmd_id, p1, p2, tile, text, frame, params=None):
        if client_id == 1: 
            return # Ignore server/system

        # Locate command name
        cmd_name = self.client.command_names.get(cmd_id, "")
        print(f"[AntiCheat] DEBUG Raw Command ID {cmd_id} (Name: '{cmd_name}') from Client {client_id}")

        if not cmd_name: 
            return

        # Check if it's a track construction command
        is_construction = (
            cmd_name == "CmdBuildRoad" or 
            cmd_name == "CmdBuildSingleRail" or
            cmd_name == "CmdBuildLongRoad" or 
            cmd_name == "CmdBuildRailroadTrack" or 
            cmd_name == "CmdBuildRoadStop" # Included for drive-throughs
        )

        if is_construction and params:
            data = self.client.get_service("DataController")
            if not data or client_id not in data.clients:
                return
            
            company_id = data.clients[client_id].get('company', 255)
            if company_id == 255:
                return # Spectators can't build anyway

            tiles_to_check = []
            
            # 1. Primary Tile
            if "Tile" in params: 
                tiles_to_check.append(params["Tile"])
            
            # 2. Start/End Ranges
            if "StartTile" in params:
                if "Tile" in params: # CmdBuildRoad
                    tiles_to_check.append(params["StartTile"])
                    tiles_to_check.append(params["Tile"])
                elif "EndTile" in params: # CmdBuildLongRoad, CmdBuildRailroadTrack
                    tiles_to_check.append(params["StartTile"])
                    tiles_to_check.append(params["EndTile"])

            # Send tiles to GameScript for verification natively
            # Since a command might encompass two endpoints, we tell GameScript to check all involved tiles
            import json
            
            # Convert to list of strings for GameScript
            tiles_strs = [str(t) for t in tiles_to_check]
            
            payload = json.dumps({
                "event": "check_crossing",
                "c_id": str(client_id),
                "comp_id": str(company_id),
                "tiles": tiles_strs
            })
            
            self.client.send_gamescript(payload)
