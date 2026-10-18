# QueryForge

**A reproducible, local cross-database query benchmarking and optimization lab** built with Python, FastAPI, MongoDB, PostgreSQL, Docker, and automated tests.

## Features

- Responsive browser dashboard served at `http://localhost:8000`
- One-click deterministic synthetic data generation, 1,000–20,000 documents/rows per database
- Equivalent product data in PostgreSQL 16 and MongoDB 7
- Single workload: category equality + price range + ordering + `LIMIT 50`
- Indexed vs. unindexed experiments using compound indexes
- Warm-up and configurable repeated sequential query measurements
- Median (p50), p95, mean, min, max, and sequential queries per second
- Database explain-plan insights (`EXPLAIN ANALYZE` / MongoDB `explain`)
- Input validation, status and health endpoints, concurrency guard, and seven unit/API tests

## Quick start on Mac

1. Install and launch [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. Open a Terminal in this folder and run:

   ```bash
   docker compose up --build -d
   ```

3. Wait for databases to become healthy. Check with:

   ```bash
   docker compose ps
   ```

4. Open **http://localhost:8000**.
5. Click **Seed synthetic data**. Then **Run 4 benchmark cases**.
6. Run automated tests:

   ```bash
   docker compose exec api python -m pytest -v
   ```

7. Stop all containers:

   ```bash
   docker compose down
   ```

   To discard generated databases as well, use `docker compose down -v` (**deletes your local QueryForge datasets**).

## API

- `GET /` browser dashboard
- `GET /health` basic health check
- `GET /api/status` database connectivity and last seeded row count (current API session)
- `POST /api/setup` JSON e.g. `{"rows":5000}` resets and seeds both databases
- `POST /api/benchmark` JSON e.g. `{"repetitions":20}` runs four experiments
- `GET /docs` interactive API documentation

## Workload and fairness considerations

The generated data uses the same seeded PRNG in both engines (`seed=42`), same identifiers, categories, and price values. Both filters use `category = electronics` and `price_cents >= 5000`, sort by `(price_cents, id)`, and return 50 matches. The indexed runs create compound indexes on category, price, and ID. Results include **complete client-side fetch times**, not just internal database server execution times. Connections remain open throughout each benchmark case.

**Interpret carefully:** PostgreSQL and MongoDB use different storage structures, protocols, query planners, and execution environments. This is a teaching experiment, **not a proof one database is universally faster**. OS page cache, database cache, and run order affect results. For more rigorous comparisons, alternate case order, add more workloads, capture hardware/system information, repeat independent trials, and report uncertainty.

## Safety and scope

For local development only. The dashboard has **no authentication** and should **not be published to the internet** without adding authentication, configuration hardening, rate limits, and secrets management. Database credentials in `compose.yaml` are local development defaults only. All generated data is synthetic; do not upload private or workplace records.

## Tests

Run inside Docker with `docker compose exec api python -m pytest -v`. Unit tests don't require live database connections; use the dashboard to run end-to-end experiments.

## Next improvements

- Multiple workload types and baseline correctness comparisons
- Repeated randomized trial order and confidence intervals
- More robust execution-plan summarization
- Persist experiment history and export CSV
- Automated CI using GitHub Actions

## Author

Shahariar Chowdhury Sahil • [GitHub](https://github.com/shahariarsahil42)

## Integrating with a Day 1 project

If you already have a `~/Desktop/queryforge` Git repository, extract the provided ZIP into `~/Downloads/queryforge_mvp` and run:

```bash
bash ~/Downloads/queryforge_mvp/install_into_existing_mac.command
```

This updates the Day 1 API, tests, and dependencies **without deleting `.git` or earlier commits**. A timestamped local backup of changed Day 1 files is created in `~/Desktop/queryforge/.queryforge_backup_.../` and excluded from Git.
