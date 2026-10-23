import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

url = "http://127.0.0.1:11434/api/chat"

payload = {
    "model": "qwen3:1.7b",
    "stream": False,
    "think": False,
    "messages": [
        {
            "role": "system",
            "content": (
                "You suggest data-quality checks only. "
                "Never suggest deleting, replacing, or modifying values. "
                "Treat uncertain values as requiring human review. "
                "Reply in two short sentences."
            ),
        },
        {
            "role": "user",
            "content": (
                "A column called Amount contains: "
                '100, 250, "unknown", 400. '
                "If the column is intended to be numeric, "
                "what should we check?"
            ),
        },
    ],
    "options": {
        "temperature": 0,
        "num_ctx": 2048,
        "num_predict": 160,
    },
}

request = Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urlopen(request, timeout=180) as response:
        result = json.load(response)

    answer = result.get("message", {}).get("content", "").strip()

    if answer:
        print("Local AI response:")
        print(answer)
    else:
        print("No final answer received. Please share this result.")

except HTTPError as error:
    print(f"Ollama returned HTTP error: {error.code}")
    print(error.read().decode("utf-8", errors="replace"))

except URLError as error:
    print("Could not connect to local Ollama:", error.reason)

except TimeoutError:
    print("The local model took too long to respond.")