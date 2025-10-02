import os
import sys
import dotenv

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

dotenv.load_dotenv() # Load environment variables from .env file

from qllm.unified_llm import UnifiedLLM
from qllm.config import Config
import logging

# Configure logging to show debug messages
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

def test_gemini_api():
    print("\n--- Testing Gemini API ---")
    
    # Load configuration
    config = Config()
    print(f"Configured backend: {config.backend}")
    print(f"Configured Gemini model: {config.gemini_model}")

    # Check for API key
    print("Checking environment variables for GEMINI_...")
    for key, value in os.environ.items():
        if key.startswith("GEMINI"):
            print(f"  Found: {key}={value[:5]}...") # Print first 5 chars for security

    api_key = os.getenv(config.gemini_api_key_env)
    if not api_key:
        print(f"Error: Gemini API key not found in environment variable {config.gemini_api_key_env}")
        print("Please set the API key before running the test.")
        return
    else:
        print("Gemini API key found.")

    try:
        # Initialize UnifiedLLM with Gemini backend
        llm = UnifiedLLM(config)
        print("UnifiedLLM initialized.")

        # Make a simple call to the Gemini LLM
        messages = [
            {"role": "user", "content": "Hello, Gemini! Are you working?"}
        ]
        print("Sending test message to Gemini...")
        response = llm.generate(messages, use_tools=False)
        
        print("\n--- Gemini API Test Result ---")
        print(f"Response: {response}")
        if response and "hello" in response.lower():
            print("Success: Gemini API appears to be working!")
        else:
            print("Warning: Gemini API responded, but the response was unexpected.")

    except Exception as e:
        print(f"Error during Gemini API test: {e}")
        print("Failure: Gemini API test failed.")

if __name__ == "__main__":
    test_gemini_api()
