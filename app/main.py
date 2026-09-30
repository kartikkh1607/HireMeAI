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
from collections.abc import Iterator
from contextlib import asynccontextmanager  # lifespan function banane ke liye
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse  # file / tukdon me jawab
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


# title /docs page pe dikhta hai
app = FastAPI(title="HireMeAI", lifespan=lifespan)


# -----------------------------------------------------------------------------
# REQUEST BODY - browser /chat pe kya bhejega, uska shape.
# FastAPI aane wale JSON ko ise match karta hai. Match nahi hua -> 422 error,
# humara function chalta hi nahi. Ek bhi "if" likhe bina validation.
#
# Ye limits API ke ABUSE se bachati hain (tumhare Groq tokens = tumhara quota):
#   question: 1-1000 characters -> khali sawaal ya 50 page ka text nahi
#   history: max 20 messages     -> koi 10,000 messages bhej ke tokens na jalaye
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
# Groq beech me fail hua to ab 500 error bhejne ka time nikal chuka hai.
# Isliye error ko stream ke andar pakad ke ek saaf message bhej dete hain.
#
# "except Exception" (sab kuch pakadna) aam taur pe bura hai, par API BOUNDARY
# pe sahi hai - user ko crash/traceback nahi dikhna chahiye.
# logger.exception() -> poora traceback TUMHARE terminal me (debug ke liye),
# user ko sirf friendly message.
# -----------------------------------------------------------------------------
def safe_stream(question: str, history: list[ChatMessage]) -> Iterator[str]:
    try:
        # "yield from" = dusre generator ke saare tukde aage pass karo
        yield from stream_answer(app.state.system_prompt, history, question)
    except Exception:
        logger.exception("Chat stream failed")
        yield "\n\n[Sorry, something went wrong. Please try again.]"


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
@app.post("/chat")
def chat(request: ChatRequest):
    # StreamingResponse generator ke har "yield" ko turant browser ko bhej deta hai
    return StreamingResponse(
        safe_stream(request.question, request.history),
        media_type="text/plain; charset=utf-8",  # plain text tukde, UTF-8 me
    )


# Home page - browser me http://127.0.0.1:8000 kholo to chat UI milega.
# Frontend aur backend SAME server se -> CORS ki zaroorat nahi
# (CORS tab lagta hai jab page ek domain se aur API dusre domain se ho).
@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")