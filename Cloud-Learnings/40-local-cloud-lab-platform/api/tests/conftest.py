"""Test configuration that must be applied before the API is imported."""

import os
import tempfile
from pathlib import Path


TEST_DB_PATH = Path(tempfile.gettempdir()) / "cloud-learnings-api-tests.db"
os.environ.setdefault("DB_PATH", str(TEST_DB_PATH))
