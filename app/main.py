"""QueryForge: local-only, teaching-oriented database benchmarking dashboard."""
import threading
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.benchmark import make_products, measure
from app.databases import (check_connections, setup_products, set_index, benchmark_session,
                           explain_postgresql, explain_mongodb)

app = FastAPI(title="QueryForge", description="Cross-database query benchmarking platform", version="1.0.0")
_lock = threading.Lock()
_dataset_size = 0


class SetupRequest(BaseModel):
    rows: int = Field(default=5000, ge=1000, le=20000)


class BenchmarkRequest(BaseModel):
    repetitions: int = Field(default=20, ge=5, le=100)


@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse(Path(__file__).resolve().parent / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "queryforge-api"}


@app.get("/api/status")
def status():
    return {"databases": check_connections(), "rows_last_seeded": _dataset_size}


@app.post("/api/setup")
def setup(request: SetupRequest):
    global _dataset_size
    if not _lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Another operation is running")
    try:
        products = make_products(request.rows)
        setup_products(products)
        _dataset_size = request.rows
        return {"message": "Synthetic data loaded into both databases", "rows_per_database": request.rows, "seed": 42}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database setup failed: {type(exc).__name__}. Check docker compose logs.") from exc
    finally:
        _lock.release()


@app.post("/api/benchmark")
def benchmark(request: BenchmarkRequest):
    if not _lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Another operation is running")
    try:
        if _dataset_size == 0:
            raise HTTPException(status_code=400, detail="Run dataset setup first")
        output = []
        for db, explain in (("postgresql", explain_postgresql),
                            ("mongodb", explain_mongodb)):
            for indexed in (False, True):
                set_index(db, indexed)
                with benchmark_session(db) as query:
                    stats = measure(query, request.repetitions)
                output.append({"database": db, "indexed": indexed, **stats, "explain": explain()})
        return {"rows_per_database": _dataset_size, "workload": "category=electronics, price_cents>=5000, order by price_cents,id, limit 50", "results": output,
                "note": "Sequential client-side timings; engines and network/protocol behavior differ. Not a controlled engine speed ranking."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Benchmark failed: {type(exc).__name__}. Check docker compose logs.") from exc
    finally:
        _lock.release()
