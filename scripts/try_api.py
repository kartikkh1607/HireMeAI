# Server ko sawaal bhejo aur jawab tukdon me print karo.
# Pehle server chalao (ek terminal): uv run uvicorn app.main:app --reload
# Phir ye (dusra terminal, project root se): uv run python -m scripts.try_api
import httpx  # HTTP client - groq ke saath pehle hi install ho chuka hai

payload = {
    "question": "What projects has he built?",
    "history": [],
}

# httpx.stream -> response ko tukdon me padho (pura aane ka wait mat karo)
with httpx.stream("POST", "http://127.0.0.1:8000/chat", json=payload, timeout=60) as response:
    print("Status:", response.status_code)
    for text in response.iter_text():
        print(text, end="", flush=True)  # flush=True -> turant screen pe dikhao
print()