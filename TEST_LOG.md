# Test log — actual runs

Executed on 15 October 2026. Every research run deliberately used the assignment
cutoff **23 September 2026**, not the machine's current date. All runs used the
same eight supplied documents and gpt-6.1-sol with medium reasoning through
Codex CLI 0.162.0-alpha.17.2. No company web research or live-data bonus was used.

| Run | Design | Time | Prose words | Fixture checks | Outcome |
|---|---|---:|---:|---:|---|
| v1 | Baseline research prompt, source IDs and quoted passages | 40.47 s model call | 166 | 4/8 | Unvalidated baseline saved |
| v2 | Explicit entity resolution, source hierarchy, recency and conflict handling | 44.02 s model call | 139 | 5/8 | Unvalidated baseline saved |
| v3 | Coverage guidance + deterministic evidence gates + skeptical review/repair | 72.72 s total | 313 | 8/8 | Accepted without repair |

## Run 1: a good model is not enough

Command:

```sh
python agent.py --ticker SRVCABLE --as-of 2026-09-23 --version v1 --out runs/v1
```

Observed: the model preferred the correct original revenue figures, rejected the
promotional blog's hidden instructions, excluded the unrelated cable-TV business,
and noticed the GST risk. Those traps did **not** fail in this run.

However, Snapshot had only two lines and no business description. Its revenue
conflict sentence mentioned the news figures but cited only the original release;
the quotation record did not support every part of that sentence. Promoter
pledging and collection risk were summarized without their useful numbers or
pledge denominator. The intended-appeal statement also lacked the specific
supporting quotation. Prose was too short for the configured acceptance gate.

Changed: v2 explicitly required 3–4 snapshot claims, all-source decisions,
primary-source precedence, entity checks, dated historical evidence, management
attribution, and an explicit question about source conflicts.

## Run 2: better selection, still incomplete communication

```sh
python agent.py --ticker SRVCABLE --as-of 2026-09-23 --version v2 --out runs/v2
```

Observed: it added the business description and both source citations for the
revenue conflict, and clearly distinguished the old 35% pledge report from the
new 4.1% figure. It still omitted the actual two conflicting revenue figures from
Open questions, the pledge denominator, and the 78-to-96-day collection change.
Only 139 prose words were generated, failing the length gate.

Changed: the final prompt explicitly requires denominator preservation, enough
detail to make each claim independently understandable, quantified latest results,
cash collection/funding, and material adverse disclosures. v3 adds an actual
review call and feeds mechanical/reviewer issues back for up to two repairs.
It cannot publish a v3 brief while those issues remain.

## Run 3: accepted final brief

```sh
python agent.py --ticker SRVCABLE --as-of 2026-09-23 --version v3 --out runs/v3
```

Observed: 313 prose words, all required sections, exact-quotation and source
decision validation passed; reviewer returned an empty issue list. Draft call:
58.77 seconds; review: 13.86 seconds. No repair was needed. Eight fixture checks
passed: business/results, explicit revenue conflict with both citations, current
pledging with its denominator, GST risk, quantified collection risk, unrelated
entity exclusion, promotional injection exclusion, and evidence on every claim.

The final brief was rendered automatically from `runs/v3/result.json`.
**No hand edits were made to its prose or Markdown.**

## Code-level checks

`python -m unittest discover -s tests -v`: **11 tests passed**. Tests mutate the
real accepted candidate to check rejection of fabricated quotations, unknown or
excluded sources, missing claim evidence, incomplete source decisions, and date
drift; they also check future-source removal, malformed input, and that the brief
is exactly the renderer output. An early test invocation before v3 had finished
could not find its result file; rerunning after generation passed all tests.

`evaluate.py` checks the known fictional fixture; it is separate from the agent
and does not feed expected answers to inference. Presence checks are not a proof
of semantic correctness. The model reviewer also has correlated blind spots.

Every run directory preserves the actual input, structured model output, source
packet and hashes, timing/token usage, validation reports and raw CLI events.
No model tool calls were observed. Baseline outputs are explicitly named
`brief-unvalidated.md`; only the accepted final is `runs/v3/brief.md`.

## Recording validation

Desktop capture returned blank frames in this environment, so the final recording
uses Playwright to capture the actual rendered local browser tour. The tour starts
a fresh model-backed run and labels the saved v3 evidence views. It is scripted,
with on-screen captions; it does not impersonate a human presenter. The recording
script and browser-error log are included for reproducibility.

The fresh run captured during the recording completed in about 66 seconds and
passed the agent's quotation gates and reviewer. Its additional fixture evaluation
was **7/8**: it correctly distinguished the cable-TV business, but classified that
document as `context` and cited it only to explain the identity distinction,
rather than marking it `exclude` as the strict fixture check requires. It did not
attribute the cable-TV penalty to the listed company. This repeat shows a real
limitation: source-category policy can drift even when the core identity judgment
is correct, and the model reviewer did not catch the label-policy deviation.
That run is preserved in `runs/demo-1792056503542200100`; the submission brief
remains the original accepted, 8/8 `runs/v3/brief.md` and was not replaced or edited.
The viewer explicitly labels saved evidence and brief views as the accepted v3 run.

The final MP4 is **2 minutes 45.56 seconds**, 1600×900, H.264, with chapter captions
and no audio. Browser error log: empty. Sampled frames were inspected for actual
rendered content, readable text, the research brief, and the limitation chapter.
