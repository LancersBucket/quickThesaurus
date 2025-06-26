import json, os, time

class Cache():
	def __init__(self, filename="cache.json", ttl=604800):
		self.filename = filename
		self.ttl = ttl
		self.cache = {}
		if (os.path.exists(self.filename)):
			with open(self.filename, "r") as file:
				self.cache = json.load(file)
		else:
			with open(self.filename, "w") as file:
				file.write("{}")
	
	def check(self, key: str) -> bool:
		if key in self.cache:
			if int(time.time()) - self.cache[key]["valid"] < self.ttl:
				# Cache is valid
				return True
		return False
	
	def get(self, key: str) -> dict | None:
		if self.check(key):
			return self.cache[key]
		return None
	
	def save(self, key: str, value: dict) -> None:
		self.cache[key] = value
		self.write()

	def write(self) -> None:
		for key in self.cache:
			self.cache[key]["valid"] = int(time.time())
		with open(self.filename, "w") as file:
			json.dump(self.cache, file, indent=4)

	def invalidate(self, key: str) -> None:
		if key in self.cache:
			self.cache[key]["valid"] = 0
			self.write()
	
	def purge(self) -> None:
		self.cache = {}
		self.write()