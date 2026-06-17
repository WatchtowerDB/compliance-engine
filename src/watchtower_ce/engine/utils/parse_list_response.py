import json
import logging

logger = logging.getLogger(__name__)


def parse_list_response(response: str, fallback_item_limit: int = 6) -> list[str]:
    """
    Parse a response string that should contain a JSON list of strings.

    Args:
        response (str): The response string to parse, potentially containing markdown formatting
        fallback_item_limit (int): Maximum number of items to return when using fallback parsing

    Returns:
        list[str]: A list of strings extracted from the response
    """
    logger.debug("Raw list response: %s", repr(response))

    try:
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

        items = json.loads(cleaned_response)

        if not isinstance(items, list):
            raise ValueError("Response is not a valid list.")

        logger.debug("Successfully parsed %s items from JSON", len(items))
        return items

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse response as JSON: %s", e)
        logger.warning("Raw response: %s", repr(response))

        # Fallback: extract items from text (one per line)
        lines = response.strip().split("\n")
        items = []

        for line in lines:
            cleaned_line = line.strip(" -\"[]'")
            # Only include non-empty lines with reasonable content
            if cleaned_line and len(cleaned_line) > 10:
                items.append(cleaned_line)

        # Limit to fallback_item_limit if we have too many items
        if len(items) > fallback_item_limit:
            items = items[:fallback_item_limit]
            logger.debug("Extracted and limited to %s items from text", len(items))
        else:
            logger.debug("Extracted %s items from text", len(items))

        return items
