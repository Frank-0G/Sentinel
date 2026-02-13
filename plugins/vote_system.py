import time
import math
from plugin_interface import IPlugin

class VoteSystem(IPlugin):
    """
    Implements a custom VoteSystem.
    
    Commands:
      !vote <type> [args]
      !yes, !no
    """
    def __init__(self, client):
        super().__init__(client)
        self.name = "VoteSystem"
        self.version = "2.0-SENTINEL"
        
        # Configuration
        self.config = {
            "vote_duration": 60,     # Time in seconds
            "pass_percentage": 51,   # % of YES votes needed to pass
            "min_votes": 2,          # Minimum valid votes to count
            "cooldown": 180,         # Seconds between votes
            "allowed_types": ["restart", "reset", "loading", "exec"] 
        }

        self.active_vote = None 
        # Structure:
        # { 
        #   'type': 'kick', 
        #   'target_id': 5, 
        #   'target_name': 'PlayerName',
        #   'initiator': 'Admin',
        #   'start_time': timestamp, 
        #   'voters': set()  # Set of Client IDs who voted YES
        # }

    def get_session(self):
        return self.client.get_service("OpenttdSession")

    def get_data(self):
        return self.client.get_service("DataController")

    def on_tick(self):
        if not self.active_vote:
            return

        # 1. Calculate Statistics
        data = self.get_data()
        if not data: return

        # Count "Real" players (exclude server client #1 if present, though DataController usually handles this)
        # Uses internal player count logic
        # Sentinel DataController.clients includes everyone.
        
        online_players = [cid for cid in data.clients if cid != 1] # Exclude server ID 1
        total_players = len(online_players)
        
        # If players dropped below minimum, cancel
        if total_players < self.min_players:
            self.cancel_vote("Not enough players on server.")
            return

        current_votes = len(self.active_vote['voters'])
        
        # Calculate Ratio
        ratio = 0.0
        if total_players > 0:
            ratio = current_votes / total_players

        # 2. Check Expiration
        elapsed = time.time() - self.active_vote['start_time']
        is_expired = elapsed >= self.vote_duration

        # 3. Decision Logic (Mimic VoteSystem.cs onVoteCheckTimerTick)
        # If ratio met OR time expired, we finalize
        if is_expired or ratio >= self.vote_ratio:
            if ratio >= self.vote_ratio and total_players >= self.min_players:
                self._pass_vote()
            else:
                if is_expired:
                    self._fail_vote("Time expired.")

    # --- ACTIONS ---

    def start_vote(self, vote_type, target_arg, target_name_resolved, initiator_name, initiator_cid):
        """
        Starts a vote.
        vote_type: 'kick', 'ban', 'restart', 'reset'
        target_arg: The ID to kick/ban (or company ID)
        """
        if self.active_vote:
            return False, "A vote is already in progress."

        # Cooldown check
        if time.time() < self.last_vote_time + self.cooldown:
            rem = int((self.last_vote_time + self.cooldown) - time.time())
            return False, f"Vote cooldown active. Wait {rem} seconds."

        # Setup Vote
        self.active_vote = {
            "type": vote_type,
            "target_id": target_arg,
            "target_name": target_name_resolved,
            "initiator": initiator_name,
            "start_time": time.time(),
            "voters": {initiator_cid} # Initiator automatically votes yes
        }

        # Announce
        s = self.get_session()
        if s:
            s.send_server_message(f"Vote started by {initiator_name}: {vote_type.upper()} {target_name_resolved}")
            s.send_server_message("Type !vote to agree.")
        
        # Run an immediate tick check (in case 1/1 players = instant pass)
        self.on_tick()
        
        return True, "Vote started."

    def cast_vote(self, client_id, client_name):
        """Called when user types !vote"""
        if not self.active_vote:
            return "No vote active."
        
        if client_id in self.active_vote['voters']:
            return "You have already voted."
            
        self.active_vote['voters'].add(client_id)
        
        # Run immediate check to see if this vote finished it
        self.on_tick()
        
        return "Vote accepted."

    def cancel_vote(self, reason="Cancelled"):
        if not self.active_vote: return
        s = self.get_session()
        if s: s.send_server_message(f"Vote Cancelled: {reason}")
        self.active_vote = None

    def get_status(self):
        if not self.active_vote: return "No active vote."
        data = self.get_data()
        online = len([c for c in data.clients if c!=1]) if data else 1
        votes = len(self.active_vote['voters'])
        elapsed = int(time.time() - self.active_vote['start_time'])
        rem = self.vote_duration - elapsed
        return f"Vote: {self.active_vote['type']} | Yes: {votes}/{online} | Time left: {rem}s"

    # --- INTERNALS ---

    def _pass_vote(self):
        s = self.get_session()
        if not s: return

        vtype = self.active_vote['type']
        target = self.active_vote['target_id']
        name = self.active_vote['target_name']
        
        s.send_server_message(f"Vote Passed! Executing {vtype} on {name}...")
        
        # Execute Action
        if vtype == 'kick':
            s.kick_player(target, "Vote Kicked")
        elif vtype == 'ban':
            s.ban_player(target, "Vote Banned")
        elif vtype == 'restart':
            s.restart_game()
        elif vtype == 'reset':
            # Company reset usually requires 1-based index in commands, 
            # but internal logic uses 0-based often. 
            # Sentinel CommandManager passes the raw int. 
            # Assuming 'target' is the raw ID passed.
            try:
                # ResetCompany usually takes company ID
                s.reset_company(int(target) - 1) 
            except: pass

        self.last_vote_time = time.time()
        self.active_vote = None

    def _fail_vote(self, reason):
        s = self.get_session()
        if s: s.send_server_message(f"Vote Failed: {reason}")
        self.last_vote_time = time.time()
        self.active_vote = None
