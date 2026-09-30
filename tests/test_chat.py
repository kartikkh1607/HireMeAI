# =============================================================================
# tests/test_chat.py - asli stream_answer(), par NAKLI Groq client ke saath.
# Check: token cap (max_completion_tokens) Groq ko jaata hai, aur
# finish_reason == "length" pe "(answer truncated)" note aata hai.
# =============================================================================
from types import SimpleNamespace

import app.chat as chat
from app.schemas import ChatMessage


def chunk(text=None, finish_reason=None):
    # Groq stream chunk ka shape: chunk.choices[0].delta.content
    # SimpleNamespace = jhatpat object jiske attributes hum khud bana dein
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=text), finish_reason=finish_reason)]
    )


class FakeClient:
    # client.chat.completions.create(...) jaisa hi raasta, par Groq ki jagah
    # humare chunks lautata hai aur jo arguments mile unhe yaad rakhta hai
    def __init__(self, chunks):
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self._chunks = chunks

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return iter(self._chunks)


def run(monkeypatch, chunks, history=None):
    fake = FakeClient(chunks)
    # chat.py "from app.config import client" karta hai -> app.chat.client patch
    monkeypatch.setattr(chat, "client", fake)
    text = "".join(chat.stream_answer("SYSTEM", history or [], "Question?"))
    return text, fake.calls[0]


def test_sends_token_cap_and_streams_text(monkeypatch):
    text, kwargs = run(monkeypatch, [chunk("Hi "), chunk("there"), chunk(finish_reason="stop")])
    assert text == "Hi there"
    assert kwargs["max_completion_tokens"] == chat.MAX_COMPLETION_TOKENS == 1500
    assert kwargs["stream"] is True


def test_truncated_answer_gets_note(monkeypatch):
    text, _ = run(monkeypatch, [chunk("Long answer"), chunk(finish_reason="length")])
    assert text == "Long answer" + chat.TRUNCATED_NOTE


def test_only_last_10_history_messages_are_sent(monkeypatch):
    history = [ChatMessage(role="user" if i % 2 == 0 else "assistant", content=f"m{i}") for i in range(14)]
    _, kwargs = run(monkeypatch, [chunk("ok")], history)
    messages = kwargs["messages"]
    # system + 10 history + naya sawaal
    assert len(messages) == 12
    assert messages[1]["content"] == "m4"
    assert messages[-1] == {"role": "user", "content": "Question?"}
