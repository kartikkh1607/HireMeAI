# =============================================================================
# tests/test_llm.py - asli structured_call(), par NAKLI Groq client ke saath.
# Check: production bug wala token cap (8192) + strict schema Groq ko jaata
# hai, aur retry policy sahi errors pe hi retry karti hai.
# =============================================================================
from types import SimpleNamespace

import httpx
import pytest
from groq import BadRequestError
from tenacity import wait_none

import app.llm as llm
from app.schemas import StrictModel


# Chhota output model - Resume jitna bada nahi chahiye, logic same hai
class Echo(StrictModel):
    text: str


def response(content, finish_reason="stop"):
    # Groq (non-stream) response ka shape: response.choices[0].message.content
    return SimpleNamespace(
        choices=[SimpleNamespace(finish_reason=finish_reason, message=SimpleNamespace(content=content))]
    )


class FakeClient:
    # Har call pe list ka agla item: response lautao, ya Exception ho to raise.
    # calls me arguments yaad rakhta hai - kitni baar aur kya bheja, dono check.
    def __init__(self, results):
        self.calls = []
        self._results = list(results)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def fake_groq(monkeypatch):
    # Retry ke beech 2s wait hota hai - tests me sleep nahi chahiye.
    # structured_call.retry = tenacity ka Retrying object; har call iski copy
    # banata hai, to yahan wait badalna kaafi hai (test ke baad wapas).
    monkeypatch.setattr(llm.structured_call.retry, "wait", wait_none())

    def install(*results):
        client = FakeClient(results)
        # llm.py "from app.config import client" karta hai -> app.llm.client patch
        monkeypatch.setattr(llm, "client", client)
        return client

    return install


def bad_request():
    # Groq strict mode me JSON kata to yahi aata hai (400 json_validate_failed)
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return BadRequestError("json_validate_failed", response=httpx.Response(400, request=req), body=None)


def test_sends_token_cap_strict_schema_and_temperature(fake_groq):
    client = fake_groq(response('{"text": "hi"}'))

    result = llm.structured_call("SYSTEM", "USER", Echo)

    assert result == Echo(text="hi")
    kwargs = client.calls[0]
    # Production bug (Render): ye limit set nahi thi -> JSON kat gaya tha
    assert kwargs["max_completion_tokens"] == llm.MAX_COMPLETION_TOKENS == 8192
    assert kwargs["temperature"] == 0
    assert kwargs["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "Echo", "schema": Echo.model_json_schema(), "strict": True},
    }


def test_validation_error_is_retried(fake_groq):
    # Pehli baar galat shape ka JSON (ValidationError) -> dusri baar sahi
    client = fake_groq(response('{"wrong": 1}'), response('{"text": "ok"}'))

    assert llm.structured_call("SYSTEM", "USER", Echo) == Echo(text="ok")
    assert len(client.calls) == 2


def test_bad_request_is_not_retried(fake_groq):
    # 400 har baar same aayega -> retry = sirf time + quota waste
    client = fake_groq(bad_request(), response('{"text": "never reached"}'))

    with pytest.raises(BadRequestError):
        llm.structured_call("SYSTEM", "USER", Echo)
    assert len(client.calls) == 1
