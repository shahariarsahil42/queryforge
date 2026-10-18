"""QueryForge: Cross-database performance benchmarking platform."""

import csv
import io
import json
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from app.benchmark import make_products, measure
from app.databases import (
    check_connections,
    setup_products,
    set_index,
    benchmark_session,
    explain_postgresql,
    explain_mongodb,
)
from app.history import (
    save_experiment,
    list_experiments,
    get_experiment,
)


app = FastAPI(
    title="QueryForge",
    description="Cross-database query benchmarking platform",
    version="2.0.0",
)

_lock = threading.Lock()
_dataset_size = 0


# -----------------------------
# REQUEST MODELS
# -----------------------------

class SetupRequest(BaseModel):
    rows: int = Field(default=5000, ge=1000, le=100000)


class BenchmarkRequest(BaseModel):
    repetitions: int = Field(default=20, ge=5, le=100)


# -----------------------------
# DASHBOARD
# -----------------------------

@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse(
        Path(__file__).resolve().parent / "static" / "index.html"
    )


# -----------------------------
# HEALTH CHECK
# -----------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "queryforge-api",
    }


# -----------------------------
# DATABASE STATUS
# -----------------------------

@app.get("/api/status")
def status():
    return {
        "databases": check_connections(),
        "rows_last_seeded": _dataset_size,
    }


# -----------------------------
# DATASET GENERATION
# -----------------------------

@app.post("/api/setup")
def setup(request: SetupRequest):
    global _dataset_size

    if not _lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Another operation is running",
        )

    try:
        products = make_products(request.rows)
        setup_products(products)

        _dataset_size = request.rows

        return {
            "message": "Synthetic data loaded into both databases",
            "rows_per_database": request.rows,
            "seed": 42,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Database setup failed: {type(exc).__name__}. "
                "Check docker compose logs."
            ),
        ) from exc

    finally:
        _lock.release()


# -----------------------------
# DATABASE BENCHMARKING
# -----------------------------

@app.post("/api/benchmark")
def benchmark(request: BenchmarkRequest):

    if not _lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Another operation is running",
        )

    try:
        if _dataset_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Run dataset setup first",
            )

        output = []

        for db, explain in (
            ("postgresql", explain_postgresql),
            ("mongodb", explain_mongodb),
        ):

            for indexed in (False, True):

                set_index(db, indexed)

                with benchmark_session(db) as query:
                    stats = measure(
                        query,
                        request.repetitions,
                    )

                output.append({
                    "database": db,
                    "indexed": indexed,
                    **stats,
                    "explain": explain(),
                })

        result = {
            "rows_per_database": _dataset_size,
            "workload": (
                "category=electronics, "
                "price_cents>=5000, "
                "order by price_cents,id, "
                "limit 50"
            ),
            "results": output,
            "note": (
                "Sequential client-side timings. "
                "Different database engines and protocols "
                "are not directly comparable."
            ),
        }

        # Automatically save the benchmark
        result["experiment_id"] = save_experiment(
            result,
            request.repetitions,
        )

        return result

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Benchmark failed: {type(exc).__name__}. "
                "Check docker compose logs."
            ),
        ) from exc

    finally:
        _lock.release()


# -----------------------------
# BENCHMARK HISTORY
# -----------------------------

@app.get("/api/history")
def history(limit: int = 25):

    if not 1 <= limit <= 100:
        raise HTTPException(
            status_code=422,
            detail="limit must be between 1 and 100",
        )

    return {
        "experiments": list_experiments(limit)
    }


# -----------------------------
# SINGLE EXPERIMENT
# -----------------------------

@app.get("/api/history/{experiment_id}")
def history_detail(experiment_id: int):

    result = get_experiment(experiment_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Experiment not found",
        )

    return result


# -----------------------------
# CSV AND JSON EXPORTS
# -----------------------------

@app.get("/api/history/{experiment_id}/export")
def export_history(
    experiment_id: int,
    format: str = "csv",
):

    result = get_experiment(experiment_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Experiment not found",
        )

    # JSON export
    if format == "json":
        return Response(
            content=json.dumps(result, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": (
                    f"attachment; "
                    f"filename=queryforge-{experiment_id}.json"
                )
            },
        )

    if format != "csv":
        raise HTTPException(
            status_code=422,
            detail="format must be csv or json",
        )

    # CSV export
    fields = (
        "experiment_id",
        "created_at",
        "rows_per_database",
        "repetitions",
        "database",
        "indexed",
        "runs",
        "p50_ms",
        "p95_ms",
        "mean_ms",
        "min_ms",
        "max_ms",
        "sequential_queries_per_sec",
    )

    stream = io.StringIO()
    writer = csv.DictWriter(
        stream,
        fieldnames=fields,
    )

    writer.writeheader()

    for row in result["results"]:
        values = {
            **result,
            **row,
        }

        writer.writerow({
            field: values.get(field, "")
            for field in fields
        })

    return Response(
        content=stream.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f"attachment; "
                f"filename=queryforge-{experiment_id}.csv"
            )
        },
    )