# Syntax sanity check for ARZON 2.0 backend
import ast
from pathlib import Path

for path in Path("backend/app").rglob("*.py"):
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
print("All backend Python files parse successfully")
