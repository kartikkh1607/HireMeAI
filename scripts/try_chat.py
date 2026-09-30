# Manual script - asli Groq call karta hai (pytest test NAHI hai).
# Chalao (project root se): uv run python -m scripts.try_chat

from app.chat import build_system_prompt, stream_answer
from app.resume import load_resume
from app.schemas import ChatMessage

resume = load_resume()
system_prompt = build_system_prompt(resume)
history: list[ChatMessage] = []

print("HireMeAI ready. Type 'exit' to quit.\n")

while True:
    question = input("Recruiter: ").strip()
    if question.lower() in {"exit", "quit"}:
        break
    if not question:
        continue

    print("HireMeAI: ", end="", flush=True)
    answer = ""
    for piece in stream_answer(system_prompt, history, question):
        print(piece, end="", flush=True)
        answer += piece
    print("\n")

    history.append(ChatMessage(role="user", content=question))
    history.append(ChatMessage(role="assistant", content=answer))