from app.resume import load_resume

resume = load_resume()

checks = {
    "7 links extracted": len(resume.links) == 7,
    "every project has a link": all(p.link for p in resume.projects),
    "every project has 3+ highlights": all(len(p.highlights) >= 3 for p in resume.projects),
    "hackathon in achievements": any("Hackathon" in a for a in resume.achievements),
    "coursework present": bool(resume.education and resume.education[0].coursework),
    "no certifications in skills": not any("practitioner" in s.lower() for s in resume.skills),
    "cert dates separated": all("AssociateApril" not in c for c in resume.certifications),
}

for name, passed in checks.items():
    print("PASS" if passed else "FAIL", "-", name)

print(f"\n{sum(checks.values())}/{len(checks)} checks passed")