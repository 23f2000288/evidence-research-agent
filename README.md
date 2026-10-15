# Evidence Research Agent

An agent that takes an NSE ticker and a folder of Markdown documents, reconciles
the evidence, and produces a concise research brief with claim-level citations.
The included test company, Sarvottam Cables (SRVCABLE), is fictional.

## Run

Requires Python 3.10+ and the Codex CLI, installed and authenticated with
`codex login`. The agent itself has **no Python package dependencies**. Existing
Codex account usage applies; this is not a free offline model. Credentials stay
in the CLI's authentication store and are never bundled in this project.

```sh
python agent.py --ticker SRVCABLE --docs research_pack --as-of 2026-09-23 --out runs/my-run
```

Use a new output directory for every run. Default is the final `v3` design.
Select another locally available model with `--model MODEL_NAME`. Other tickers
use the same pipeline; put their documents in a separate folder. No SRVCABLE facts
or special filenames are hardcoded in the agent. The fixture checks in
`evaluate.py` are intentionally specific to the assignment.

Each `.md` input must start with `---` front matter containing `source`, `url`,
`published` (YYYY-MM-DD), and `type`. See `research_pack/` for examples. Sources
published after the as-of date are excluded before inference and logged. The
runner accepts up to 180,000 body characters and fails clearly on invalid inputs.

## Model and design

Actual runs used **gpt-6.1-sol**, medium reasoning, through `codex exec`.
It was available through the existing local login and handled conflicting
evidence and structured outputs in one compact model pipeline. Using the same
model for drafting and review keeps setup simple, but their errors can correlate.
No model comparison or claim of optimal cost/accuracy is made.

The separate research instruction file is [prompts/system.md](prompts/system.md).
It is passed as task instructions through CLI stdin; it does not replace Codex's
own privileged system instructions. The separate skeptical reviewer prompt is
[prompts/review.md](prompts/review.md). Earlier prompts are preserved as `v1.md`
and `v2.md`.

1. **Ingest:** parse source metadata, preserve document hashes, apply the date cutoff.
2. **Draft with an evidence record:** account for every document as use, context,
   or exclude; write claims with exact quoted passages. Prefer relevant original
   evidence over secondary headlines; keep historical facts dated.
3. **Validate:** check quotation existence, source IDs, excluded citations, complete
   source decisions, ticker/date echoes, section sizes and prose length.
4. **Review:** a separate model call checks semantic support, attribution,
   identity, recency, conflicts, and material omissions. Up to two repairs are
   allowed; unresolved failures withhold the final v3 brief.
5. **Render:** generate Markdown and source links deterministically from the
   accepted evidence record. No hand editing of the final brief.

The runner disables web search, ignores user CLI configuration, uses a temporary
working directory and a read-only sandbox, and instructs the model to use no
tools. It checks the event stream for tool use and rejects such runs. This is
defense in depth, **not** a complete hostile-document security sandbox. The
documents are still sent to the selected model provider. All observed test runs
had no tool-use events.

The CLI integration follows the official
[non-interactive execution documentation](https://developers.openai.com/codex/noninteractive).

## Required submission artifacts

- **Exact generated brief:** [runs/v3/brief.md](runs/v3/brief.md).
- **Three-run test log:** [TEST_LOG.md](TEST_LOG.md), with preserved `runs/v1`,
  `runs/v2`, and `runs/v3` outputs.
- **Evidence record:** [runs/v3/result.json](runs/v3/result.json).
- **Source selection:** `source_decisions` in the evidence record.
- **Recording:** `demo/screen-recording.mp4`, an actual scripted browser capture
  of the local viewer, with on-screen chapter captions. It starts a fresh model
  run; the evidence and brief views are explicitly labelled as the accepted v3
  run. No personal voice narration is claimed.
- **Form-ready explanations:** [SUBMISSION.md](SUBMISSION.md).

The packet's `.example` source URLs are deliberately fictional, so the preserved
local documents and quotation record are the auditable evidence.

## Check or demonstrate

```sh
python -m unittest discover -s tests -v
python evaluate.py runs/v1 runs/v2 runs/v3
python demo_server.py
```

Open `http://127.0.0.1:8765` for the local viewer. It binds to loopback only. Its
Run button launches a fresh v3 run using your local login. The viewer does not
upload documents. The research process sends the packet to the model provider.

The optional recording script uses Playwright (`npm install playwright`,
`npx playwright install chromium`, then `node demo/record_demo.cjs`). This
dependency is only for recording, not the agent. `?tour=1` starts the timed tour
and a real run. MP4 conversion uses FFmpeg; the supplied recording is ready to view.

## Limits

Exact quotation matching proves that a passage exists, not that a conclusion is
true. The reviewer can miss mistakes. Source metadata is supplied, not
independently authenticated. No live market data, valuation model, OCR, PDF
parsing, or document retrieval service is included. Larger packets need a
retrieval/chunking design. One fictional fixture and three design runs are useful
development evidence, not a broad financial-research accuracy benchmark.
