import requests

# Server setup
MODEL_URL = "http://127.0.0.1:8080/v1/chat/completions"
HEADERS = {"Content-Type": "application/json"}

# -------------------------
# User-level batching
# -------------------------
def batch_inference(user_prompts, max_tokens=256):
    batched_responses = []

    for prompt in user_prompts:
        data = {
            "model": "local-model",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        resp = requests.post(MODEL_URL, headers=HEADERS, json=data)
        resp.raise_for_status()
        result = resp.json()["choices"][0]["message"]["content"]
        batched_responses.append(result)

    return batched_responses


if __name__ == "__main__":
    # Multiple user queries at once
    user_queries = [
        "Summarize the importance of crop rotation.",
        "List 5 main steps in seed production.",
        "Explain the difference between open-pollinated and hybrid seeds."
    ]

    responses = batch_inference(user_queries)
    for i, r in enumerate(responses):
        print(f"User {i+1}: {r}")
