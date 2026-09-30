import time

from app.resume import load_resume

start = time.perf_counter()
resume = load_resume()
elapsed = time.perf_counter() - start

print(resume.model_dump_json(indent=2))
print(f"\nTime: {elapsed:.2f}s")