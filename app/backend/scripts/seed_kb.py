"""python -m scripts.seed_kb  (from app/backend/)"""

from __future__ import annotations

import asyncio

from app.seed_kb import seed

if __name__ == "__main__":
    asyncio.run(seed())
