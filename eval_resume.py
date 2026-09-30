# =============================================================================
# eval_resume.py - resume parsing ka GOLDEN SET eval
# Har check ek known-correct answer hai: humne resume khud padh ke pakka kiya
# ki usme 7 links, 3 projects, hackathon wagairah hain.
# Prompt / schema / model / filter kuch bhi badlo -> ye chalao -> FAIL = kuch toota.
#
# RULE: eval ka logic filter se INDEPENDENT hona chahiye. Agar eval bhi wahi
# normalize() use kare jo filter karta hai, to filter ki galti eval me bhi
# hogi aur kabhi pakdi nahi jayegi. Isliye yahan golden words haath se likhe hain.
# =============================================================================
from app.resume import load_resume

resume = load_resume()

# Resume padh ke chune hue words jo skills me KABHI nahi aane chahiye
CERT_WORDS = ("practitioner", "cloudops", "data engineer", "certified")

checks = {
    "7 links extracted": len(resume.links) == 7,
    "every project has a link": all(p.link for p in resume.projects),
    "every project has 3+ highlights": all(len(p.highlights) >= 3 for p in resume.projects),
    "hackathon in achievements": any("Hackathon" in a for a in resume.achievements),
    "coursework present": bool(resume.education and resume.education[0].coursework),
    # v3 me ye check sirf "practitioner" dekhta tha -> "AWS CloudOps Engineer"
    # skills me hone ke bawajood PASS aata tha. Kamzor check = jhootha PASS.
    "no certifications in skills": not any(
        word in s.lower() for s in resume.skills for word in CERT_WORDS
    ),
    "cert dates separated": all("AssociateApril" not in c for c in resume.certifications),
}

for name, passed in checks.items():
    print("PASS" if passed else "FAIL", "-", name)

# True ko Python 1 ginta hai -> sum = kitne pass hue
print(f"\n{sum(checks.values())}/{len(checks)} checks passed")

# Koi FAIL ho to skills print karo, debug aasan ho
if not checks["no certifications in skills"]:
    print("\nSkills:", resume.skills)