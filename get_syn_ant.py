from urllib.request import urlopen
from bs4 import BeautifulSoup

class SynAnt:
	def __init__(self, word):
		self._word = word
		self._htmlparser = BeautifulSoup(self._get_html(word), "html.parser")

		self._thesaurus = {}
		self._extract_definitions()

	def _get_html(self, word):
		url = f"https://www.merriam-webster.com/thesaurus/{word}"
		page = urlopen(url)
		html_bytes = page.read()
		return html_bytes.decode("utf-8")
	
	def get_word(self):
		return self._word

	def get_thesaurus(self):
		return self._thesaurus
	
	def _extract_definitions(self):
		for result in self._htmlparser.select("div[class*='sense-content']"):
			asin = ""
			for asinwords in result.select("div[class*='as-in-word'] > em"):
				asin = asinwords.get_text(strip=True)
			self._thesaurus[asin] = {}
		
			for definition in result.select("span[class*='dt']"):
				definition = definition.get_text(strip=True)
				self._thesaurus[asin]["def"] = definition

			synonyms = []
			for symgroup in result.select("span[class*='sim-list-scored']"):
				for sym in symgroup.select("span[class='syl']"):
					sym = sym.get_text(strip=True)
					synonyms.append(sym)
			self._thesaurus[asin]["syn"] = synonyms

			antonyms = []
			for antgroup in result.select("span[class*='opp-list-scored']"):
				for ant in antgroup.select("span[class='syl']"):
					ant = ant.get_text(strip=True)
					antonyms.append(ant)
			self._thesaurus[asin]["ant"] = antonyms