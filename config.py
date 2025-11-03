"""Configuration r/w"""
import json, os

class Config:
    """Configuration Handler"""
    default_config = {
        "offset": [23, 0],
        "window_size": [525, 800],
        "alignment": "right",
        "close_on_copy": True,
        "show_synonyms": True,
        "show_antonyms": True,
    }

    def __init__(self, filename="config.json") -> None:
        self.filename = filename
        if os.path.exists(self.filename):
            with open(self.filename, "r", encoding="UTF-8") as file:
                self.config = json.load(file)
            self.validate_keys()
        else:
            with open(self.filename, "w", encoding="UTF-8") as file:
                json.dump(self.default_config, file, indent=4)

    def validate_keys(self) -> None:
        """Validates all default keys exist in the config, adding them if not"""
        for key, default_value in self.default_config.items():
            if key not in self.config:
                self.config[key] = default_value
        self.write()

    def set_default(self) -> None:
        """Reset config to default values"""
        with open(self.filename, "w", encoding="UTF-8") as file:
            json.dump(self.default_config, file, indent=4)
        self.config = self.default_config.copy()

    # R+W Config #
    def check(self, key: str) -> bool:
        """Check if a key exists in the config"""
        if key in self.config:
            return True
        return False
    def get_bool(self, key: str) -> bool:
        """Get the key from the config"""
        if self.check(key):
            return self.config[key]
        return self.default_config[key]
    def get_list(self, key: str) -> list[int]:
        """Get the key from the config"""
        if self.check(key):
            return self.config[key]
        return self.default_config[key]
    def get(self, key: str):
        """Get the key from the config"""
        if self.check(key):
            return self.config[key]
        return self.default_config[key]
    def save(self, key: str, value, save_to_disk=True) -> None:
        """Save a config value, optionally writing to disk"""
        self.config[key] = value
        if save_to_disk:
            self.write()
    def write(self) -> None:
        """Write the data to config"""
        with open(self.filename, "w", encoding="UTF-8") as file:
            json.dump(self.config, file, indent=4)
