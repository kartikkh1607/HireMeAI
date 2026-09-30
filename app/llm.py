from typing import Literal, TypeVar

from groq import APIConnectionError, InternalServerError, RateLimitError
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import MODEL, client

T = TypeVar("T", bound=BaseModel)

Effort = Literal["low", "medium", "high"]

RETRYABLE_ERRORS = (
    ValidationError,
    RateLimitError,
    APIConnectionError,
    InternalServerError,
)


@retry(
    retry=retry_if_exception_type(RETRYABLE_ERRORS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def structured_call(
    system_prompt: str,
    user_prompt: str,
    output_model: type[T],
    reasoning_effort: Effort = "medium",
) -> T:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": output_model.__name__,
                "schema": output_model.model_json_schema(),
                "strict": True,
            },
        },
        temperature=0,
        reasoning_effort=reasoning_effort,
    )

    choice = response.choices[0]
    if choice.finish_reason == "length":
        raise ValueError("Output max_tokens pe cut ho gaya - JSON incomplete hai")

    return output_model.model_validate_json(choice.message.content)
