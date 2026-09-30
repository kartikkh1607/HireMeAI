# =============================================================================
# tests/conftest.py
# pytest ye file HAR test file se pehle load karta hai - shared setup yahan.
#
# app.config import hote hi GROQ_API_KEY check karta hai (na ho to crash).
# CI / naye laptop pe .env nahi hoti, isliye nakli key de dete hain.
# Tests me Groq KABHI call nahi hota (sab monkeypatch hai), to key asli ho
# ya nakli - farak nahi padta. load_dotenv() pehle se set env ko override
# nahi karta, isliye ye values jeet-ti hain.
# =============================================================================
import os

os.environ.setdefault("GROQ_API_KEY", "test-key-not-used")
# .env me ENV=production ho tab bhi tests "local" mode me chalein (/docs on)
os.environ["ENV"] = "test"
