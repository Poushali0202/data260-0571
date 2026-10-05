from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from database import Base, engine
from routers.auth import router as auth_router
from routers.notices import router as notices_router
from routers.suppliers import router as suppliers_router

PORT_BASE = 8571
ROOT = Path(__file__).resolve().parent

app = FastAPI(title="Grocery supply and recall notices")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Base.metadata.create_all(bind=engine)
app.include_router(auth_router)
app.include_router(suppliers_router)
app.include_router(notices_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/notices")
def notice_page():
    return FileResponse(ROOT / "index.html")


@app.get("/feedback.js")
def script():
    return FileResponse(ROOT / "feedback.js")


if __name__ == "__main__":
    uvicorn.run(app, port=PORT_BASE)
