# =============================================================================
# app/schemas.py
# Kaam: project ke saare data ka "shape" (structure) define karna.
# Har file yahin se import karti hai -> ek jagah badlo, sab jagah lagu.
#
# Do tarah ke models hain:
#   1. LLM OUTPUT models (StrictModel se bane) -> Resume, Project, etc.
#      Ye Groq ko JSON schema ki tarah jaate hain (strict mode).
#   2. APP models (normal BaseModel) -> ChatMessage
#      Ye sirf humare code/API ke andar use hote hain, LLM ko schema nahi jaata.
# =============================================================================

from typing import Literal  # "sirf ye fixed values allowed hain" batane ke liye

from pydantic import BaseModel, ConfigDict, Field


# -----------------------------------------------------------------------------
# Base class - saare LLM output models isse inherit karte hain.
# extra="forbid" -> JSON schema me "additionalProperties": false aa jaata hai.
# Matlab: model apni taraf se koi extra field nahi jod sakta.
# Groq ke strict mode ki ye ek requirement hai.
# Base class isliye banayi taaki ye line har class me repeat na karni pade.
# -----------------------------------------------------------------------------
class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# -----------------------------------------------------------------------------
# STRICT MODE KE 2 RULES (neeche har class me dikhenge):
#   1. Koi default value nahi (na "= None", na "= []")
#      -> strict mode me har field REQUIRED honi chahiye.
#   2. Jo value missing ho sakti hai -> "str | None"
#      -> model khud null bhejega. Field hamesha rahegi, value null ho sakti hai.
#   List ke liye None ki zaroorat nahi - khali ho to [] bhejega.
# -----------------------------------------------------------------------------


# Ek job / internship / freelance kaam
class Experience(StrictModel):
    company: str | None
    role: str | None
    duration: str | None  # str rakha, date nahi - resumes me format alag-alag hota hai
    highlights: list[str]  # bullet points
    skills_used: list[str]


# Ek project.
# description vs highlights alag kyun? Pehle sirf description tha, to model
# kabhi subtitle daalta tha kabhi bullets -> REGRESSION hua tha.
# Ek field = ek matlab. Ambiguous field = har run me alag output.
class Project(StrictModel):
    name: str  # None nahi - bina naam ka project ho hi nahi sakta
    description: str | None  # ek line ka subtitle ("Recipe Browser Android Application")
    highlights: list[str]  # saare bullet points
    tech_stack: list[str]
    link: str | None  # GitHub repo - PDF annotations se aata hai


# Ek degree / college
class Education(StrictModel):
    institution: str
    degree: str | None
    duration: str | None
    score: str | None  # str kyunki "8.17", "85%", "8.17/10" - sab format chalne chahiye
    coursework: list[str]  # baad me add hua - pehle ye data chup-chaap gayab tha


# -----------------------------------------------------------------------------
# Poora resume - baaki saare models isme nest hote hain.
# JSON schema me nested models "$defs" + "$ref" ban jaate hain.
#
# SCHEMA COVERAGE LESSON: strict mode me LLM SIRF wahi fields bhar sakta hai
# jo yahan hain. Resume ka koi section yahan nahi hai -> uska data bina kisi
# error ke drop ho jayega (achievements aur coursework ke saath yahi hua tha).
# -----------------------------------------------------------------------------
class Resume(StrictModel):
    name: str | None
    email: str | None
    phone: str | None  # parse hota hai, par chat.py LLM ko nahi bhejta (privacy)
    location: str | None
    summary: str | None
    skills: list[str]  # resume.py ka filter isme se certifications hatata hai
    experiences: list[Experience]  # nested model ki list
    projects: list[Project]
    education: list[Education]
    certifications: list[str]
    achievements: list[str]  # hackathon, LeetCode wagairah
    links: list[str]  # saare http/https URLs


# -----------------------------------------------------------------------------
# Chat ka ek message (history me use hota hai).
# Ye StrictModel NAHI hai - ye LLM ka output schema nahi hai, bas humara type.
#
# SECURITY: role sirf "user" ya "assistant" ho sakta hai.
# Agar koi browser/API se history me {"role": "system", ...} bheje (apne rules
# inject karne ke liye), Pydantic reject kar dega -> FastAPI 422 error.
# Ek bhi "if" likhe bina security check ho gaya - Literal ka kamaal.
#
# ABUSE LIMIT: content max 4000 characters. Pehle sirf question (1000) limited
# tha - koi history me 20 x 2MB text bhej ke tumhare Groq tokens jala sakta tha.
# -----------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)