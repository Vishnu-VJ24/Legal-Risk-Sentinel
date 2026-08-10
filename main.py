from __future__ import annotations

import uvicorn

from src.config import get_settings
from src.server import app

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)
