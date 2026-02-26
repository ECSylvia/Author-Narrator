import json
import os

class SettingsManager:
    def __init__(self):
        # Store settings in the user's home directory or app data to persist across updates
        self.settings_path = os.path.join(os.path.expanduser("~"), ".author_narrator_settings.json")
        self.settings = {}
        self.load_settings()

    def load_settings(self):
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r') as f:
                    self.settings = json.load(f)
            except Exception as e:
                print(f"Error loading settings: {e}")
                self.settings = {}

    def save_settings(self):
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get_api_key(self):
        return self.settings.get("elevenlabs_api_key", "")

    def set_api_key(self, key):
        self.settings["elevenlabs_api_key"] = key.strip()
        self.save_settings()
