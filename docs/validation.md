# Validation record

Initial checks on 1 October 2026 and UI polish checks on 2 October 2026,
Windows, Python 3.12.0. Live results and offline fixture results are kept separate.
This document records technical verification; the recorded walkthrough is linked
in the README.

## Source, graph and offline checks

The seed validates to 58 nodes and 83 directed edges. The recursive graph audit
found five Marker nodes and exactly five standalone occurrences. Source SHA-256:
`f2f82fbcc7fd68d0365b16076ebad2764d4fc7f33fc41b910675c90053ed4fd3`.

A fresh `.venv-review` environment was installed from all 62 locked dependency
versions, followed by an editable project install without dependency resolution.
Validation passed. Its offline suite initially passed 117 tests with 14 live
tests deselected. After TLS compatibility and UI contrast changes, it passed
**119 tests**, with 14 live tests deselected, in **42.34 seconds**. The final
layout/export source then passed the full suite again in **24.14 seconds** and
all 14 offline exports passed. After the final planner input-contract change,
all 24 service tests passed. Final Ruff check passed; 41 files were already formatted.

The completion audit found that the opt-in pytest harness dropped the TLS
compatibility setting when constructing its service. It now preserves configured
connection settings, selects the packaged assignment fixture, and pauses between
questions. An offline regression check covers that configuration path. The final
offline suite passed **120 tests**, with 14 live tests deselected, in **15.34
seconds**. The corrected actual command `pytest -m live -k Q05` passed **one real
two-stage test**, with 133 tests deselected, in **27.48 seconds**. This targeted
pytest result is separate from the 14 saved capture checks described below.

The review ZIP was then extracted into `dist/archive-review` and installed in a
new environment with the README's exact `python -m venv`, pinned `pip install`,
and `pip install --no-deps -e .` steps. `pip check` found no broken requirements;
graph validation passed; **120 offline tests passed**, with 14 live tests
deselected, in **30.90 seconds**. There was one nonfatal Windows permission
warning when pytest tried to rename its cache directory. A real query from the
newly installed ZIP returned the two expected Portable Speaker suppliers through
both Gemini stages. Its imported package path was checked to point into the
extracted ZIP, rather than the original source tree.

Checks cover invalid source records and references, graph schema/cardinality,
recursive occurrence scans, repeated purchase lines, integer money, strict price
boundaries, deduplication, delivered purchases, entity resolution, complete answer
references, sanitized provider errors, exports and UI submission/state behavior.
The TLS compatibility test requires certificate verification and hostname checking.

The initial UI test run encountered a cold-render timeout; the individual retry
and subsequent complete suites passed. A lint command initially included the
dependency cache; the environment was fully reinstalled and the fresh environment
was checked independently. Dependency/cache directories are now explicitly excluded.

## Real Gemini checks

The configured local key received a structured response from `gemini-3.8-flash`.
The full catalog planner returned HTTP 503, reporting high model demand. Python's
default HTTPS handshake also failed on this Windows network. Verified TLS 1.2
reached Google's endpoint and the Gemini API. `GEMINI_TLS12=1` is an optional
compatibility setting; certificates and hostnames remain verified.

`gemini-3.5-flash-lite` passed a complete real query and answer stage for the
NovaTech/MetroSupply question, retrieving P01, P02 and P03. It is the current
default. The first full 14-question run is retained in
[live_attempt_01.json](../examples/live_attempt_01.json). It passed six examples;
eight did not meet submission requirements. Two presentation plans omitted
`matching_count`, one order-total question was declined incorrectly, and later
requests hit HTTP 429. Deterministic fallback answers were explicitly labeled.

The second paced run passed 11 of 14 cases without rate-limit errors; its record
is [live_attempt_02.json](../examples/live_attempt_02.json). Input instructions
were clarified further: order_details requires only order_id, while customer,
items and total are outputs. Prompt version 3 includes explicit operation input
contracts and supported combined-filter examples using placeholders.
All three targeted cases (Q01, Q05, Q14) then passed both real stages, retained in
[targeted_live_results.json](../examples/targeted_live_results.json). The next
full batch passed **13 of 14**, retained in
[live_attempt_03.json](../examples/live_attempt_03.json). Q08 was declined because
the linked-product output of lookup_value was not explicit. Prompt version 4
clarifies that output. Its actual two-stage targeted rerun passed, retained in
[targeted_marker_results.json](../examples/targeted_marker_results.json).

[sample_results.json](../examples/sample_results.json) and
[sample_results.md](../examples/sample_results.md) collect **all 14 independently
verified real captures** from these two final reports. They preserve each run's
timestamp, prompt version, model, measured duration, actual usage, evidence and
capture source. This is not presented as a single uninterrupted all-pass batch.
All 12 retrieval cases completed both real Gemini stages; the unknown-entity and
out-of-scope cases correctly stop before presentation. Interpretation remains
probabilistic; evidence validation is not a proof of intent understanding.

## UI review

Initial browser review covered 1440×900, 1024×768 and 390×844. The native sidebar
can be opened and closed on narrow screens. Current screenshots are linked in
the UI polish section below.
The source graph remains directed; layout forces use an undirected view to spread
incoming neighbors without clustering their labels.

Browser selection of P01 showed six nodes/five edges; removing Marker reduced
the visible graph to five nodes/four edges. The direction table still showed all
five actual relationships. Keyboard Tab focused the neighborhood switch with a
visible native outline. There was no document-level horizontal overflow at
390 or 1024 pixels. The actual downloaded JSON and CSV were read back and
validated: O01, one record, historical total 539700 paise. Download reruns retained
the completed result and duration. Automated AppTest checks passed navigation,
all result states and no inference on navigation.

The earlier LIVE browser run completed O01 through both Gemini stages in
**4.48 seconds** with prompt version 4. Its downloaded
[execution evidence](../examples/browser_live_result.json) was read back and
validated, and [the live screenshot](screenshots/live-order-1440.jpg) records the
result. The first preview process could not connect under restricted network
permissions; restarting with authorized Gemini network access resolved that
preview-only failure. The localhost app is running at http://127.0.0.1:8501.

The source review archive was built with an explicit allowlist. ZIP integrity
passed and no selected file contained the locally configured key. .env,
environments, caches and local logs are excluded. All local documentation links
were checked and resolve. Planning documents, recording scripts, duplicate
environments and temporary installation copies were removed after the user
recorded the Loom walkthrough; the final archive contains the retained deliverables.

## UI polish — 2 October 2026

The interface now has a shared local visual system, dark sidebar, teal accent,
illustrated welcome header, white question composer, icon example buttons,
and readable answer cards. Order totals use retrieved integer-paise aggregates.
After submission, a compact header and collapsed examples bring the answer
closer to the composer. Selected entities use a readable table; raw attributes
remain available in an expander. Plotly colors, labels, hover cards and node
outlines match the interface. Dynamic question, answer and model text is escaped
before entering the decorative HTML. The illustration uses local inline SVG;
no new asset service, font CDN, dependency or LLM provider was added.

The full offline suite passed **120 tests**, with 14 live tests deselected, in
**34.88 seconds**. After the compact-result change, all **16 UI tests passed**
in **33.71 seconds**, including explicit submission, history, zero results,
missing credentials, provider errors, fallback and no inference on navigation.
Ruff lint and formatting checks passed for the UI modules.

Actual browser review covered the desktop question and order-result workspace,
graph explorer, dataset dashboard, and 390-pixel phone composer and explorer. Neither phone view
had document-level horizontal overflow. Captures:
[live workspace](screenshots/polished-live-workspace.png),
[phone workspace](screenshots/polished-ask-390.png),
[offline answer](screenshots/polished-result-1440.png),
[offline explorer](screenshots/polished-explorer-desktop.png),
[phone explorer](screenshots/polished-explorer-390.png),
[dataset dashboard](screenshots/polished-dataset-1440.png).
The final live preview was restarted to load the mobile toolbar spacing correction;
the phone composer has 64-pixel top padding and 390-pixel document width.
The earlier live screenshot above documents the original interface's actual Gemini run.

## Final cleanup — 2 October 2026

The retained `.venv` passed **120 offline tests**, with 14 live tests deselected,
in **39.04 seconds**. Graph validation, Ruff lint and formatting checks passed.
The local app runs from that environment. Blueprints, implementation notes,
internal checklists, Loom speaking guides, obsolete UI screenshots, temporary
installation copies and generated caches were removed. The duplicate
`live_failures.json` was identical to the retained `live_attempt_03.json`.
The user's recorded Loom link is included in README.md.

Commands are in [README.md](../README.md). Never place API keys in reports or screenshots.
