import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.settings import settings
from qllm.backends import GeminiBackend
from qllm.config import Config

if __name__ == "__main__":
    if not settings.gemini_api_key:
        print("Error: QAI_GEMINI_API_KEY environment variable not set in .env file.")
        sys.exit(1)

    print("Initializing Gemini Backend...")
    try:
        config = Config(
            backend="gemini",
            gemini_model="gemini-2.5-flash",
        )
        backend = GeminiBackend(cfg=config)
        print("Gemini Backend initialized successfully.")
    except Exception as e:
        print(f"Error initializing Gemini Backend: {e}")
        sys.exit(1)

    messages = [{"role": "user", "content": "Hello"}]
    
    print(f"Sending messages to Gemini: {messages}")
    try:
        response = backend.chat(messages)
        print(f"Raw response from Gemini: {response}")
        
        text = backend.extract_text(response)
        print(f"Extracted text: {text}")
        
        if "Error" in text:
             print("Test failed: Error in response.")
        else:
             print("Test passed: Received a valid response.")

    except Exception as e:
        print(f"An error occurred during the chat: {e}")
