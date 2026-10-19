from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pymongo.errors import PyMongoError, WriteError

from database import Base, engine
from mongo_db import setup_collections
from routers.auth import router as auth_router
from routers.chat import router as chat_router
from routers.doc_notices import router as doc_notices_router
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
setup_collections()
app.include_router(doc_notices_router)
app.include_router(chat_router)


@app.exception_handler(WriteError)
def mongo_validation_error(request: Request, error: WriteError):
    return JSONResponse(status_code=400, content={"detail": f"MongoDB rejected the document: {error.details.get('errmsg')}"})


@app.exception_handler(PyMongoError)
def mongo_error(request: Request, error: PyMongoError):
    return JSONResponse(status_code=500, content={"detail": f"MongoDB error: {type(error).__name__}"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/notices")
def notice_page():
    return FileResponse(ROOT / "index.html")


@app.get("/chat")
def chat_page():
    return FileResponse(ROOT / "chat.html")


@app.get("/feedback.js")
def script():
    return FileResponse(ROOT / "feedback.js")


if __name__ == "__main__":
    uvicorn.run(app, port=PORT_BASE)
