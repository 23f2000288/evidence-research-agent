"""Create a local upload bundle without caches or intermediate media."""
import hashlib
from pathlib import Path
import zipfile
from agent import ROOT

target = ROOT.parent / "Research_Agent_Submission.zip"
files = []
for path in ROOT.rglob("*"):
    if not path.is_file():
        continue
    relative = path.relative_to(ROOT)
    if any(part in {"__pycache__", ".git", "node_modules", ".venv"} for part in relative.parts):
        continue
    if relative.parts[0] == "demo" and path.suffix in {".webm", ".png", ".wav"}:
        continue
    if path.name == "capture-test.mp4":
        continue
    files.append(path)
with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(files):
        archive.write(path, Path("research-agent") / path.relative_to(ROOT))
with zipfile.ZipFile(target) as archive:
    assert archive.testzip() is None
print(f"Saved {target}")
print(f"{len(files)} files, {target.stat().st_size:,} bytes")
print(f"SHA256 {hashlib.sha256(target.read_bytes()).hexdigest()}")
