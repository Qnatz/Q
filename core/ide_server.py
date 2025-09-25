import uvicorn
from fastapi import FastAPI, Request
import threading
import asyncio
import logging

logger = logging.getLogger(__name__)

class IDEServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8001):
        self.app = FastAPI()
        self.host = host
        self.port = port
        self.context_data = {} # Store received context data

        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/")
        async def read_root():
            return {"message": "IDE Server is running"}

        @self.app.post("/context")
        async def post_context(request: Request):
            data = await request.json()
            self.context_data = data
            logger.info(f"Received IDE context: {data}")
            return {"message": "Context received successfully"}

        @self.app.get("/context")
        async def get_context():
            return self.context_data

    def start_server(self):
        """Starts the Uvicorn server in a separate thread."""
        logger.info(f"Starting IDE server on http://{self.host}:{self.port}")
        # Use a custom loop to run uvicorn in a separate thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="warning")
        server = uvicorn.Server(config)
        loop.run_until_complete(server.serve())

    def run_in_thread(self):
        """Helper to run the server in a daemon thread."""
        thread = threading.Thread(target=self.start_server, daemon=True)
        thread.start()
        logger.info("IDE server thread started.")

if __name__ == "__main__":
    # Example usage:
    server = IDEServer()
    server.run_in_thread()
    # Keep the main thread alive for a bit to allow the server to start
    import time
    time.sleep(10)
    print("Main thread exiting, server should continue in background.")
