from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1 import v1_router


app = FastAPI()

# -------------------------
# CORS (REQUIRED FOR NEXT.JS)
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Next.js dev
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# API VERSIONING
# -------------------------
app.include_router(v1_router)

# -------------------------
# HEALTH CHECK
# -------------------------
@app.get("/")
def root():
    return {"message": "Stock Signal Platform backend is alive"}
