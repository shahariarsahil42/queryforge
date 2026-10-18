"""Database operations for equivalent MongoDB/PostgreSQL query workloads."""
import os
from contextlib import contextmanager
from pymongo import MongoClient, ASCENDING
import psycopg

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://queryforge:queryforge@localhost:5432/queryforge")


def mongo_client():
    return MongoClient(MONGO_URL, serverSelectionTimeoutMS=3500)


def postgres_connect():
    return psycopg.connect(POSTGRES_URL, connect_timeout=4)


def check_connections():
    state = {}
    try:
        with mongo_client() as client:
            client.admin.command("ping")
        state["mongodb"] = "connected"
    except Exception:
        state["mongodb"] = "unavailable"
    try:
        with postgres_connect() as conn:
            conn.execute("SELECT 1").fetchone()
        state["postgresql"] = "connected"
    except Exception:
        state["postgresql"] = "unavailable"
    return state


def setup_products(products: list[dict]):
    with postgres_connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, category TEXT NOT NULL, price_cents INTEGER NOT NULL)")
        conn.execute("TRUNCATE TABLE products")
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO products (id, category, price_cents) VALUES (%s, %s, %s)",
                [(p["id"], p["category"], p["price_cents"]) for p in products],
            )
        conn.execute("DROP INDEX IF EXISTS ix_products_category_price")
        conn.commit()
    with mongo_client() as client:
        coll = client["queryforge"]["products"]
        coll.drop()
        coll.insert_many([{"_id": p["id"], "category": p["category"], "price_cents": p["price_cents"]} for p in products], ordered=False)


def set_index(database: str, enabled: bool):
    if database == "postgresql":
        with postgres_connect() as conn:
            if enabled:
                conn.execute("CREATE INDEX IF NOT EXISTS ix_products_category_price ON products (category, price_cents, id)")
            else:
                conn.execute("DROP INDEX IF EXISTS ix_products_category_price")
            conn.commit()
    else:
        with mongo_client() as client:
            coll = client["queryforge"]["products"]
            if enabled:
                coll.create_index([("category", ASCENDING), ("price_cents", ASCENDING), ("_id", ASCENDING)], name="category_price_id")
            else:
                coll.drop_indexes()  # keeps built-in _id index


def query_postgresql():
    with postgres_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, category, price_cents FROM products WHERE category = %s AND price_cents >= %s ORDER BY price_cents, id LIMIT 50", ("electronics", 5000))
            return cur.fetchall()


def query_mongodb():
    with mongo_client() as client:
        coll = client["queryforge"]["products"]
        return list(coll.find({"category": "electronics", "price_cents": {"$gte": 5000}}).sort([("price_cents", 1), ("_id", 1)]).limit(50))


def explain_postgresql():
    with postgres_connect() as conn:
        row = conn.execute("EXPLAIN (ANALYZE, FORMAT JSON) SELECT id, category, price_cents FROM products WHERE category = %s AND price_cents >= %s ORDER BY price_cents, id LIMIT 50", ("electronics", 5000)).fetchone()
    plan = row[0][0]
    return {"root_node": plan["Plan"]["Node Type"], "execution_ms": round(plan["Execution Time"], 3), "details": plan["Plan"]}


def _plan_stages(value):
    stages = set()
    if isinstance(value, dict):
        for key, entry in value.items():
            if key in ("stage", "nodeType") and isinstance(entry, str):
                stages.add(entry)
            stages.update(_plan_stages(entry))
    elif isinstance(value, list):
        for entry in value:
            stages.update(_plan_stages(entry))
    return stages


def explain_mongodb():
    with mongo_client() as client:
        coll = client["queryforge"]["products"]
        report = coll.find({"category": "electronics", "price_cents": {"$gte": 5000}}).sort([("price_cents", 1), ("_id", 1)]).limit(50).explain()
    return {"stages": sorted(_plan_stages(report.get("queryPlanner", {}).get("winningPlan", {}))),
            "execution_stats": {k: report.get("executionStats", {}).get(k) for k in ("nReturned", "totalKeysExamined", "totalDocsExamined", "executionTimeMillis")}}


@contextmanager
def benchmark_session(database: str):
    """Keep connections warm across repetitions for a more meaningful benchmark."""
    if database == "postgresql":
        with postgres_connect() as conn:
            with conn.cursor() as cur:
                def run():
                    cur.execute("SELECT id, category, price_cents FROM products WHERE category = %s AND price_cents >= %s ORDER BY price_cents, id LIMIT 50", ("electronics", 5000))
                    return cur.fetchall()
                yield run
    else:
        with mongo_client() as client:
            coll = client["queryforge"]["products"]
            def run():
                return list(coll.find({"category": "electronics", "price_cents": {"$gte": 5000}}).sort([("price_cents", 1), ("_id", 1)]).limit(50))
            yield run
