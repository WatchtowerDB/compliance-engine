import re

from .synonym_set import Phrase, SynonymSet

_WORD_RE = re.compile(r"[a-z0-9]+")
_CITATION_START_RE = re.compile(r"\b(?:article|req(?:uirement)?)\b", re.IGNORECASE)
_NUMBER_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)")
_PAREN_RE = re.compile(r"^\s*\(\s*([a-z0-9]+)\s*\)")
_CLAUSE_RE = re.compile(r"^\s*,\s*clause\s+([a-z0-9]+)")


def _normalize_text(text: str) -> str:
    return " ".join(_WORD_RE.findall(text.lower()))


def _extract_citation_from_line(line: str) -> str | None:
    """
    Parse a single citation from a line of text.

    Returns the citation path as a normalized string, e.g.
    - "9 1"
    - "5 1 e"
    - "3 5"
    """
    match = _CITATION_START_RE.search(line)
    if match is None:
        return None

    tail = line[match.end() :]
    number_match = _NUMBER_RE.match(tail)
    if number_match is None:
        return None

    tokens = [number_match.group(1)]
    tail = tail[number_match.end() :]

    while tail:
        paren_match = _PAREN_RE.match(tail)
        if paren_match is not None:
            tokens.append(paren_match.group(1).lower())
            tail = tail[paren_match.end() :]
            continue

        clause_match = _CLAUSE_RE.match(tail)
        if clause_match is not None:
            tokens.append(clause_match.group(1).lower())
            tail = tail[clause_match.end() :]
            continue

        break

    return " ".join(tokens)


def _citation_signatures(text: str) -> set[str]:
    """Extract citation-path signatures from text line by line."""
    signatures: set[str] = set()
    for line in text.splitlines():
        signature = _extract_citation_from_line(line)
        if signature is not None:
            signatures.add(signature)
    return signatures


def _requirement_signatures(requirement: str) -> set[str]:
    """Build normalized signatures for one requirement citation."""
    signature = _extract_citation_from_line(requirement)
    if signature is not None:
        return {signature}
    return {_normalize_text(requirement)}


def _matches_phrase(text_lower: str, phrase: Phrase) -> bool:
    """Return True if `phrase` is present in `text_lower`."""
    if isinstance(phrase, SynonymSet):
        return phrase.appears_in(text_lower)
    return phrase.lower() in text_lower


def _matches_step(text_lower: str, step: Phrase) -> bool:
    """
    Keyword-overlap match for remediation steps.
    A step is considered present if >= 60% of its meaningful words appear.
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
    Return True if at least one expected requirement citation appears in `text`.

    Matching is ancestor-aware at the citation-path level:
    - `Article 5(1)` matches `Article 5(1)(e)`
    - `Article 5(1)(e)` does not match `Article 5(1)`
    - markdown, bullets, bolding, and punctuation are ignored
    """
    text_signatures = _citation_signatures(text)

    for req in requirements:
        for req_sig in _requirement_signatures(req):
            for sig in text_signatures:
                if sig == req_sig or sig.startswith(req_sig + " "):
                    return True
    return False
