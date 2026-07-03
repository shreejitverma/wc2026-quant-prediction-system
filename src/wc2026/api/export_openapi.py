"""Export the OpenAPI schema to disk so the frontend typed client can be
generated (`npm run gen:api`) without a running server.

Usage: uv run python -m wc2026.api.export_openapi [out_path]
Default out_path: frontend/openapi.json (run from the repo root; see Makefile
target `openapi`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .server import app


def main(out_path: str = "frontend/openapi.json") -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"OpenAPI schema written to {out}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
