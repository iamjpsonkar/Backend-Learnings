"""
lab-runner/validators/http_validator.py — HTTP/API validation helpers
"""

import sys
import time
import urllib.request
import urllib.error
import json


def http_status(url: str, expected_status: int = 200, timeout: int = 10) -> tuple[bool, str]:
    """Check that a URL returns the expected HTTP status code."""
    try:
        req = urllib.request.urlopen(url, timeout=timeout)
        status = req.status
        passed = status == expected_status
        return passed, f"GET {url} returned {status} (expected {expected_status})"
    except urllib.error.HTTPError as e:
        passed = e.code == expected_status
        return passed, f"GET {url} returned {e.code} (expected {expected_status})"
    except urllib.error.URLError as exc:
        return False, f"GET {url} failed: {exc.reason}"
    except Exception as exc:
        return False, f"GET {url} error: {exc}"


def http_body_contains(url: str, pattern: str, timeout: int = 10) -> tuple[bool, str]:
    """Check that an HTTP response body contains a pattern."""
    try:
        req = urllib.request.urlopen(url, timeout=timeout)
        body = req.read().decode("utf-8", errors="replace")
        found = pattern in body
        return found, f"Pattern '{pattern}' {'found' if found else 'not found'} in {url}"
    except Exception as exc:
        return False, f"HTTP body check failed for {url}: {exc}"


def wait_for_http(url: str, max_wait: int = 60, interval: int = 3) -> tuple[bool, str]:
    """Wait for an HTTP endpoint to become available."""
    start = time.time()
    while time.time() - start < max_wait:
        try:
            urllib.request.urlopen(url, timeout=5)
            return True, f"{url} is reachable"
        except Exception:
            time.sleep(interval)
    return False, f"{url} not reachable after {max_wait}s"


def json_field_equals(url: str, field_path: str, expected: str, timeout: int = 10) -> tuple[bool, str]:
    """
    Check that a JSON response field equals an expected value.
    field_path uses dot notation: e.g. "status" or "data.health"
    """
    try:
        req = urllib.request.urlopen(url, timeout=timeout)
        data = json.loads(req.read().decode())
        value = data
        for key in field_path.split("."):
            value = value.get(key) if isinstance(value, dict) else None
        passed = str(value) == str(expected)
        return passed, f"Field '{field_path}' = '{value}' (expected '{expected}')"
    except Exception as exc:
        return False, f"JSON field check failed: {exc}"


if __name__ == "__main__":
    """CLI: python3 http_validator.py <check> <url> [arg]"""
    if len(sys.argv) < 3:
        print("Usage: http_validator.py <check> <url> [arg]", file=sys.stderr)
        sys.exit(1)

    check = sys.argv[1]
    url = sys.argv[2]
    arg = sys.argv[3] if len(sys.argv) > 3 else None

    checks = {
        "status": lambda u, a: http_status(u, int(a) if a else 200),
        "body-contains": lambda u, a: http_body_contains(u, a),
        "wait": lambda u, a: wait_for_http(u, int(a) if a else 60),
        "json-field": lambda u, a: json_field_equals(u, a.split("=")[0], a.split("=")[1]) if a and "=" in a else (False, "format: field=value"),
    }

    fn = checks.get(check)
    if fn is None:
        print(f"Unknown check: {check}", file=sys.stderr)
        sys.exit(1)

    passed, msg = fn(url, arg)
    print(msg)
    sys.exit(0 if passed else 1)
