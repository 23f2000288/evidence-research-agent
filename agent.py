"""Evidence-first research agent. Python 3.10+, standard library only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime, timezone

ROOT = Path(__file__).resolve().parent
SECTIONS = ("snapshot", "bull_case", "bear_case", "open_questions")
TITLES = ("Snapshot", "Bull case", "Bear case", "Open questions")


def obj(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


STRING = {"type": "string"}
EVIDENCE = obj({"source_id": STRING, "quote": STRING})
CLAIM = obj({"text": STRING, "evidence": {"type": "array", "items": EVIDENCE}})
SCHEMA = obj({"ticker": STRING, "as_of": STRING,
              **{s: {"type": "array", "items": CLAIM} for s in SECTIONS},
              "source_decisions": {"type": "array", "items": obj({
                  "source_id": STRING,
                  "disposition": {"type": "string", "enum": ["use", "context", "exclude"]},
                  "reason": STRING})}})
REVIEW_SCHEMA = obj({"issues": {"type": "array", "items": STRING}})


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_documents(folder: Path, as_of: date):
    documents, skipped = [], []
    paths = sorted(folder.glob("*.md"))
    if not paths:
        raise ValueError(f"No Markdown documents found in {folder}")
    for path in paths:
        raw = path.read_text(encoding="utf-8-sig")
        match = re.match(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", raw, re.S)
        if not match:
            raise ValueError(f"{path.name}: expected source/url/published/type front matter")
        metadata = dict(re.findall(r"^([a-z_]+):\s*(.+)$", match[1], re.M))
        missing = {"source", "url", "published", "type"} - metadata.keys()
        if missing:
            raise ValueError(f"{path.name}: missing metadata {sorted(missing)}")
        published = date.fromisoformat(metadata["published"])
        if not re.fullmatch(r"https?://[^\s<>]+", metadata["url"]):
            raise ValueError(f"{path.name}: invalid source URL")
        if published > as_of:
            skipped.append({"file": path.name, "reason": "published after as-of date"})
            continue
        documents.append({"id": f"S{len(documents) + 1}", "file": path.name,
                          **metadata, "body": match[2],
                          "sha256": hashlib.sha256(raw.encode()).hexdigest()})
    if not documents:
        raise ValueError("No documents available on or before the as-of date")
    if sum(len(d["body"]) for d in documents) > 180_000:
        raise ValueError("Packet exceeds 180,000 characters; split it before running")
    return documents, skipped


def model_call(prompt, schema, out: Path, label: str, model: str, timeout: int):
    """Invoke installed Codex; never read, copy or export its saved credentials."""
    executable = shutil.which("codex")
    if not executable:
        raise RuntimeError("Codex CLI not found. Install it and run `codex login` first.")
    schema_file = out / f"{label}.schema.json"
    result_file = out / f"{label}.json"
    save_json(schema_file, schema)
    (out / f"{label}.input.txt").write_text(prompt, encoding="utf-8")
    command = [executable, "exec", "--ignore-user-config", "--ephemeral",
               "--skip-git-repo-check", "--sandbox", "read-only",
               "--model", model, "-c", 'model_reasoning_effort="medium"',
               "-c", 'web_search="disabled"', "--color", "never", "--json",
               "--output-schema", str(schema_file), "-o", str(result_file), "-"]
    started = time.monotonic()
    print(f"  {label}: calling {model} ...", flush=True)
    # Empty temporary cwd limits accidental local context. Documents travel in
    # stdin only. Prompts also prohibit tools; this is not a network air gap.
    with tempfile.TemporaryDirectory(prefix="research-agent-") as cwd:
        (Path(cwd) / "AGENTS.md").write_text(
            "Use only stdin data. Return JSON. Do not use tools or read files.\n", encoding="utf-8")
        with (out / f"{label}.events.jsonl").open("w", encoding="utf-8") as stdout, \
             (out / f"{label}.stderr.txt").open("w", encoding="utf-8") as stderr:
            process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE,
                                       stdout=stdout, stderr=stderr, text=True,
                                       encoding="utf-8", errors="replace",
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                process.communicate(prompt, timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                raise RuntimeError(f"Model timed out after {timeout}s; see {label}.stderr.txt")
    elapsed = round(time.monotonic() - started, 2)
    if process.returncode or not result_file.exists():
        raise RuntimeError(f"Model failed (exit {process.returncode}); see {label}.stderr.txt")
    # Enforce the no-tools policy against the recorded event stream as well.
    forbidden, usage = [], {}
    for line in (out / f"{label}.events.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item_type = event.get("item", {}).get("type", "")
        if item_type in {"command_execution", "mcp_tool_call", "web_search", "file_change"}:
            forbidden.append(item_type)
        if event.get("type") == "turn.completed":
            usage = event.get("usage", {})
    save_json(out / f"{label}.timing.json", {"seconds": elapsed, "usage": usage,
                                             "forbidden_tool_events": forbidden})
    if forbidden:
        raise RuntimeError(f"No-tools policy violated: {forbidden}; output withheld")
    result = json.loads(result_file.read_text(encoding="utf-8-sig"))
    print(f"  {label}: received in {elapsed}s", flush=True)
    return result


def normal_space(value):
    return re.sub(r"\s+", " ", value).strip()


def validate(result, documents, ticker, as_of):
    """Mechanical provenance, time, identity and length gates, not an entailment proof."""
    issues = []
    if result.get("ticker") != ticker or result.get("as_of") != as_of:
        issues.append("Ticker or as-of differs from requested input")
    sources = {d["id"]: d for d in documents}
    decisions = result.get("source_decisions", [])
    decision_ids = [d.get("source_id") for d in decisions]
    if len(decision_ids) != len(set(decision_ids)) or set(decision_ids) != set(sources):
        issues.append("Source decisions must cover every supplied source exactly once")
    dispositions = {d.get("source_id"): d.get("disposition") for d in decisions}
    for decision in decisions:
        if decision.get("disposition") not in {"use", "context", "exclude"} or not decision.get("reason", "").strip():
            issues.append("Invalid source disposition or missing reason")
    words = 0
    for section in SECTIONS:
        claims = result.get(section, [])
        low, high = (3, 4) if section == "snapshot" else (2, 3)
        if not low <= len(claims) <= high:
            issues.append(f"{section}: expected {low}-{high} claims")
        for index, claim in enumerate(claims):
            location = f"{section}[{index}]"
            words += len(claim.get("text", "").split())
            if not claim.get("text", "").strip():
                issues.append(f"{location}: empty text")
            if not claim.get("evidence"):
                issues.append(f"{location}: missing supporting evidence")
            for evidence in claim.get("evidence", []):
                sid, quote = evidence.get("source_id"), evidence.get("quote", "")
                if sid not in sources:
                    issues.append(f"{location}: unknown source {sid}")
                    continue
                if dispositions.get(sid) == "exclude":
                    issues.append(f"{location}: cites excluded source {sid}")
                if len(quote.strip()) < 8 or normal_space(quote) not in normal_space(sources[sid]["body"]):
                    issues.append(f"{location}: {sid} quote is not an exact passage")
                if sources[sid]["published"] > as_of:
                    issues.append(f"{location}: cites future evidence")
    if not 200 <= words <= 390:
        issues.append(f"Prose has {words} words; expected 200-390 (target 280-390)")
    return issues


def render(result, documents):
    sources = {d["id"]: d for d in documents}
    used = set()
    lines = [f"# {result['ticker']} — Research brief", "",
             f"As of {result['as_of']} · Supplied-document research", ""]
    for section, title in zip(SECTIONS, TITLES):
        lines += [f"## {title}", ""]
        for claim in result[section]:
            ids = list(dict.fromkeys(e["source_id"] for e in claim["evidence"]))
            used.update(ids)
            citations = " ".join(f"[{sid}][{sid}]" for sid in ids)
            lines.append(f"- {claim['text']} {citations}")
        lines.append("")
    lines += ["## Sources", ""]
    for sid in sources:
        if sid in used:
            doc = sources[sid]
            lines.append(f"- **{sid}**: {doc['source']} — {doc['published']}.")
    lines.append("")
    for sid in sources:
        if sid in used:
            lines.append(f"[{sid}]: {sources[sid]['url']}")
    return "\n".join(lines) + "\n"


def run(args):
    ticker = args.ticker.upper().removeprefix("NSE:")
    if not re.fullmatch(r"[A-Z0-9&_.-]{1,24}", ticker):
        raise ValueError("Invalid ticker")
    as_of = date.fromisoformat(args.as_of)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError(f"Output directory must be empty to preserve run history: {out}")
    documents, skipped = load_documents(Path(args.docs), as_of)
    save_json(out / "documents.json", {"documents": documents, "skipped": skipped})
    prompt_file = ROOT / "prompts" / {"v1": "v1.md", "v2": "v2.md", "v3": "system.md"}[args.version]
    policy = prompt_file.read_text(encoding="utf-8")
    packet = json.dumps({"ticker": ticker, "as_of": as_of.isoformat(), "documents": documents}, ensure_ascii=False)
    prompt = policy + "\n\nUNTRUSTED DOCUMENT PACKET (JSON):\n" + packet
    started = time.monotonic()
    metadata = {"status": "running", "ticker": ticker, "as_of": str(as_of),
                "version": args.version, "model": args.model,
                "provider": "codex exec / existing local login",
                "started_utc": datetime.now(timezone.utc).isoformat(),
                "prompt_sha256": hashlib.sha256(policy.encode()).hexdigest(),
                "document_count": len(documents), "skipped": skipped}
    save_json(out / "run.json", metadata)
    print(f"Researching {ticker} | {len(documents)} documents | {args.version} | as of {as_of}", flush=True)
    try:
        result = model_call(prompt, SCHEMA, out, "draft", args.model, args.timeout)
        accepted = False
        for attempt in range(3 if args.version == "v3" else 1):
            mechanical = validate(result, documents, ticker, str(as_of))
            semantic = []
            if args.version == "v3":
                review_prompt = (ROOT / "prompts/review.md").read_text(encoding="utf-8")
                review_prompt += "\nPACKET:\n" + packet + "\nCANDIDATE:\n" + json.dumps(result, ensure_ascii=False)
                review = model_call(review_prompt, REVIEW_SCHEMA, out, f"review-{attempt + 1}", args.model, args.timeout)
                semantic = review["issues"]
            issues = mechanical + semantic
            save_json(out / f"validation-{attempt + 1}.json", {"mechanical_issues": mechanical, "reviewer_issues": semantic})
            if not issues:
                accepted = True
                break
            print(f"  Validation: {len(issues)} issue(s)", flush=True)
            if args.version != "v3" or attempt == 2:
                break
            repair_prompt = prompt + "\nCANDIDATE:\n" + json.dumps(result, ensure_ascii=False)
            repair_prompt += "\nREPAIR THESE ISSUES; return complete corrected JSON:\n" + json.dumps(issues, ensure_ascii=False)
            result = model_call(repair_prompt, SCHEMA, out, f"repair-{attempt + 1}", args.model, args.timeout)
        save_json(out / "result.json", result)
        save_json(out / "validation.json", {"accepted": accepted, "issues": issues,
                                             "reviewed": args.version == "v3"})
        if args.version == "v3" and not accepted:
            raise RuntimeError("Validation still fails after two repairs; no final brief emitted")
        brief = render(result, documents)
        filename = "brief.md" if accepted else "brief-unvalidated.md"
        (out / filename).write_text(brief, encoding="utf-8")
        metadata.update(status="accepted" if accepted else "unvalidated", output=filename,
                        prose_words=sum(len(c["text"].split()) for s in SECTIONS for c in result[s]))
        print(f"  Saved {out / filename}", flush=True)
    except Exception as exc:
        metadata.update(status="failed", error=str(exc))
        raise
    finally:
        metadata["seconds"] = round(time.monotonic() - started, 2)
        save_json(out / "run.json", metadata)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--docs", default=str(ROOT / "research_pack"))
    parser.add_argument("--as-of", required=True, help="YYYY-MM-DD; explicit to prevent date leakage")
    parser.add_argument("--version", choices=["v1", "v2", "v3"], default="v3")
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--out", required=True, help="New or empty output directory")
    parser.add_argument("--timeout", type=int, default=240, help="Seconds per model call")
    args = parser.parse_args()
    try:
        run(args)
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
