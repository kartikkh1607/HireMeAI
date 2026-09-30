# =============================================================================
# tests/test_resume.py - resume.py ke tests. Groq ko EK BHI call nahi.
#   1. Committed cache FRESH hai? (warna production startup pe Groq call)
#   2. cache_key har us cheez pe badalti hai jo output badal sakti hai
#   3. certifications wala filter asli skills nahi hatata
# =============================================================================
import json

import pytest

import app.resume as resume
from app.schemas import Resume

STALE_CACHE = (
    "Committed resume cache is stale - run `uv run python eval_resume.py` and commit data/resume_cache.json"
)


# ----------------------------------------------------------------- cache freshness
def test_committed_cache_is_fresh():
    # Prompt / model / PARSER_VERSION / PDF badla aur eval_resume.py chalana
    # bhool gaye -> production phir startup pe Groq call karega (wahi bug jisse
    # Render deploy fail hua tha). Ye test us galti ko commit se pehle pakadta hai.
    cached = json.loads(resume.CACHE_PATH.read_text(encoding="utf-8"))
    assert cached.get("cache_key") == resume.cache_key(resume.RESUME_PATH), STALE_CACHE

    # Schema badla ho to load_resume() bhi dobara parse karta hai -> wo bhi stale
    parsed = Resume.model_validate(cached["resume"])
    # PRIVACY: cache repo me public hai - phone kabhi nahi hona chahiye
    assert parsed.phone is None


# ----------------------------------------------------------------- cache key
@pytest.fixture
def resume_file(tmp_path):
    # Asli PDF ki zaroorat nahi - cache_key sirf raw bytes hash karta hai
    path = tmp_path / "resume.pdf"
    path.write_bytes(b"fake resume bytes")
    return path


def test_cache_key_is_stable(resume_file):
    assert resume.cache_key(resume_file) == resume.cache_key(resume_file)


@pytest.mark.parametrize("name", ["PARSER_PROMPT", "MODEL", "PARSER_VERSION"])
def test_cache_key_changes_when_input_changes(monkeypatch, resume_file, name):
    before = resume.cache_key(resume_file)
    # resume.py ke module-level naam badlo (cache_key() wahi padhta hai)
    monkeypatch.setattr(resume, name, getattr(resume, name) + " changed")
    assert resume.cache_key(resume_file) != before


def test_cache_key_changes_when_file_changes(resume_file):
    before = resume.cache_key(resume_file)
    resume_file.write_bytes(b"updated resume bytes")
    assert resume.cache_key(resume_file) != before


# ----------------------------------------------------------------- certs filter
def make_resume(skills, certifications):
    return Resume(
        name=None,
        email=None,
        phone=None,
        location=None,
        summary=None,
        skills=skills,
        experiences=[],
        projects=[],
        education=[],
        certifications=certifications,
        achievements=[],
        links=[],
    )


def test_remove_certs_from_skills_keeps_real_skills():
    # Asli resume jaise cert names (en dash "–" ke saath)
    certs = [
        "AWS Certified CloudOps Engineer – Associate (April 2026)",
        "AWS Certified Data Engineer – Associate (April 2026)",
        "AWS Certified Cloud Practitioner – Amazon Web Services (December 2025)",
    ]
    skills = [
        "AWS",
        "Python",
        "Cloud",
        "AWS (Lambda, API Gateway)",  # akela "aws" bachta hai -> asli skill
        "AWS CloudOps Engineer",  # v3 bug: koi marker nahi, par cert list me hai
        "AWS Data Engineer (Associate)",  # marker "(associate)"
        "AWS Certified Cloud Practitioner",  # marker "certified"
    ]

    cleaned = resume.remove_certs_from_skills(make_resume(skills, certs))

    assert cleaned.skills == ["AWS", "Python", "Cloud", "AWS (Lambda, API Gateway)"]
    assert cleaned.certifications == certs  # certs khud nahi chhede
