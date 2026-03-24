import json
import os

def update_triggers():
    path = "triggers.json"
    if not os.path.exists(path):
        print("triggers.json not found")
        return

    with open(path, "r") as f:
        data = json.load(f)

    changed = 0
    for item in data:
        if "discord" not in item:
            # Default to IRC visibility if not present
            item["discord"] = item.get("irc", True)
            changed += 1

    if changed > 0:
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Updated {changed} triggers with 'discord' flag.")
    else:
        print("No changes needed.")

if __name__ == "__main__":
    update_triggers()
