from fastapi import FastAPI

app = FastAPI(
    title="QueryForge",
    description="Cross-database performance analysis platform",
    version="0.1.0"
)


@app.get("/")
def home():
    return {
        "project": "QueryForge",
        "message": "Welcome to QueryForge!"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "queryforge-api"
    }
