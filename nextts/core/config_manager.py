import json
import os
from cryptography.fernet import Fernet

class ConfigManager:
    DEFAULT_CONFIG_PATH = "config.json"
    _KEY_FILE = ".key"

    def __init__(self, config_path=None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.key = self._load_or_create_key()
        self.fernet = Fernet(self.key)
        self.config = self._load_config()

    def _load_or_create_key(self):
        if os.path.exists(self._KEY_FILE):
            with open(self._KEY_FILE, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self._KEY_FILE, "wb") as f:
                f.write(key)
            return key

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_config(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    def set_api_key(self, provider, api_key):
        encrypted_key = self.fernet.encrypt(api_key.encode()).decode()
        if "api_keys" not in self.config:
            self.config["api_keys"] = {}
        self.config["api_keys"][provider] = encrypted_key
        self.save_config()

    def get_api_key(self, provider):
        encrypted_key = self.config.get("api_keys", {}).get(provider)
        if encrypted_key:
            try:
                return self.fernet.decrypt(encrypted_key.encode()).decode()
            except:
                return ""
        return ""

    def set_setting(self, key, value):
        self.config[key] = value
        self.save_config()

    def get_setting(self, key, default=None):
        return self.config.get(key, default)
