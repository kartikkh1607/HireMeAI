# =============================================================================
# app/llm.py
# Kaam: ek REUSABLE function - "ye prompt lo, aur output EXACTLY is Pydantic
#       model ke shape me do". Galti ho to khud retry karo.
#
# Week 1 day 4 ki 2 kamzoriyan yahan fix hoti hain:
#   1. json_object sirf "valid JSON" deta tha, schema ki guarantee nahi
#      -> ab json_schema + strict: True
#   2. galat output pe koi retry nahi tha -> ab tenacity se retry
#
# Abhi sirf resume.py isko use karta hai, par ye generic hai - kal koi naya
# model (jaise JobDescription) banao, yahi function kaam karega.
# =============================================================================

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

# -----------------------------------------------------------------------------
# GENERIC TYPE
# T = "koi bhi class jo BaseModel se bani ho".
# structured_call(..., Resume) -> Resume milega
# structured_call(..., Ticket) -> Ticket milega
# Fayda: VS Code ko pata rehta hai kaunsa type wapas aaya -> autocomplete sahi.
# -----------------------------------------------------------------------------
T = TypeVar("T", bound=BaseModel)

# Sirf ye 3 values allowed. Galti se "meduim" likha to VS Code turant pakdega.
Effort = Literal["low", "medium", "high"]

# -----------------------------------------------------------------------------
# RETRY POLICY - kaunse errors pe dobara try karna hai.
# Rule: sirf TEMPORARY problems retry karo.
#
#  Retry karo (dobara try se theek ho sakta hai):
#   ValidationError     -> LLM ne galat shape ka JSON diya (next try me sahi de sakta hai)
#   RateLimitError      -> 429, bahut zyada requests - thoda ruk ke try karo
#   APIConnectionError  -> network gaya / timeout
#   InternalServerError -> Groq ka server kharab (5xx)
#
#  Retry MAT karo (har baar same error aayega, sirf time + quota waste):
#   AuthenticationError (401) -> galat API key
#   BadRequestError (400)     -> galat request / schema
#   ValueError ("length")     -> neeche dekho
#
# Interview Q: "ValidationError bhi ValueError ki subclass hai, to length wala
# ValueError retry kyun nahi hota?"
# A: tenacity isinstance(error, RETRYABLE_ERRORS) check karta hai. Subclass
# rishta ek taraf chalta hai: ValidationError IS-A ValueError, par plain
# ValueError IS-NOT-A ValidationError. Isliye length wala retry nahi hota.
# -----------------------------------------------------------------------------
RETRYABLE_ERRORS = (
    ValidationError,
    RateLimitError,
    APIConnectionError,
    InternalServerError,
)


# -----------------------------------------------------------------------------
# @retry DECORATOR - poore function ko wrap karta hai.
# Function fail hua (RETRYABLE error se) -> ruko -> dobara poora function chalao.
#
# stop_after_attempt(3) -> maximum 3 tries (1 original + 2 retry)
# wait_exponential(...) -> har retry se pehle wait. Formula: 1 * 2^(n-1),
#                          phir min 2 / max 10 se clamp.
#                          3 tries me waits: 2s, 2s. (Aur tries hote to 4s, 8s, 10s...)
#                          Isko EXPONENTIAL BACKOFF kehte hain - rate limit lage
#                          to server ko saans lene ka time milta hai.
# reraise=True          -> 3 baar fail ho gaya to ASLI error dikhao, tenacity ka
#                          "RetryError" wrapper nahi. Debugging aasan hoti hai.
# -----------------------------------------------------------------------------
@retry(
    retry=retry_if_exception_type(RETRYABLE_ERRORS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def structured_call(
    system_prompt: str,
    user_prompt: str,
    output_model: type[T],  # class khud pass hoti hai (Resume), object nahi (Resume(...))
    reasoning_effort: Effort = "medium",  # default medium; chat me "low" dete hain
) -> T:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        # ---- STRICT STRUCTURED OUTPUT ----
        # json_object (Week 1) = "koi bhi valid JSON"
        # json_schema + strict = "SIRF is schema wala JSON" - Groq generation ke
        # waqt hi model ko schema ke bahar jaane nahi deta.
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": output_model.__name__,  # "Resume" - class ka naam
                "schema": output_model.model_json_schema(),  # Pydantic -> JSON schema
                "strict": True,
            },
        },
        temperature=0,  # extraction hai, creativity nahi chahiye (Week 1 Q2)
        reasoning_effort=reasoning_effort,  # gpt-oss reasoning model hai - kitna "soche"
    )

    choice = response.choices[0]

    # ---- TRUNCATION CHECK (Week 1 Q3) ----
    # "length" = max_tokens pe output kat gaya -> JSON adhoora hai.
    # Reasoning models sochne me bhi tokens khaate hain, isliye ye zyada hota hai.
    # Retry nahi karte - dobara bhi wahin katega. Isliye plain ValueError.
    if choice.finish_reason == "length":
        raise ValueError("Output max_tokens pe cut ho gaya - JSON incomplete hai")

    # ---- PARSE + VALIDATE ek step me ----
    # Week 1 me 2 steps the: json.loads() -> Model(**data)
    # model_validate_json() dono ek saath karta hai. Shape galat ho to
    # ValidationError -> jo upar RETRYABLE list me hai -> auto retry.
    # (Strict mode ke baad bhi ye check rakhte hain - defense in depth.
    #  Har model/provider strict mode 100% support nahi karta.)
    return output_model.model_validate_json(choice.message.content) # type: ignore