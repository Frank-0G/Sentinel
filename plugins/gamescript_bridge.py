from plugin_interface import IPlugin
from openttd_types import NetworkAction
import json

class GameScriptBridge(IPlugin):
    """
    Plugin to act as a bridge between GameScript events and the Python Sentinel Bot.
    Handles generic commands like Chat, IRC messages, Discord messages, etc.
    """
    def __init__(self, client):
        super().__init__(client)
        self.client = client

    def on_gamescript_event(self, event_type, data):
        """
        Handle events from GameScript JSON payloads.
        In SentinelGS, 'event_type' can be the value of 'event' or 'command' in the payload.
        """
        if event_type == "chat":
            msg_type = data.get("type", "public")
            msg_text = data.get("text", "")
            
            # Send message to OpenTTD chat using the client API
            # signature: send_chat(action, desttype, dest_id, message)
            if msg_type == "server":
                c_id = int(data.get("client", 0))
                # Send a private client message (desttype=2) 
                self.client.send_chat(NetworkAction.NETWORK_ACTION_CHAT_CLIENT, 2, c_id, f"[Server] {msg_text}")
            elif msg_type == "public":
                # Send a server broadcast (desttype=0)
                self.client.send_chat(NetworkAction.NETWORK_ACTION_SERVER_MESSAGE, 0, 0, msg_text)
            elif msg_type == "team":
                comp = int(data.get("company", 0))
                # Send a company-wide chat (desttype=1)
                self.client.send_chat(NetworkAction.NETWORK_ACTION_CHAT_COMPANY, 1, comp, msg_text)
        
        elif event_type == "ircmessage":
            # Just broadcast to standard OpenTTD chat, and the IRC Bridge plugin
            # will automatically pick it up (irc_bridge listens to on_chat).
            # If we need direct IRC sending without showing in-game, we'd need
            # cross-plugin communication, but typically sending as server message works.
            msg_text = data.get("text", "")
            # We prefix with [GS] or nothing, depending on preference.
            self.client.send_chat(3, 0, 0, f"[GameScript] {msg_text}")
