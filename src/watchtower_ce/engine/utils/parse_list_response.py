import logging

from json_repair import repair_json

logger = logging.getLogger(__name__)


def parse_list_response(response: str) -> list[str]:
    """
    Parse a response string that should contain a JSON list of strings.

    Args:
        response (str): The response string to parse, potentially containing markdown formatting

    Returns:
        list[str]: A list of strings extracted from the response

    Raises:
        ValueError: If json-repair cannot parse the response into a list.
    """
    logger.debug("Raw list response: %s", repr(response))

    # Clean up potential markdown formatting
    cleaned_response = response.strip()
    cleaned_response = cleaned_response.replace("\n", " ")
    if cleaned_response.startswith("```python3"):
        cleaned_response = cleaned_response[10:]
    elif cleaned_response.startswith("```python"):
        cleaned_response = cleaned_response[9:]
    elif cleaned_response.startswith("```py"):
        cleaned_response = cleaned_response[5:]
    elif cleaned_response.startswith("```json"):
        cleaned_response = cleaned_response[7:]
    elif cleaned_response.startswith("```sql"):
        cleaned_response = cleaned_response[6:]
    elif cleaned_response.startswith("```"):
        cleaned_response = cleaned_response[3:]

    if cleaned_response.endswith("```"):
        cleaned_response = cleaned_response[:-3]

    cleaned_response = cleaned_response.strip()

    try:
        repaired_items = repair_json(cleaned_response, return_objects=True)
        if isinstance(repaired_items, list):
            normalized_items = [str(item) for item in repaired_items]
            logger.debug(
                "Successfully parsed %s items",
                len(normalized_items),
            )
            return normalized_items
        raise ValueError("json-repair did not produce a list response.")
    except (ValueError, TypeError) as repair_error:
        logger.warning(
            "Failed to parse list response: %s",
            repair_error,
        )
        logger.warning("Raw response: %s", repr(response))
        raise ValueError("Failed to parse list response") from repair_error
