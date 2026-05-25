import pytest
import json
from api.analyze import _parse_json

def test_parse_json_valid_only():
    """Test extracting a valid JSON string that contains only the JSON."""
    raw = '{"valid": true, "reason": "ok"}'
    result = _parse_json(raw)
    assert result == {"valid": True, "reason": "ok"}

def test_parse_json_with_surrounding_text():
    """Test extracting a valid JSON string that has text around it."""
    raw = 'Here is the JSON: {"valid": true, "reason": "ok"}\nHope it helps.'
    result = _parse_json(raw)
    assert result == {"valid": True, "reason": "ok"}

def test_parse_json_empty_string():
    """Test with an empty string."""
    assert _parse_json('') == {}

def test_parse_json_no_json_object():
    """Test with a string containing no JSON object."""
    assert _parse_json('There is no json here') == {}

def test_parse_json_malformed():
    """Test with a malformed JSON string. The regex matches it, but json.loads will fail."""
    raw = 'Here is bad json: {"key": value}'
    with pytest.raises(json.decoder.JSONDecodeError):
        _parse_json(raw)
