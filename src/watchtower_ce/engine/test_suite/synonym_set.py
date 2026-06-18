class SynonymSet:
    """
    A set of synonymous strings used for flexible text matching.

    Holds a collection of strings considered equivalent (e.g. "CVV", "CVC",
    "Card Verification Value"). Matching is always case-insensitive.
    """

    def __init__(self, *words: str):
        """
        Initialize a set of synonyms.

        Args:
            *words: Synonym strings. Duplicates (case-insensitive) are deduplicated,
                    keeping the first occurrence's casing.

        Raises:
            TypeError: If any argument is not a string.
        """
        seen: dict[str, str] = {}

        for word in words:
            if not isinstance(word, str):
                raise TypeError(f"Synonyms must be strings, got {type(word).__name__}.")

            lw = word.lower()
            if lw not in seen:
                seen[lw] = word

        self._synonyms: frozenset[str] = frozenset(seen.values())

    def __contains__(self, word: object) -> bool:
        """
        Check if a word is in the synonym set (case-insensitive).

        Args:
            word: The word to check.

        Returns:
            True if the word matches any synonym in the set (ignoring case), False otherwise.
        """
        if not isinstance(word, str):
            return False
        return any(word.lower() == s.lower() for s in self._synonyms)

    def __iter__(self):
        """
        Iterate over the synonyms in the set.

        Yields:
            str: The next synonym in the set.
        """
        return iter(self._synonyms)

    def __len__(self) -> int:
        """
        Return the number of unique synonyms in the set.

        Returns:
            int: The count of synonyms.
        """
        return len(self._synonyms)

    def __repr__(self) -> str:
        """
        Return a string representation of the SynonymSet for debugging.

        Returns:
            str: A string in the format "SynonymSet(word1, word2, ...)"
        """
        return f"SynonymSet({', '.join(sorted(self._synonyms))})"

    def __str__(self) -> str:
        """
        Return a human-readable string description of the synonyms.

        Returns:
            str: A string in the format "Any of ['word1', 'word2', ...]"
        """
        return f"Any of {sorted(self._synonyms)}"


# Type alias used throughout the benchmark suite.
Phrase = str | SynonymSet
