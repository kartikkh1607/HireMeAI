# =============================================================================
# app/main.py
# Kaam: WEB LAYER - browser aur humare code ke beech ka darwaza.
#   - server start pe resume load karna (ek baar)
#   - URLs (endpoints) banana: /chat, /profile, /health
#   - aane wale data ko validate karna
#   - jawab browser tak stream karna
#
# Is file me koi "business logic" nahi hai (parsing, prompt, LLM call).
# Wo sab resume.py / chat.py me hai. Ye sirf unhe web se jodti hai.
# (Separation of concerns - diagram yaad karo)
#
# Chalana: uv run uvicorn app.main:app --reload
# =============================================================================

import logging  # server ke terminal me errors/info print karne ke liye
import math
import os
import threading
import time
from collections import deque
from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager  # lifespan function banane ke liye
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse  # file / JSON / tukdon me jawab
from fastapi.staticfiles import StaticFiles  # React build ki JS/CSS files serve karne ke liye
from pydantic import BaseModel, Field

from app.chat import build_system_prompt, stream_answer
from app.resume import load_resume
from app.schemas import ChatMessage

# Logging ON karo. Default level WARNING hota hai - isliye pehle
# "Resume loaded for ..." wali INFO line terminal me dikhi hi nahi thi.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")

# Apna logger - messages "hiremeai" naam ke saath terminal me dikhenge
logger = logging.getLogger("hiremeai")

# Frontend (index.html) ka folder - resume.py jaisa hi absolute path trick
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# ENV=production (deploy pe set karo) -> /docs, /redoc, /openapi.json band.
# Local pe ye pages kaam ke hain, par public server pe poora API map
# sabko dikhane ki zaroorat nahi. (.env app.config import hote hi load ho chuki hai)
IS_PRODUCTION = os.getenv("ENV", "").strip().lower() == "production"

# -----------------------------------------------------------------------------
# STREAM ERROR SENTINEL - jawab ke BEECH me Groq fail ho to ye fixed string
# stream ke end me bhejte hain. Status 200 pehle hi ja chuka hota hai, isliye
# error batane ka yahi tareeka bachta hai. Frontend (frontend/src/api.ts) is
# EXACT string ko pehchaan ke hata deta hai aur Retry dikhata hai.
# Badlo to dono jagah badlo!
# -----------------------------------------------------------------------------
STREAM_ERROR_SENTINEL = "\n\n[[HIREMEAI_STREAM_ERROR]]"


# -----------------------------------------------------------------------------
# LIFESPAN - server ki zindagi ka start aur end.
#   yield se PEHLE ka code -> server start hote hi EK BAAR chalta hai
#   yield ke BAAD ka code  -> server band hote waqt (humein kuch nahi karna)
#
# Original hiremeai ka sabse bada bug yahan fix hota hai: wahan HAR /chat
# request pe PDF padhi jaati thi aur LLM se parse hoti thi. Ab ek baar.
#
# FAIL FAST: resume load nahi hua (file missing, key galat) to server START
# HI NAHI hoga - error turant dikhega. Behtar hai us situation se jahan server
# chal jaaye aur pehla recruiter aake error dekhe.
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    resume = load_resume()  # cache ho to ~0s, warna ~5s (LLM call)

    # app.state = FastAPI ka "shared dabba". Yahan rakha data har request
    # me available hota hai.
    app.state.resume = resume
    app.state.system_prompt = build_system_prompt(resume)  # prompt bhi ek baar

    logger.info("Resume loaded for %s", resume.name)
    yield  # <- yahan server requests lena shuru karta hai


# title /docs page pe dikhta hai. None = wo page band (production me)
app = FastAPI(
    title="HireMeAI",
    lifespan=lifespan,
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)


# -----------------------------------------------------------------------------
# RATE LIMITER - ek IP kitne sawaal pooch sakti hai (Groq quota bachane ke liye).
# Koi nayi library nahi - bas har IP ke request times ki list (deque).
#
# SLIDING WINDOW: "pichhle 60 second me kitni requests?" - har baar ginte hain.
# (Fixed window "12:00-12:01" me 12:00:59 + 12:01:00 pe double requests nikal
#  jaati hain; sliding me nahi.)
#
# LIMITATIONS (jaan-boojh ke simple rakha):
#   - Data sirf is PROCESS ki memory me hai. Server restart = counts reset.
#     2+ workers/instances chalaoge to har ek ki alag ginti hogi. Ek instance
#     ke liye theek hai; scale karna ho to Redis jaisa shared store chahiye.
#   - Proxy ke peeche (Render, Nginx) request.client.host = PROXY ka IP hota
#     hai, user ka nahi -> sab users ek hi limit share karenge! Isliye deploy
#     pe uvicorn aise chalao:
#       uvicorn app.main:app --proxy-headers --forwarded-allow-ips="*"
#     Tab uvicorn X-Forwarded-For header se asli IP nikaalta hai.
#
# threading.Lock kyun? "def" endpoints alag-alag threads me chalte hain -
# do requests ek saath deque badlein to count galat ho sakta hai.
# -----------------------------------------------------------------------------
MINUTE = 60.0
DAY = 24 * 60 * 60.0


class RateLimiter:
    def __init__(self, per_minute: int, per_day: int, clock: Callable[[], float] = time.monotonic):
        self.per_minute = per_minute
        self.per_day = per_day
        self.clock = clock  # tests me nakli ghadi de sakte hain
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._last_prune = clock()

    def hit(self, key: str) -> tuple[str, float] | None:
        """Allowed -> None (aur request gin li). Blocked -> (message, retry_after_seconds)."""
        now = self.clock()
        with self._lock:
            self._prune(now)
            hits = self._hits.setdefault(key, deque())
            # 24 ghante se purane timestamps hatao (deque ke left = sabse purane)
            while hits and hits[0] <= now - DAY:
                hits.popleft()

            if len(hits) >= self.per_day:
                return (
                    f"Daily limit reached ({self.per_day} questions per day). Please try again tomorrow.",
                    hits[0] + DAY - now,
                )

            recent = [t for t in hits if t > now - MINUTE]
            if len(recent) >= self.per_minute:
                return (
                    f"Too many questions ({self.per_minute} per minute). Please wait a moment and try again.",
                    recent[0] + MINUTE - now,
                )

            hits.append(now)  # sirf ALLOWED requests gini jaati hain
            return None

    def _prune(self, now: float) -> None:
        # Ghante me ek baar: jo IPs 24h se nahi aayin unhe memory se hatao,
        # warna har naya visitor hamesha ke liye dict me pada rahega
        if now - self._last_prune < 3600:
            return
        self._last_prune = now
        stale = [ip for ip, hits in self._hits.items() if not hits or hits[-1] <= now - DAY]
        for ip in stale:
            del self._hits[ip]


chat_limiter = RateLimiter(per_minute=10, per_day=100)


# FastAPI DEPENDENCY - /chat ke function se PEHLE chalti hai.
# HTTPException raise ki -> endpoint chalta hi nahi, seedha 429 JSON jaata hai:
#   {"detail": "Too many questions ..."}  + Retry-After header (seconds)
def enforce_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    blocked = chat_limiter.hit(ip)
    if blocked:
        message, retry_after = blocked
        raise HTTPException(
            status_code=429,
            detail=message,
            headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
        )


# -----------------------------------------------------------------------------
# REQUEST BODY - browser /chat pe kya bhejega, uska shape.
# FastAPI aane wale JSON ko ise match karta hai. Match nahi hua -> 422 error,
# humara function chalta hi nahi. Ek bhi "if" likhe bina validation.
#
# Ye limits API ke ABUSE se bachati hain (tumhare Groq tokens = tumhara quota):
#   question: 1-1000 characters -> khali sawaal ya 50 page ka text nahi
#   history: max 20 messages     -> koi 10,000 messages bhej ke tokens na jalaye
#   ChatMessage.content: max 4000 -> ek message me 2MB text nahi (schemas.py)
#   ChatMessage ka role Literal  -> "system" role inject karo to 422
# -----------------------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    # default_factory=list -> history na bhejo to khali list. "= []" nahi likhte
    # kyunki mutable default Python me bugs deta hai (sab requests same list share karein)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


# -----------------------------------------------------------------------------
# SAFE STREAM - stream ke BEECH me error aaye to kya karein?
#
# Streaming me HTTP status (200 OK) PEHLE hi chala jaata hai, jawab baad me.
# Groq beech me fail hua to ab 503 bhejne ka time nikal chuka hai.
# Isliye error pakad ke STREAM_ERROR_SENTINEL bhejte hain - frontend use
# pehchaan ke error + Retry dikhata hai (aur us adhure jawab ko history me
# nahi daalta).
#
# "except Exception" (sab kuch pakadna) aam taur pe bura hai, par API BOUNDARY
# pe sahi hai - user ko crash/traceback nahi dikhna chahiye.
# logger.exception() -> poora traceback TUMHARE terminal me (debug ke liye).
# (User Stop dabaye to GeneratorExit aata hai - wo Exception NAHI hai,
#  isliye yahan pakda nahi jaata. Sahi hai - wo error nahi hai.)
# -----------------------------------------------------------------------------
def safe_stream(first: str, rest: Iterator[str]) -> Iterator[str]:
    if first:
        yield first  # pehla tukda chat() me pehle hi nikaal liya tha
    try:
        # "yield from" = dusre generator ke saare tukde aage pass karo
        yield from rest
    except Exception:
        logger.exception("Chat stream failed mid-way")
        yield STREAM_ERROR_SENTINEL


# -----------------------------------------------------------------------------
# ENDPOINTS
#
# Sab "def" hain, "async def" NAHI. Kyun? Groq client SYNC hai (ruk ke wait
# karta hai). FastAPI "def" endpoints ko alag thread me chalata hai -> ek
# recruiter ka lamba jawab dusron ko block nahi karta.
# "async def" ke andar sync call karte to POORA server ruk jaata.
# (Common interview trap!)
# -----------------------------------------------------------------------------


# Deploy ke baad check karne ke liye "server zinda hai?"
@app.get("/health")
def health():
    return {"status": "ok", "candidate": app.state.resume.name}


# Parsed resume dekhna (frontend me kaam aayega). Yahan bhi phone hata diya.
@app.get("/profile")
def profile():
    return app.state.resume.model_dump(exclude={"phone"})


# Asli chat endpoint. POST kyunki data (sawaal + history) body me bhej rahe hain.
# dependencies=[...] -> rate limit check endpoint se PEHLE (limit par -> 429)
@app.post("/chat", dependencies=[Depends(enforce_rate_limit)])
def chat(request: ChatRequest):
    stream = stream_answer(app.state.system_prompt, request.history, request.question)

    # -------------------------------------------------------------------------
    # GENERATOR "PRIME" KARNA - pehla tukda yahin nikaal lo.
    # Generator banane se code chalta NAHI; next() pe pehli baar chalta hai.
    # Zyadatar errors (rate limit, galat key, Groq down) PEHLE token se pehle
    # aate hain. Agar yahin next() karein to status abhi bheja nahi gaya ->
    # asli 503 error de sakte hain (text me chhupa "sorry" nahi).
    # next(stream, "") -> jawab bilkul khaali ho to StopIteration ki jagah "".
    # -------------------------------------------------------------------------
    try:
        first = next(stream, "")
    except Exception:
        logger.exception("Chat failed before first chunk")
        return JSONResponse(
            status_code=503,
            content={"detail": "The AI service is temporarily unavailable. Please try again in a moment."},
        )

    # StreamingResponse generator ke har "yield" ko turant browser ko bhej deta hai
    return StreamingResponse(
        safe_stream(first, stream),
        media_type="text/plain; charset=utf-8",  # plain text tukde, UTF-8 me
    )


# Home page - browser me http://127.0.0.1:8000 kholo to chat UI milega.
# Frontend aur backend SAME server se -> CORS ki zaroorat nahi
# (CORS tab lagta hai jab page ek domain se aur API dusre domain se ho).
@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


# React (Vite) build: static/index.html upar wala "/" deta hai, aur uski
# JS/CSS files static/assets/ me hoti hain -> /assets/... URL pe serve.
# check_dir=False -> frontend build na hua ho tab bhi server start ho jaaye.
app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets", check_dir=False), name="assets")