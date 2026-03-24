import json
import os

print("Resetting triggers.json to include !ts and !g aliases...")

triggers = [
    # --- GOAL SYSTEM (PUBLIC) ---
    {
        "name": "goal",
        "admin": False,
        "irc": True,
        "in_game": True,
        "description": "Shows the current scoreboard and goal progress.",
        "aliases": ["g", "cv"], 
        "response": None 
    },
    {
        "name": "progress",
        "admin": False,
        "irc": True,
        "in_game": True,
        "description": "Displays a visual progress bar of the leading company.",
        "aliases": ["prog"],
        "response": None
    },
    {
        "name": "townstats",
        "admin": False,
        "irc": True,
        "in_game": True,
        "description": "Displays CityBuilder town requirements for a specific company.",
        "aliases": ["ts", "town"],
        "response": None
    },
    {
        "name": "claimed",
        "admin": False,
        "irc": True,
        "in_game": True,
        "description": "Lists all currently claimed towns and their owners.",
        "aliases": ["claims"],
        "response": None
    },

    # --- GOAL SYSTEM (ADMIN) ---
    {
        "name": "goalreached",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Forces the current game to end and declares the leader as winner.",
        "response": None
    },
    {
        "name": "awarning",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Issues a warning message to a specific company.",
        "response": None
    },

    # --- STANDARD PUBLIC COMMANDS ---
    {
        "name": "help",
        "admin": False,
        "irc": True,
        "in_game": True,
        "description": "Shows help information.",
        "aliases": ["commands"],
        "response": None
    },
    {
        "name": "rules",
        "admin": False,
        "irc": True,
        "in_game": True,
        "description": "Shows server rules.",
        "response": "Rules: 1. Be nice. 2. No blocking. 3. Have fun!"
    },
    {
        "name": "status",
        "admin": False,
        "irc": True,
        "in_game": True,
        "description": "Shows server status (players, companies, year).",
        "response": None
    },
    {
        "name": "server",
        "admin": False,
        "irc": True,
        "in_game": True,
        "description": "Shows server name.",
        "response": None
    },
    {
        "name": "players",
        "admin": False,
        "irc": True,
        "in_game": True,
        "description": "Lists connected players.",
        "response": None
    },
    {
        "name": "companies",
        "admin": False,
        "irc": True,
        "in_game": True,
        "description": "Lists active companies.",
        "response": None
    },
    {
        "name": "vote",
        "admin": False,
        "irc": False,
        "in_game": True,
        "description": "Cast a YES vote.",
        "aliases": ["yes"],
        "response": None
    },
    {
        "name": "votekick",
        "admin": False,
        "irc": False,
        "in_game": True,
        "description": "Start a vote to kick a player.",
        "response": None
    },
    {
        "name": "voteban",
        "admin": False,
        "irc": False,
        "in_game": True,
        "description": "Start a vote to ban a player.",
        "response": None
    },
    {
        "name": "voterestart",
        "admin": False,
        "irc": False,
        "in_game": True,
        "description": "Start a vote to restart the map.",
        "response": None
    },
    {
        "name": "votereset",
        "admin": False,
        "irc": False,
        "in_game": True,
        "description": "Start a vote to reset a company.",
        "response": None
    },
    {
        "name": "resetme",
        "admin": False,
        "irc": False,
        "in_game": True,
        "description": "Flag your own company for reset.",
        "response": None
    },
    {
        "name": "limits",
        "admin": False,
        "irc": True,
        "in_game": True,
        "description": "Show server limits.",
        "response": None
    },
    {
        "name": "seed",
        "admin": False,
        "irc": True,
        "in_game": True,
        "description": "Show map seed.",
        "response": None
    },
    {
        "name": "screenshot",
        "admin": False,
        "irc": False,
        "in_game": True,
        "description": "Take a screenshot of a location.",
        "response": None
    },
    {
        "name": "alogin",
        "admin": False,
        "irc": False,
        "in_game": True,
        "description": "Login as admin.",
        "response": None
    },
    
    # --- STANDARD ADMIN COMMANDS ---
    {
        "name": "say",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Speak as server.",
        "response": None
    },
    {
        "name": "rcon",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Execute console command.",
        "response": None
    },
    {
        "name": "kick",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Kick a player.",
        "response": None
    },
    {
        "name": "ban",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Ban a player.",
        "response": None
    },
    {
        "name": "move",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Move a player to a company.",
        "response": None
    },
    {
        "name": "reset",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Reset a company immediately.",
        "response": None
    },
    {
        "name": "empty",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Empty a company (move players to spec).",
        "response": None
    },
    {
        "name": "lockcompany",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Lock a company with password.",
        "response": None
    },
    {
        "name": "unlockcompany",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Remove password from a company.",
        "response": None
    },
    {
        "name": "pause",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Pause the game.",
        "response": None
    },
    {
        "name": "unpause",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Unpause the game.",
        "response": None
    },
    {
        "name": "shutdown",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Shutdown the server.",
        "response": None
    },
    {
        "name": "restart",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Restart the server/Sentinel.",
        "response": None
    },
    {
        "name": "news",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Post a news item.",
        "response": None
    },
    {
        "name": "cancelvote",
        "admin": True,
        "irc": True,
        "in_game": True,
        "description": "Cancel any active vote.",
        "response": None
    }
]

file_path = os.path.join(os.path.dirname(__file__), "triggers.json")

try:
    with open(file_path, "w") as f:
        json.dump(triggers, f, indent=4)
    print(f"Success! triggers.json has been generated at {file_path}")
    print(f"Aliases added: ts -> townstats, g -> goal")
except Exception as e:
    print(f"Error writing file: {e}")
