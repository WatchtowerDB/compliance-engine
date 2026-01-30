class SynonymSet:
    """
    A set of synonymous strings used for flexible text matching.

    This class holds a collection of strings that are considered equivalent (synonyms).
    It allows checking if a given word exists in the set in a case-insensitive manner.
    This is useful for validating analysis outputs where multiple terms might refer
    to the same concept (e.g., "CVV", "CVC", "Card Verification Value").
    """

    def __init__(self, *words: str):
        """
        Initialize a set of synonyms.

        Args:
            *words: Variable length argument list of synonym strings.

        Raises:
            TypeError: If any of the provided words are not strings.
        """
        temp: dict[str, str] = {}

        for word in words:
            if not isinstance(word, str):
                raise TypeError(f"Synonyms must be strings. Got {type(word).__name__}.")

            lw = word.lower()
            if lw not in temp:
                temp[lw] = word

        self._synonyms: frozenset[str] = frozenset(temp.values())

    def __contains__(self, word):
        """
        Check if a word is in the synonym set (case-insensitive).

        Args:
            word: The word to check.

        Returns:
            True if the word matches any synonym in the set (ignoring case), False otherwise.
        """
        return any(word.lower() == syn.lower() for syn in self._synonyms)

    def __iter__(self):
        """
        Iterate over the synonyms in the set.

        Yields:
            str: The next synonym in the set.
        """
        return iter(self._synonyms)

    def __len__(self):
        """
        Return the number of unique synonyms in the set.

        Returns:
            int: The count of synonyms.
        """
        return len(self._synonyms)

    def __repr__(self):
        """
        Return a string representation of the SynonymSet for debugging.

        Returns:
            str: A string in the format "SynonymSet(word1, word2, ...)"
        """
        return f"SynonymSet({', '.join(sorted(self._synonyms))})"

    def __str__(self):
        """
        Return a human-readable string description of the synonyms.

        Returns:
            str: A string in the format "Any of ['word1', 'word2', ...]"
        """
        return f"Any of {sorted(self._synonyms)}"
