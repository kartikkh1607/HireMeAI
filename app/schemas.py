from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Experience(StrictModel):
    company: str | None
    role: str | None
    duration: str | None
    highlights: list[str]
    skills_used: list[str]


class Project(StrictModel):
    name: str
    description: str | None
    highlights: list[str]
    tech_stack: list[str]
    link: str | None


class Education(StrictModel):
    institution: str
    degree: str | None
    duration: str | None
    score: str | None
    coursework: list[str]


class Resume(StrictModel):
    name: str | None
    email: str | None
    phone: str | None
    location: str | None
    summary: str | None
    skills: list[str]
    experiences: list[Experience]
    projects: list[Project]
    education: list[Education]
    certifications: list[str]
    achievements: list[str]
    links: list[str]