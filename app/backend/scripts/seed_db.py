"""python -m scripts.seed_db  (from app/backend/)"""

from __future__ import annotations

import asyncio

from app.seed_db import seed

if __name__ == "__main__":
    asyncio.run(seed())
