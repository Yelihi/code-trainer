"""READ answers compare primitive values, independently of output layout."""
import json
import re
from decimal import Decimal, InvalidOperation


def values(text):
    tokens = re.findall(r'"(?:[^"\\]|\\.)*"|[^\s,]+', text.strip())
    result = []
    for token in tokens:
        if token.lower() in ('true', 'false'):
            result.append(('bool', token.lower()))
        elif token in ('null', 'None', 'undefined', 'NaN', 'Infinity', '-Infinity'):
            result.append(('literal', 'null' if token == 'None' else token))
        else:
            try:
                value = json.loads(token, parse_int=Decimal, parse_float=Decimal)
            except (ValueError, InvalidOperation, RecursionError):
                return None
            if isinstance(value, str):
                result.append(('string', value))
            elif isinstance(value, Decimal):
                result.append(('number', value))
            else:
                return None
    return result or None


def matches(answer, expected):
    expected_values = values(expected)
    if expected_values is not None:
        return values(answer) == expected_values
    # Legacy text exercises still compare their words in order.
    return answer.split() == expected.split()
