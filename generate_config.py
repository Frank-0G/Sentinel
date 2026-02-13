import os

# This string contains the raw XML configuration with all comments.
# Using a raw string (r"...") prevents any processing of the text until it's written to the file.
xml_content = r"""<config>
    <server_id>99</server_id>

    <admin_host>127.0.0.1</admin_host>
    <admin_port>9901</admin_port>
    <admin_password>FR-JJ-GE2011</admin_password>

    <screenshot_path>../../../screenshots</screenshot_path>
    <screenshot_url>https://openttd.btpro.nl/screenshots</screenshot_url>
    
    <executable>/home/openttd/Servers/Production/OpenTTD-AdminPort/openttd</executable>
    <config_file>/home/openttd/Servers/Production/OpenTTD-AdminPort/configs/Server99/Server99.cfg</config_file>
    <extra_args>-D -d script=5 -b 8bpp-optimized</extra_args>
    <launch_wait>15</launch_wait>

    <irc_enabled>true</irc_enabled>
    <irc_server>hub.irc.boxor.net</irc_server>
    <irc_port>6668</irc_port>
    <irc_ssl>false</irc_ssl>
    <irc_channel>#btpro-srv99</irc_channel>
    <irc_nickname>ttd-srv99</irc_nickname>

    <trigger_prefix>!</trigger_prefix>
    <trigger_file>triggers.json</trigger_file>

    <auto_restart_minutes>60</auto_restart_minutes>
    
    <chat_log_retention_days>365</chat_log_retention_days>
    
    <chat_db_config>
        <host>localhost</host>
        <user>openttd</user>
        <password>TaBVH9DFPJNDvrdH</password>
        <database>BTPro-Chatlog</database>
    </chat_db_config>

    <mysql_config>
        <host>localhost</host>
        <user>openttd</user>
        <password>TaBVH9DFPJNDvrdH</password>
        <database>openttd</database>
        <port>3306</port>
        <autocommit>true</autocommit>
    </mysql_config>

    <welcome_message>
        <public>Welcome to the BTPro.nl Playground, {name} from {country}.</public>
        
        <private>
            <line>This is a GOAL server. press enter and type !help for commands.</line>
            <line>-=-=-=-=</line>
            <line>TO DISPLAY OUR COMMUNITY HIGHSCORES, USE TRIGGER: !highscore</line>
            <line>If you are a registered player, we can record your scores in our database!</line>
            <line>To register, please visit our website: https://openttd.btpro.nl</line>
            <line>-=-=-=-=-=-=-=-=</line>
            <line>SERVER RULES --- https://openttd.btpro.nl --- SERVER RULES (or type !rules)</line>
            <line>-=-=-=-=-=-=-=-=-=-=-=-=</line>
        </private>
    </welcome_message>
</config>
"""

output_file = "controller_config.xml"

try:
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(xml_content.strip())
    print(f"[Success] '{output_file}' has been generated. Open it in a text editor to see all comments.")
except Exception as e:
    print(f"[Error] Failed to write file: {e}")
