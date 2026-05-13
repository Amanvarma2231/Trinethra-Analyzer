import json
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def extract_json_from_response(text: str) -> Optional[Dict[str, Any]]:
    """
    Extracts JSON from an LLM response string.
    Handles markdown code blocks and raw JSON.
    """
    if not text:
        return None
        
    # Try to find JSON in code blocks
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_match:
        text = json_match.group(1)
    
    # Try parsing directly
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        # Try to find anything that looks like a JSON object or array
        try:
            match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
            if match:
                return json.loads(match.group(1))
        except:
            pass
            
    logger.error(f"Failed to extract JSON from response: {text[:200]}...")
    return None

def validate_evidence(data: Dict[str, Any]) -> bool:
    """Validates the structure of evidence extraction output."""
    if not isinstance(data, dict) or "evidence" not in data:
        return False
    if not isinstance(data["evidence"], list):
        return False
    return True

def validate_score(data: Dict[str, Any]) -> bool:
    """Validates the structure of scoring output."""
    if not isinstance(data, dict) or "score" not in data:
        return False
    try:
        score = float(data["score"])
        return 1 <= score <= 10
    except:
        return False

def safe_json_response(data: Any, default: Any = None) -> Any:
    """Ensures data is JSON serializable."""
    try:
        json.dumps(data)
        return data
    except:
        return default
