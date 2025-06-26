"""Merriam-Webster Thesaurus Parser"""
from urllib.request import urlopen
import urllib.error
from bs4 import BeautifulSoup

class SynAnt:
    """Thesaurus"""
    def __init__(self, word: str):
        self._word = word
        html = self._get_html(word)
        self._thesaurus = {}

        # Generate html parser and thesaurus if there is no error
        if html is not None:
            self._htmlparser = BeautifulSoup(html, "html.parser")
            self._extract_definitions()

    def _get_html(self, word: str) -> str | None:
        """Get the html from Merriam-Webster"""
        url = f"https://www.merriam-webster.com/thesaurus/{word}"
        # If the webpage isn't valid it isn't a word
        try:
            with urlopen(url) as page:
                html_bytes = page.read()
            return html_bytes.decode("utf-8")
        except urllib.error.URLError:
            return None

    def get_word(self) -> str:
        """Returns the word"""
        return self._word

    def get_thesaurus(self) -> dict:
        """Returns the whole thesaurus"""
        return self._thesaurus

    def _extract_definitions(self) -> None:
        """Extract definitions from the html"""
        # Each subdefinition is located within .sense-content
        for result in self._htmlparser.select("div[class*='sense-content']"):
                        # Extract the "as in" word, this loop should only ever run once
            asin = ""
            for asinwords in result.select("div[class*='as-in-word'] > em"):
                asin = asinwords.get_text(strip=True)
            self._thesaurus[asin] = {}

            # Get the definition related to the "as in" word
            for definition in result.select("span[class*='dt']"):
                definition = definition.get_text("*spl;",strip=True)
                try:
                    definition = definition.split("*spl;")[0]
                except IndexError:
                    pass
                self._thesaurus[asin]["def"] = definition

            # Get all synonyms for this "as in" definition
            synonyms = []
            for symgroup in result.select("span[class*='sim-list-scored']"):
                for sym in symgroup.select("span[class='syl']"):
                    sym = sym.get_text(strip=True)
                    synonyms.append(sym)
            self._thesaurus[asin]["syn"] = synonyms

            # Get all antonyms for this "as in" definition
            antonyms = []
            for antgroup in result.select("span[class*='opp-list-scored']"):
                for ant in antgroup.select("span[class='syl']"):
                    ant = ant.get_text(strip=True)
                    antonyms.append(ant)
            self._thesaurus[asin]["ant"] = antonyms
