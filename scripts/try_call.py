# Manual script - asli Groq call karta hai (pytest test NAHI hai).
# Chalao (project root se): uv run python -m scripts.try_call

from app.config import client, MODEL

message = {"role": "user", "content": "Say hi in exactly 5 words"}

messages = [message]

response = client.chat.completions.create(
    model=MODEL, messages=messages, reasoning_effort="low"
)

print(response.choices[0].message.content)
print(response.usage)
print(response.choices[0].finish_reason)
