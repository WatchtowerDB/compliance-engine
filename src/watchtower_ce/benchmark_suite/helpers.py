from .synonym_set import Phrase, SynonymSet


def _matches_phrase(text_lower: str, phrase: Phrase) -> bool:
    """Return True if `phrase` is present in `text_lower`."""
    if isinstance(phrase, SynonymSet):
        return phrase.appears_in(text_lower)
    return phrase.lower() in text_lower


def _matches_step(text_lower: str, step: Phrase) -> bool:
    """
    Keyword-overlap match for remediation steps.
    A step is considered present if ≥ 60% of its meaningful words appear.
    """

    def _step_present(step_str: str) -> bool:
        keywords = [w for w in step_str.lower().split() if w != "/" and len(w) > 2]

        if not keywords:
            return False

        hits = sum(1 for kw in keywords if kw in text_lower)
        return hits >= len(keywords) * 0.6

    if isinstance(step, SynonymSet):
        return any(_step_present(synonym) for synonym in step)
    return _step_present(step)


def _check_requirement_identified(text: str, requirements: list[str]) -> bool:
    """
    Return True if at least one expected requirement string appears in `text`.
    Normalises "Req 3.4", "Requirement 3.4", "3.4", "Article 9", etc.
    """
    text_lower = text.lower()
    for req in requirements:
        bare = (
            req.lower()
            .replace("requirement", "")
            .replace("req.", "")
            .replace("req", "")
            .replace("article", "")
            .strip()
        )
        variants = [
            req.lower(),
            f"req {bare}",
            f"req. {bare}",
            f"requirement {bare}",
            f"article {bare}",
            bare,
        ]
        if any(v in text_lower for v in variants):
            return True
    return False
