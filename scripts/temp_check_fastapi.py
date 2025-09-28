try:
    import fastapi
    print("FastAPI is installed.")
except ImportError:
    print("FastAPI is NOT installed.")

try:
    import uvicorn
    print("Uvicorn is installed.")
except ImportError:
    print("Uvicorn is NOT installed.")
