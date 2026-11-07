from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .api.routes import router

app = FastAPI(title="Drone Racing Aggregator API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(engine)
    from .seed import main as seed_main
    try:
        seed_main()
    except Exception as exc:
        print(f"SEED WARNING: {exc}")


@app.get("/api/health")
def health():
    return {"status": "ok"}
