"""Cache Handler"""
import json, os, time

class Cache:
    """Cache Handler"""
    def __init__(self, filename="cache.json", ttl=604800):
        self.filename = filename

        # TTL is currently set to 1 week, although I'm not sure what would be a better value
        self.ttl = ttl

        self.cache = {}
        # If the cache already exists, pull it, otherwise create it
        if os.path.exists(self.filename):
            with open(self.filename, "r", encoding="UTF-8") as file:
                self.cache = json.load(file)
        else:
            with open(self.filename, "w", encoding="UTF-8") as file:
                file.write("{}")

    # R+W Cache #
    def check(self, key: str) -> bool:
        """Check if a key exists in the cache"""
        if key in self.cache:
            if int(time.time()) - self.cache[key]["valid"] < self.ttl:
                # Cache is valid
                return True
        return False
    def get(self, key: str) -> dict | None:
        """Get the key from the cache"""
        if self.check(key):
            return self.cache[key]
        return None
    def save(self, key: str, value: dict, save_to_disk=True) -> None:
        """Save a cache value, optionally writing to disk"""
        self.cache[key] = value
        if save_to_disk:
            self.write()
    def write(self, ttl_update=True) -> None:
        """Write the data to cache, adding a ttl value"""
        if ttl_update:
            for key in self.cache:
                self.cache[key]["valid"] = int(time.time())
        with open(self.filename, "w", encoding="UTF-8") as file:
            json.dump(self.cache, file, indent=4)
    def purge(self, invalid_only=False) -> None:
        """Purge cache, optionally only discard invalid entries"""
        newcache = self.cache.copy()
        if invalid_only:
            # Loop over each key, and if check returns False, we know it's invalid, so delete it
            for key in self.cache:
                if not self.check(key):
                    del newcache[key]
            self.cache = newcache
        else:
            # Otherwise just clear the whole list
            self.cache = {}

        self.write(ttl_update=False)

    # Cache Validation #
    def invalidate(self, key: str) -> None:
        """Invalidate cache for a specific entry"""
        if key in self.cache:
            self.cache[key]["valid"] = 0
            self.write(ttl_update=False)
    def invalidate_all(self) -> None:
        """Invalidate cache for all entries"""
        for key in self.cache:
            self.cache[key]["valid"] = 0
        self.write(ttl_update=False)
    def revalidate(self, key: str) -> None:
        """Revalidate cache for a specific entry"""
        if key in self.cache:
            self.cache[key]["valid"] = self.ttl
            self.write(ttl_update=False)
    def revalidate_all(self) -> None:
        """Revalidate cache for all entries"""
        for key in self.cache:
            self.cache[key]["valid"] = self.ttl
        self.write(ttl_update=False)

    # Cache Information #
    def size(self) -> str:
        """Returns the size of the cache file"""
        output = ""
        size = os.path.getsize(self.filename)
        if size >= 1000000:
            output = f"{size/1000000} MB"
        elif size >= 1000:
            output = f"{size/1000} KB"
        else:
            output = f"{size} bytes"

        return output
    def count(self) -> tuple[int, int]:
        """Returns total count, and invalid count of entries."""
        total = 0
        invalid = 0
        for key in self.cache:
            total += 1
            if not self.check(key):
                invalid += 1

        return total, invalid
