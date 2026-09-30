# =============================================================================
# app/config.py
# Kaam: settings ek jagah - .env se GROQ_API_KEY padhna, Groq client banana,
#       aur model ka naam. Baaki files (llm.py, chat.py) yahin se import karti hain.
#
# FAIL FAST: key na ho to import hote hi error - server start hi nahi hoga,
# pehle recruiter ke sawaal pe crash hone se behtar. (Tests conftest.py me
# nakli key set karte hain, isliye wahan ye error nahi aata.)
# MODEL resume.py ki cache key me bhi jaata hai - badlo to resume dobara parse.
# =============================================================================
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in the environment variables.")

client = Groq(api_key=GROQ_API_KEY)
MODEL = "openai/gpt-oss-120b"
