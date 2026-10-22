"""Reset the database from data/: uv run -m backend.seed"""

from backend.db import path, seed

if __name__ == "__main__":
    counts = seed()
    print(
        f"Seeded {path()}: {counts['claims']} claims, {counts['policies']} policies, "
        f"{counts['customers']} customers and {counts['handlers']} handlers."
    )
