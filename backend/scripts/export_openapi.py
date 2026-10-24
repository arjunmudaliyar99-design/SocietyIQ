"""Write the OpenAPI schema for the TypeScript client (docs/04 §3).

Run from backend/: uv run python scripts/export_openapi.py ../packages/shared/openapi.json
"""

import json
import os
import sys

# The local-only dev routes must never appear in the shared API types.
os.environ["APP_ENV"] = "test"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import create_app  # noqa: E402

if __name__ == "__main__":
    with open(sys.argv[1], "w", encoding="utf-8") as f:
        json.dump(create_app().openapi(), f, indent=2, sort_keys=True)
        f.write("\n")
