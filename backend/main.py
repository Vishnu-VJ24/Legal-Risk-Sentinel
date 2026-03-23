from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.analyze import router as analyze_router

app = FastAPI(title="LexAI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router, prefix="/api")


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
