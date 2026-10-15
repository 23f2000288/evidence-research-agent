# Submission text

## Build description

I built a Python research agent that accepts an NSE ticker and supplied documents,
accounts for every source, reconciles conflicting evidence, and writes a concise
Markdown brief. Each claim carries an exact supporting quotation. Code validates
the evidence record and builds the citations; a separate model review checks
semantic support and can request repairs before the final brief is emitted.

## Model and tools

Python standard library; gpt-6.1-sol at medium reasoning through the authenticated
Codex CLI; JSON Schema for structured output. A local HTML viewer and Playwright
are used for the demo recording. No web research was performed on the fictional
company. The model was available through the existing login and supported the
structured drafting/review workflow without an additional API-key setup.

## Research brief

Paste the complete contents of **runs/v3/brief.md**, unchanged.

Hand edits: **None.** The Markdown was generated deterministically from the
model's accepted evidence record.

## Iteration summary

I ran three prompt/design variants. v1 handled the obvious misleading sources but
omitted the business description and left parts of some claims incompletely cited.
v2 improved source hierarchy, identity and recency, but was still too terse and
omitted useful figures and the pledge denominator. v3 added explicit coverage,
exact-quote/source/date validation, and a separate skeptical reviewer with a repair
loop. Fixture checks improved from 4/8 to 5/8 to 8/8. All 11 code tests passed.
The full observed log and original outputs are preserved in TEST_LOG.md and runs/.
An extra run for the recording scored 7/8 on the strict fixture checks: it correctly
distinguished the unrelated business but labelled its source as context rather
than exclude. This policy drift is documented in the log; the submitted brief is
the unchanged original 8/8 v3 result.

## Design decision

Keep the evidence record separate from the polished brief. A source link alone
can hide weak support. Requiring an exact quotation for every claim makes support
inspectable, and deterministic citation rendering avoids invented source links.
All eight source decisions remain visible, including rejected documents.

## Limitation

A genuine quotation can be misinterpreted. The reviewer uses the same model family
and may share the drafter's blind spots. The agent trusts supplied metadata and
cannot independently authenticate a filing or calculate valuation without more
data. This is a research aid requiring human review.

## Recording disclosure

The 2–3 minute recording is an actual scripted browser capture with on-screen
chapter captions. It starts a fresh model-backed run, then walks through the
accepted v3 evidence audit, test iterations, brief, and limitation. It is not a
recording of a person speaking. No synthetic voice is used.

## Links still needed for the form

The build and recording have been prepared locally. Add the GitHub repository URL
and the uploaded recording's viewable link after publishing them to the account
you want to use. Do not submit local filesystem paths as public links.
