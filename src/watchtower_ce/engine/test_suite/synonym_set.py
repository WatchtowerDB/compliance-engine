class SynonymSet:
    def __init__(self, *words: str):
        temp: set[str] = set()

        for word in words:
            if not isinstance(word, str):
                raise TypeError("Synonyms must be strings")
            if word.lower() not in temp:
                temp.add(word)

        self._synonyms: frozenset[str] = frozenset(temp)

    def __contains__(self, word):
        return word.lower() in self._synonyms

    def __iter__(self):
        return iter(self._synonyms)

    def __len__(self):
        return len(self._synonyms)

    def __repr__(self):
        return f"SynonymSet({', '.join(sorted(self._synonyms))})"

    def __str__(self):
        return f"Any of {sorted(self._synonyms)}"
