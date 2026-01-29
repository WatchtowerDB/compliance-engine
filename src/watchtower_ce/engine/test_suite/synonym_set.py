class SynonymSet:
    def __init__(self, *words: str):
        temp: dict[str, str] = {}

        for word in words:
            if not isinstance(word, str):
                raise TypeError(f"Synonyms must be strings. Got {type(word).__name__}.")

            lw = word.lower()
            if lw not in temp:
                temp[lw] = word

        self._synonyms: frozenset[str] = frozenset(temp.values())

    def __contains__(self, word):
        return any(word.lower() == syn.lower() for syn in self._synonyms)

    def __iter__(self):
        return iter(self._synonyms)

    def __len__(self):
        return len(self._synonyms)

    def __repr__(self):
        return f"SynonymSet({', '.join(sorted(self._synonyms))})"

    def __str__(self):
        return f"Any of {sorted(self._synonyms)}"
