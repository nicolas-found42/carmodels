# Reverse engineering with AI agents: tools, procedure and examples

Research date: **11 October 2026**, America/New_York. Requested recent window:
**27 September–11 October 2026**. The dated discovery section distinguishes items
published in that window from older resources that remain useful.

## Where to start

For this repository's game and asset work, start with **REA tools exposed in this session,
one available native analysis engine, and a small question that can be checked against original
bytes or a retained execution capture**. Use REA to discover and trace; use ordinary
Python/C/C++ tools to implement the recovered behavior; use an independent comparison
to decide whether the interpretation holds. My recommendation is **REA + Ghidra**
as the first baseline here, then a direct Ghidra MCP bridge when you need editable
types, structures or database annotations that the selected REA provider does not
expose. This is a judgment about fit and existing setup, not a measured claim that
one bridge outperforms the others or proves local backend readiness.

REA currently documents native analysis through Hopper, Ghidra or IDA, alongside
JavaScript/Electron, .NET, Android and package inspection. Static JavaScript and
.NET inspection does not require a native decompiler. These different routes are
a good reason to identify the target before selecting an engine. [REA owner
README](https://github.com/morluto/rea/blob/main/README.md)

Start with one finite helper, asset record, IPC feature or build difference;
require exact evidence, a falsifiable check and named unknowns. The proposed
procedure below was not benchmarked end-to-end during this research.

## Choose the tools by target and job

These are recommendations by fit, not a benchmark ranking. No common evaluation
found here compares these stacks on the same target, question and oracle.
Installed/released/main capabilities can differ; use connected schemas and
reported availability.

| Project | Fit and documented behavior | Practical limit |
| --- | --- | --- |
| [REA](https://github.com/morluto/rea) | Default front door here: CLI/MCP across native, JS/Electron, .NET, Android and packages, with identity and evidence. | Provider/host support differs; snapshots cache observations rather than save engine databases. [README](https://github.com/morluto/rea/blob/main/README.md), [contract](https://github.com/morluto/rea/blob/main/docs/cli.md) |
| [LaurieWired/GhidraMCP](https://github.com/LaurieWired/GhidraMCP) | Direct Ghidra decompilation, renaming and listings; GUI and headless PyGhidra. | Current README names Ghidra 12.1.4; headless Python 3.10–3.13; `--project DIR` retains state. Older GUI-only comparisons are stale. [README](https://github.com/LaurieWired/GhidraMCP/blob/main/README.md) |
| [bethington/ghidra-mcp](https://github.com/bethington/ghidra-mcp) | Detailed types/structures/dataflow, batching, documentation playbooks, P-code emulation and GUI debugger. | Hygiene score does not establish truth; debugger is GUI-specific and scripts are separately gated. [README](https://github.com/bethington/ghidra-mcp/blob/main/README.md), [workflow](https://github.com/bethington/ghidra-mcp/blob/main/docs/prompts/FUNCTION_DOC_WORKFLOW_V5.md) |
| [Official IDA MCP](https://github.com/HexRaysSA/ida-mcp) | Existing licensed IDA workflow; GUI/headless server built on Nexus for shared database clients. | IDA 9.4+ with idalib/Python 3.11+; competing IDA servers can confuse routing. [README](https://github.com/HexRaysSA/ida-mcp/blob/main/README.md) |
| [mrexodia/ida-pro-mcp](https://github.com/mrexodia/ida-pro-mcp) | Compatible existing community integration; useful authored prompts/examples. | Current owner recommends official Hex-Rays server; tool/session behavior is version-specific. [README](https://github.com/mrexodia/ida-pro-mcp/blob/main/README.md) |
| [r2mcp](https://github.com/radareorg/radare2-mcp) / [r2ai](https://github.com/radareorg/r2ai) | Terminal/script-oriented alternative: r2mcp connects external agents; r2ai is in-radare2 AI with ReAct/local or remote models; decai focuses on decompilation. | Different layers. r2mcp has optional read-only/sandbox/tool restrictions; HTTP session multiplexing needs ABI 91+. [r2mcp](https://github.com/radareorg/radare2-mcp/blob/main/README.md), [r2ai](https://github.com/radareorg/r2ai/blob/master/README.md) |
| [Binary Ninja built-in MCP](https://docs.binary.ninja/guide/mcp/) | Binary Ninja 6.0 shipped first-party MCP; GUI integration is available in all editions including Free. | Headless macOS/Linux needs Commercial/Ultimate; native Windows headless is excluded. [Owner release](https://binary.ninja/2026/09/03/binary-ninja-6.0-krypton.html#MCP) |
| [BinAssist](https://github.com/symgraph/BinAssist) | Optional Binary Ninja assistant: LLIL/MLIL/HLIL context, ReAct/MCP, selective rename/retype/structure actions, RAG/semantic graph. | Suggested types, summaries and confidence remain hypotheses; graph paths do not prove vulnerabilities. [README](https://github.com/symgraph/BinAssist/blob/master/README.md) |
| [e5r](https://github.com/h5i-dev/e5r) | Study Rust CLI/JSON, evidence strength and Git-mergeable content-anchored annotation logs. | Detailed scorecard checkpoint records 39 wrong compiled-C functions among 229 measured; experimental secondary view. [README](https://github.com/h5i-dev/e5r/blob/main/README.md), [scorecard](https://github.com/h5i-dev/e5r/blob/main/docs/scorecard.md) |

### Target routing

| Target | First route | Extra tools only when the question needs them |
| --- | --- | --- |
| Native ELF/PE/Mach-O | REA native route with an explicitly chosen available provider, or one direct Ghidra/IDA/Binary Ninja bridge. | Debugger or bounded emulation for runtime-dependent values; Frida for observed calls/arguments. |
| Extracted JavaScript/Electron/ASAR | REA `analyze_javascript_application`; inspect modules, source maps and IPC relationships. | Browser/Electron observation for one declared scenario; native engine for a referenced add-on. |
| Managed .NET PE/CLI | REA managed inspection for metadata/CIL. | Native route for NativeAOT or native dependency bodies; a managed decompiler when higher-level reconstruction needs it. |
| Android APK | REA Android inspection using caller-supplied headless JADX and JDK; inspect resources separately. | Apktool for decoded resources; adb for an explicit device/emulator question; Frida for targeted runtime hooks. |
| Firmware | Format/region inventory and extraction before native analysis. | Caller-supplied Binwalk/Unblob on a supported Linux host; identify each embedded executable's architecture independently. |
| Game archives, textures, model streams | Inventory and hash the carrier; a format-aware parser plus relevant executable decode path. | The game's emulator/debugger, retained memory/draw captures and format-specific decoders; native application bridges alone do not understand GPU packet semantics. |

The application/package/managed/Android/firmware routes and prerequisites above
come from [REA's target matrix](https://github.com/morluto/rea/blob/main/README.md)
and [routing skill](https://github.com/morluto/rea/blob/main/.agents/skills/reverse-engineer-anything/SKILL.md).
Frida is a dynamic instrumentation toolkit that runs injected logic in a target
process and exposes memory/hooking/native-call capabilities; it belongs in the
runtime layer, after you know what observation you need. [Frida official
documentation](https://frida.re/docs/home/)

For the game-format route, the recommendation follows this repo's existing
distinction between static derivation, retained captures and game-render fidelity.
A native call graph or successful model export does not prove that the running
game selects, animates or shades it the same way. [Repo contribution and check
contract](../CONTRIBUTING.md), [existing recovery limits](README.md)

## The procedure to follow

The following is a proposed procedure synthesized from owner contracts and examples.
It was not executed as a complete benchmark in this research.

### 1. Define a finite reconstruction contract

State the exact target/build, question, input/output and stopping rule. Example:
recover one stock-body record decoder; explain offsets, counts, index ownership
and signedness; reproduce retained geometry; reject truncation/overlap; leave
runtime part selection and shading for separate captures.

A request to explain “search” also needs a boundary: tokenization, ranking,
IPC and server behavior are different questions. Record SHA-256, platform,
architecture, access scope and evidence needed for every required claim.

**Deliverable:** target manifest, `spec.md`, question checklist.
**Done when:** each required claim has a planned observation or falsifiable check.

### 2. Preserve identity and baseline analyzer state

Inspect headers, sections, imports, resources and members. Verify architecture,
endianness, image/load base and entry points. Distinguish file offset, RVA,
static VA and runtime address. Record analyzer version, import options and
analysis completion state.

Keep original bytes unchanged. Retain a separate database/export before editing
names/types. For archives, preserve member ordinal/path/digest; duplicate names
do not establish ownership.

REA snapshots bind eligible cached results to target bytes, operation, parameters,
provider and settings. They are cached observations, **not saved engine databases**.
CLI processes are separate; retained MCP references can belong to one connection.
[REA identity/cache contract](https://github.com/morluto/rea/blob/main/docs/cli.md)

**Deliverable:** immutable manifest, baseline state and versions.
**Done when:** every later source location maps to an exact input.

### 3. Trace one connected feature slice

Start from a resource, API, string, UI action or known record/packet; follow
references through relevant callers, transformations and state to the output.
Retrieve a small neighborhood first.

For Electron: renderer → preload → IPC handler → main-process operation.
For assets: member selection → decompression → decoder → consumer/render submission.
A promising filename/resource remains a candidate until ownership and consumer
path agree. Server behavior remains outside a client-only observation.

Save raw results once, then summarize/page them. REA documents saved Evidence,
summary/page views and finite feature investigation.
[CLI/evidence](https://github.com/morluto/rea/blob/main/docs/cli.md),
[guided prompts](https://github.com/morluto/rea/blob/main/docs/mcp-prompts.md)

**Deliverable:** feature map, exact sources, named gaps.
**Done when:** proposed boundary has identified inputs, outputs, state and dependencies.

### 4. Require hypothesis → discriminating test → observed result

For every type, field, formula or dependency, separate the raw observation from
interpretation; name an alternative and the cheapest test that distinguishes them.
Use tools/code for base conversion, endianness, sign extension, overflow,
floating-point bits and layout. If pseudocode disagrees with instructions,
check callers, ABI, register/stack inputs, widths and control flow.

DX-Ball's sound-pan example recovered omitted inputs/arithmetic from instructions,
caller context and raw constants before checking reconstructed C.
[Worked case](https://rea.tools/showcase/dx-ball/)

**Deliverable:** hypotheses, alternatives, test results and limits.
**Done when:** accepted claims survive a check that could refute them.

### 5. Change types/names carefully, then re-decompile

Use address-based identities, controlled batches and a mutation log. Correct
supported prototypes/types before comments, then re-read the resulting decompilation.
A changed type can create new variables or materially alter pseudocode.

Use one writer for a shared database or assign separate mutable copies.
Different chat contexts do not imply isolated analyzer state. Other workers
return proposed mutations rather than racing to change shared signatures.

bethington V5 orders prototype/type changes before comments because prototypes
can wipe plate comments; it refetches variables after changes and explicitly
distinguishes documentation hygiene from disassembly falsification.
Its naming style is optional; use this repo's conventions.
[Authored V5 workflow](https://github.com/bethington/ghidra-mcp/blob/main/docs/prompts/FUNCTION_DOC_WORKFLOW_V5.md)

**Deliverable:** reviewed mutations and fresh export.
**Done when:** annotations agree with raw evidence and edits can be replayed.

### 6. Use runtime for one named uncertainty

Examples: which variant is selected, what bytes enter the decoder, what value
is returned at a boundary. Declare target identity, lifecycle, input/scenario,
capture location and discriminating observation.

Pick the smallest suitable oracle: leaf emulation, breakpoint, Frida hook,
process trace, browser/Electron scenario or game emulator capture. Record module
base when translating runtime addresses. Hooks/debugger timing/simplified emulation
can affect behavior; keep that limit.

REA separates static inspection from runtime capture, which executes or interacts
with the selected target under user permissions.
[Runtime guide](https://github.com/morluto/rea/blob/main/docs/cli.md#capture-runtime-behavior)

**Deliverable:** retained capture and static/runtime reconciliation.
**Done when:** the uncertainty is settled or explicitly remains open.

### 7. Reconstruct against an independent oracle

Implement the smallest accepted contract and preserve unknown behavior. Compare
with original bytes, retained outputs, independently executed original routines,
a formal model with stated assumptions, or historical compiled bytes.

Tests derived from the same speculative formula as the candidate can agree
while both are wrong. Pure functions need boundary/signed/overflow/state cases;
parsers need truncation, overlap, count/index/ownership controls and corpus coverage.
A correct export does not establish runtime selection, shading or animation.

The published DX-Ball sound-pan check reports 3,205 original-x86 comparisons and 63
matching function bytes under a pinned historical compiler/reviewed relocations:
finite routine evidence, not whole-game equivalence. TH04 supplies an architecture-
specific instruction-to-C++/historical-compiler example.
[DX-Ball](https://rea.tools/showcase/dx-ball/),
[TH04](https://rea.tools/showcase/th04/)

**Deliverable:** candidate, independent comparisons, negative controls, counterexamples.
**Done when:** acceptance checks pass for stated coverage; failures remain visible.

### 8. Audit unknowns, preserve handoff and close owned state

Have a reviewer check the ledger and primary evidence, including alternatives,
excluded states and malformed inputs. Preserve failed experiments.
Mark questions answered/partial/unresolved and give the next discriminating
experiment. Save necessary snapshots/databases and close owned sessions.

REA guided prompts include reconstruction verification, bounded process capture
and residual-unknown audit.
[Prompt inventory](https://github.com/morluto/rea/blob/main/docs/mcp-prompts.md)

**Deliverable:** reproducible report with exact coverage and open work.
**Done when:** the finite contract is satisfied, with remaining gaps stated.

## How to divide the agents

Begin with one analyst and one independent verifier; add workers for independent
questions. This is a recommended starting arrangement, not a measured optimum.

| Role | Assigned output |
| --- | --- |
| Coordinator | Target/contract/checklist, budget, accepted ledger and next questions. |
| Static analyst | One feature slice: raw locations, hypotheses, proposed types/names and gaps. |
| Runtime investigator | One declared scenario: capture, identity, discriminating observation and limits. |
| Reconstructor | Candidate from accepted contract; assumptions and exact behavior. |
| Verifier | Independent oracle, negative controls, counterexamples and coverage audit. |

Use explicit target/session IDs wherever supported. Reserve database copies for
mutable workers or serialize edits through one writer; shared-client support
does not guarantee isolated hypotheses. Official IDA MCP uses Nexus for shared
database clients. [Owner documentation](https://github.com/HexRaysSA/ida-mcp/blob/main/README.md)

Re:Live provides concrete scoped tasks, completion criteria, parent validation,
role prompts and JSONL logs. Borrow these ideas, replacing security-specific
scanner/PoC roles with format analyst/reconstructor for this repo.
[Role/scope implementation](https://github.com/boringllm/ReLive/blob/main/README.md)

## Evidence ledger and workspace

Keep a compact `spec.md` and `report.md`, immutable input manifest, saved
analysis state, raw Evidence/captures, candidate implementation and independent
verification results.

Each ledger entry should contain:

- Stable claim ID, target/member digest, file/member ordinal and precise address space.
- Raw evidence location; actual observation; inference and competing explanation.
- Discriminating test, result/counterexample, dependency IDs and scope limits.
- Status: observation, inference, verified-for-scope, refuted or unresolved.

Example: a field multiplied by 12 before a bounds check suggests a 12-byte element
count; an alternative expansion branch remains possible until record comparisons
and deliberate count corruption distinguish them. Confidence prioritizes work;
it does not promote an inference into a fact. Dependencies invalidate downstream
claims when their roots fail. This is a proposed schema inspired by
[REA Evidence](https://github.com/morluto/rea/blob/main/docs/cli.md) and
[Reverify dependencies](https://github.com/2akouwu/reverify/blob/main/README.md).

## A starter run you can repeat

Proposed recipe, **not executed by this research**. Use an installed recorded REA
version, an available provider and a small exact target. Replace `main` with a
real discovered function.

```sh
TARGET="/absolute/path/to/your/executable"
CASE="$PWD/.scratch/re-first-pass"
mkdir -p "$CASE/analysis" "$CASE/evidence"
shasum -a 256 "$TARGET" > "$CASE/evidence/target-sha256.txt"
file "$TARGET" > "$CASE/evidence/target-file.txt"
rea analyze "$TARGET" --provider ghidra \
  --snapshot "$CASE/analysis/target.snapshot.json" --json \
  > "$CASE/evidence/overview.json"
rea function "$TARGET" main --provider ghidra \
  --snapshot "$CASE/analysis/target.snapshot.json" --json \
  > "$CASE/evidence/function.json"
```

For JS/Electron/ASAR, start with `rea analyze-javascript-application
"/absolute/path/to/app-or.asar" --json` and retain the output; summarize/page
large exports rather than inserting them whole into context.
[Documented command shapes/cache/views](https://github.com/morluto/rea/blob/main/docs/cli.md)

If only a package runner exists, use an exact recorded `rea-agents` version.
Connected schemas/installed version take precedence over repository-main examples.
A working connection does not need repeated setup/doctor.
First-session target: one feature slice, explicit hypotheses, one independent
check and one negative control or counterexample.

## Reusable prompts

Five **new proposed templates**, not copied project prompts. Replace brackets;
they do not authorize additional runtime actions.

### 1. Bounded triage

```text
Investigate [question] in [exact target]. Record hash, format, architecture,
build, provider/version and matching saved state. Use available schemas.
Inventory at most three promising entry points. Return raw locations,
observations, inferences, alternatives and gaps. Preserve original input.
Stop when you can define a finite feature slice and checkable contract.
```

### 2. Feature trace

```text
Trace [entry/resource/API] through inputs, transformations, state and outputs
for [one behavior]. Every type/field/formula/dependency needs raw evidence,
an alternative and the cheapest falsifying test. Use tools for arithmetic.
Reconcile pseudocode with instructions, widths, callers and ABI.
Query again only to close a named gap; update the evidence ledger.
```

### 3. Scoped worker

```text
Scope: [target hash, range/member, one question]. State: [explicit session
or assigned database copy]. Done when: [deliverable and required evidence].
Reuse baseline facts. Return locations, hypotheses, proposed mutations,
counterexamples and unknowns. Do not mutate shared state; send proposals
to its writer. Report out-of-scope dependencies and the next question.
```

### 4. Reconstruction and verification

```text
Implement [finite accepted contract]; preserve unknowns.
Compare with [independent byte/runtime/capture oracle] on [corpus].
Include boundary, signedness/overflow/float cases and intended negative
controls. Never derive expectations from the candidate.
Report every difference and exact covered states; distinguish static
derivation, finite behavioral agreement and broader runtime equivalence.
```

### 5. Skeptical audit/handoff

```text
Check [report/ledger] against primary evidence and contract.
Mark supported-for-scope, contradicted or unresolved. Inspect mixed builds,
stale/shared state, offset/VA confusion, decompiler guesses, circular tests
and excluded runtime states. Confidence/hygiene cannot replace evidence.
Return blockers, counterexamples, next experiment and reusable handoff.
```

## Existing projects, prompts and workflows to study

| Resource | What to borrow and what remains bounded |
| --- | --- |
| [REA guided prompts](https://github.com/morluto/rea/blob/main/docs/mcp-prompts.md) | Six workflows for investigation, comparison, verification, crashes, unknown audits and bounded capture. Prompts do not invoke tools automatically. |
| [bethington V5](https://github.com/bethington/ghidra-mcp/blob/main/docs/prompts/FUNCTION_DOC_WORKFLOW_V5.md), [batch](https://github.com/bethington/ghidra-mcp/blob/main/docs/prompts/FUNCTION_DOC_WORKFLOW_V5_BATCH.md) | Type audit, re-decompilation, batching/comment order and hygiene-versus-truth distinction; preserve raw evidence before replacing annotations. |
| [mrexodia authored prompts](https://github.com/mrexodia/ida-pro-mcp/blob/main/README.md#prompt-engineering), [reversing dataset](https://github.com/mrexodia/mcp-reversing-dataset) | Tool-assisted arithmetic, corrected pointers and instruction follow-up; task folders retain inputs/prompts. Small smoke tests, not production benchmarks; keep answers out of blinded evaluation. |
| [DX-Ball project](https://github.com/N0zoM1z0/dx-ball), [sound-pan case](https://rea.tools/showcase/dx-ball/), [compiler notes](https://github.com/N0zoM1z0/dx-ball/blob/a55dca27ec0a07018c1b2c95ae2be027f7d8c3c4/docs/BUILD_MATCHING.md) | Finite reconstruction, raw caller/constants/instructions, original-code comparisons and historical compiler replay; preserve toolchain/relocation limits. |
| [TH04](https://github.com/N0zoM1z0/th04), [DOS bullet case](https://rea.tools/showcase/th04/) | Integer widths, instruction semantics and historical compilation; one function does not establish a playable game. |
| [e5r tutorial](https://github.com/h5i-dev/e5r/blob/main/docs/tutorial.md) | Target identity → function/signature discovery → committed annotations. Consult scorecard before trusting decompilation or speed claims. |
| [Re:Live prompts](https://github.com/boringllm/ReLive/tree/main/agents), [workflow](https://github.com/boringllm/ReLive/blob/main/README.md) | Scoped role/handoff/validation/event logging ideas; mock pipeline success does not establish live quality. |
| [Reverify loop](https://github.com/2akouwu/reverify/blob/main/README.md#the-verification-loop) | Typed claims, dependencies and useful refutations; evaluate actual predicates/backends. |

## What the research says about reliability

**Reveree, submitted 1 September 2026**, evaluates nine models and four prompting
strategies on 88 picoCTF/NYU-CTF challenges. It distinguishes solve rate, milestone
progress through an eight-stage RE schema and action behavior. Some comprehension
stages use an outcome-blinded LLM judge validated against a human expert;
other stages are deterministic. The authors report that model choice dominates,
prompting effects are model-dependent, and additional budget/persistence rarely
rescues comprehension failures. They also investigate recall/contamination.
This is CTF evidence, not a benchmark of full desktop reconstruction or this
repo's PS2 format pipeline. [Author
paper](https://arxiv.org/abs/2609.01185)

**AgentRE-Bench** uses a deterministic scorer on controlled x86-64 ELF/PE tasks,
with 25 tool calls and a fixed static-analysis toolset. It explicitly excludes
debugger/emulator execution, Ghidra/IDA, script writing and ARM/MIPS; it records
single trials rather than estimating run variance. The useful design lesson is
structured answers, false-claim penalties and fixed ground truth. Its scores
cannot identify the best Ghidra/REA bridge or predict game-asset recovery.
[Owner benchmark and
limits](https://github.com/agentrebench/AgentRE-Bench)

**e5r's scorecard** demonstrates why “the generated C compiles” is insufficient:
its behavioral checks found substantial wrong output, and the detailed checkpoint
still lists 39 disagreeing functions among 229 measured. The scorecard also
bounds its corpus and explains that timing comparisons use different analysis
depths. This is a project self-evaluation to inspect, not independent proof of
universal quality. [Detailed
scorecard](https://github.com/h5i-dev/e5r/blob/main/docs/scorecard.md)

Compare workflows with target/question/budget/oracle fixed; track fixture coverage,
wrong-control rejection, repeated queries, cost and handoff reproducibility.

## Recommended progression for this repository

Use **REA + Ghidra + ordinary Python/C/C++ + Git/JSON evidence** first.
Recover one finite helper/decoder with independent checks. Add one direct bridge
only for a demonstrated typing/structure/editing gap. Close one runtime uncertainty
with a bounded capture. Compare single analyst versus analyst/verifier on the
same hidden fixtures before increasing worker count. Standardize contracts,
evidence, counterexamples and unknown audits. Other engines, Frida and orchestrators
are selected options, not prerequisites.

## Research evidence and limits

This note uses owner GitHub READMEs/source documentation, author papers and
first-party case studies. Recommendations are labeled judgments or proposed
procedures. Web search snippets and directories were discovery inputs; they do
not establish technical behavior by themselves.

Primary source text and Jev claim-check receipts for this research are retained
under `.scratch/ai-agent-re-research/primary-sources.json`, with additional
checks in `.scratch/ai-agent-re-research/additional-claims.json`. Jev checked the
core capability/limitation claims against those texts; those judgments support
citation consistency, not actual target execution or an independent tool
benchmark. This research did not install tools, execute target binaries,
test bridge compatibility, or validate the source projects' broad performance
claims. Exposed schemas do not prove backend readiness. The local skill pins 6.3.0;
installed/released/main capabilities can differ.

Open work: implement and measure this procedure on a small hash-pinned
carmodels fixture; compare a single analyst with analyst/verifier roles; establish
which provider supplies the required target/architecture operations; and settle
runtime-dependent asset/renderer claims with their own captures rather than
a successful static export.

## What changed in the last two weeks

The requested window is **September 27–October 11, 2026**, in America/New_York. Release dates below come from GitHub's `published_at`, converted to that timezone; video publication timestamps were fetched directly from YouTube and converted to New York time. Where YouTube's supplied `upload_date` differs, both dates are noted. The selected metadata is retained in [source-manifest.json](evidence/ai-agent-reverse-engineering-2026-10-11/source-manifest.json). This is a researched shortlist, not a complete census.

| Date | Primary source | What to take from it |
| --- | --- | --- |
| Oct 8 | [Official Hex-Rays IDA MCP v20261008.0.1](https://github.com/HexRaysSA/ida-mcp/releases/tag/v20261008.0.1) | The release adds import options to `open_database`. For a new compatible IDA setup, evaluate the vendor server: its [README](https://github.com/HexRaysSA/ida-mcp) requires IDA 9.4+ with idalib and Python 3.11+. |
| Oct 9 | [GhidrAssistMCP 3.0.0](https://github.com/symgraph/GhidrAssistMCP/releases/tag/3.0.0) | Explicit operations for pseudocode/disassembly/P-code, application-wide lifetime, project open/save/close controls and stronger program selection. A useful alternative when you want an in-process Ghidra integration; tool names changed in this major release. |
| Oct 9 | [bethington Ghidra MCP 7.0.0-rc.2](https://github.com/bethington/ghidra-mcp/releases/tag/v7.0.0-rc.2) | A release candidate, with recorded Ghidra 12.1.4 regression evidence and targeting/bridge fixes. Distinguish this prerelease from the stable 6.0.0 release and from current repository documentation. |
| Oct 6 | [r2ai 1.5.2](https://github.com/radareorg/r2ai/releases/tag/1.5.2) | Recent radare2 AI maintenance. The release itself provides a changelog comparison; avoid reading a new tag as proof of an analysis-quality improvement. |
| Oct 10, 11:58 p.m. | [REA 6.4.0](https://github.com/morluto/rea/releases/tag/rea-agents-6.4.0) | The upstream release label is Oct 11 UTC. It adds ADB/Apktool and JEB paths, retained-evidence discovery and focused views, resource-bounded JS analysis, and configurable Ghidra import language/compiler specifications. Its notes also describe bounded MIPS ELF support. Relevant to console research, but not proof of full PS2 EE/VU support. |

The [official IDA architecture description](https://hex-rays.com/blog/hex-rays-ida-mcp-server) is particularly useful: a small database/Python/reference interface lets the agent compose analysis in code, and IDA Nexus coordinates clients using a database. The vendor's token-reduction figure is an internal malware-benchmark result, not a universal tool ranking. Interpreter execution also reaches beyond the analysis database; use a separate environment for untrusted targets.

**Recent firsthand workflow lesson:** Maurice Heumann's [October 9 FPS decompilation account](https://momo5502.com/posts/2026-10-09-game-decompilation/) describes workers and a reviewer producing readable but semantically wrong code. The project improved after adopting comparison against original function bytes using the original compiler, with relocation handling required. He reports 99% of functions present and 83% byte exact; those are self-reported results from private code. Borrow the fixed acceptance check and bounded work allocation. The reported token total and an unnamed game's outcome are not a reproducible benchmark, and function matching alone does not validate the complete port.

## Recent YouTube: what is worth watching

Direct YouTube search found relevant uploads that date-filtered web searches missed. Three English automatic-caption transcripts were read; audiovisual demonstrations were not independently watched or reproduced. Creator reports remain anecdotes, and automatic captions can misrecognize technical names. Recommendations below are based on usefulness to this investigation.

| Priority | Video and publication date | Useful material and evidence limit |
| --- | --- | --- |
| 1 | Low Level, [Has AI Solved Reverse Engineering?](https://www.youtube.com/watch?v=wIe3eDfGKUo), Oct 9 | Firsthand monitor-firmware investigation: package extraction, Ghidra inspection of the updater DLL, candidate decryption, then checking the image's stored checksum and structural plausibility. The practical lesson is independent validation after the agent's first success claim. Caption transcript read; no exploit or hardware result independently verified. |
| 2 | lustoykov, [Reverse Engineer Anything with AI, Here's How](https://www.youtube.com/watch?v=cHPWA4omJD8), Oct 10 | Installation/run sections at 5:50/6:15 and comparison at 8:20. In one authenticator-APK task, the presenter reports the vanilla agent outperforming REA on speed, cost and verification. Useful reason to A/B your own harness; one task does not establish a general winner. Caption transcript read. |
| 3 | Undocumented Behavior, [AI Game Decompilation: A Deep Dive](https://www.youtube.com/watch?v=Pl7ThC4PiVA), Oct 11 | Matching decompilation at 1:50, agent loops at 4:45, and checker manipulation at 6:02. It links Chris Lewis's projects and Maurice Heumann's account; use those first-party records for factual workflow claims. Caption transcript read; this is an explanatory overview. |
| 4 | Nick Saraev, [I Tested The Viral Github Repo To Reverse Engineer Anything](https://www.youtube.com/watch?v=dAzs_rU6080), Oct 10 | Creator chapters advertise rebuilding Preview at 2:44 and matching the app at 4:46. Metadata/description/chapters checked; captions returned HTTP 429, so the claimed outcome was not assessed. |
| Optional | AI Search, [The AI unlock has begun](https://www.youtube.com/watch?v=h5zkzon0gM4), Oct 5 at 11:36 p.m. New York time; YouTube lists Oct 6 | Creator chapters cover modding, Rust rebuilding and prompts at 11:50. A discovery source; linked projects and broad capability claims require separate verification. Metadata only. |

For basic MCP mechanics, two older tutorials were directly date-checked: Jackson Mittag's [Claude + Ghidra tutorial](https://www.youtube.com/watch?v=ybSWI2cZzIU), Apr 10, 2026, and Exploit Mastery's [Ghidra & Claude tutorial](https://www.youtube.com/watch?v=RwxYUZwCeag), Apr 26, 2026. They are outside the requested window; installation details should be checked against today's upstream documentation.

## Awesome lists: discovery, with an upstream check

The context-awesome corpus was searched for reverse-engineering sections and Ghidra resources, then current lists were read on GitHub. List endorsement and hosting-list stars are not measurements of a tool's correctness.

| Resource | Use it for | Qualification |
| --- | --- | --- |
| [DiscoverBox/awesome-ai-reverse, English catalog](https://github.com/DiscoverBox/awesome-ai-reverse/blob/main/README_EN.md) | The most directly relevant discovery map found: vendor integrations, Ghidra/IDA, JS, mobile, native and agent workflows. | Check release/status claims upstream. Its live catalog changed during the research and older search snapshots had older release information. |
| [morluto/awesome-reverse-engineering](https://github.com/morluto/awesome-reverse-engineering) | Foundational tools, formats, protocols and AI interfaces, organized around actual targets. | Maintained by the REA author; useful organization, not an independent comparison of REA. |
| [AllsafeCyberSecurity/awesome-ghidra](https://github.com/AllsafeCyberSecurity/awesome-ghidra) | Architecture loaders, extensions, scripts and learning references. | Most entries are supporting infrastructure rather than agent orchestration. |
| [ram-elgov/awesome-llm-reverse-engineering](https://github.com/ram-elgov/awesome-llm-reverse-engineering) | Names of models, papers and datasets to investigate. | A checked citation is wrong: the listed REACTor link, [arXiv 2407.01234](https://arxiv.org/abs/2407.01234), is actually a paper on power storage. Do not inherit paper titles or results without opening the primary record. |
| [heaven-hm's game reconstruction catalog](https://github.com/heaven-hm/awesome-reverse-engineered-games/blob/main/docs/09_documented_ai_reverse_engineering_projects.md) | Leads for game-specific projects. | Its linked `OpenIGI/OpenIGI` repository returned 404 during this research. Avoid repeating its completion/time claims as verified results. |

## More examples to borrow from

**Chris Lewis's Snowboard Kids workflow is especially relevant to this repo.** His older [Long Tail account](https://blog.chrislewis.au/the-long-tail-of-llm-assisted-decompilation/) describes moving from easiest-first scheduling to similar known functions, giving agents a graphics-command decoder and reference, separating worktrees, and protecting the original checksum and verification command after an agent edited the expected hash. He also describes dropping a permuter when its intermediate output confused the agent. The lesson for PS2 recovery is to teach VIF/VU/GIF semantics with small tools and validated examples, then test a narrow recovery claim.

The publicly available implementation points are [Snowboard Kids 2 skills](https://github.com/cdlewis/snowboardkids2-decomp/tree/main/.claude/skills), [hooks](https://github.com/cdlewis/snowboardkids2-decomp/tree/main/.claude/hooks), [decompilation environment](https://github.com/cdlewis/snowboardkids2-decomp/tree/main/tools/claude-decomp-env), and [Nigel](https://github.com/cdlewis/nigel). Their directories were checked through GitHub's contents API. Current Nigel documentation describes candidate-source → templated prompt → verification → success/failure handling, with dry-run, limits and sharding. Adapt its success condition to a target-derived check: a task disappearing from a queue is insufficient evidence by itself. Its example reset command assumes a disposable working copy, so preserve your worktree policy when adapting it.

Lewis's [Oct 2 Snowboard Kids: Recompiled release](https://blog.chrislewis.au/introducing-snowboard-kids-recompiled/) falls inside the requested window. It is a released result for modern platforms, with substantial community testing; it does not make the older workflow posts recent publications.

[Dryxio/reagent](https://github.com/Dryxio/reagent) is a concrete reconstruction pipeline to study: bounded function manifests, reverser/checker rounds, structural checks, candidate overlays in an isolated project copy, build/test/runtime gates, and explicit unknowns. Its documentation calls these conservative checks rather than proof of semantic equivalence. Start with one function, inspect its configured validation, and use `parity --strict-exit` for standalone parity automation because ordinary parity exits zero even on RED results.

[jonradoff/lofp](https://github.com/jonradoff/lofp) demonstrates a different reconstruction route. The original game engine source was lost, but its owner used preserved world scripts, manuals and gameplay logs to rebuild it with Claude Code. The README records mistakes in spawn semantics and filename case handling. This is artifact/specification recovery, not binary decompilation; it shows why manuals and historical captures belong in the evidence inventory.

## A concrete starting sequence

This sequence is a recommendation for the current recovery work, not a claim that one tool outperforms every alternative.

1. Pick one unresolved relationship: one archive member's field → one executable consumer → one captured output. Define the expected result before the agent edits anything.
2. Use the already exposed REA/Ghidra/radare2 tools and exact current schemas. Pin the target hash, loader/language and analyzer version. Avoid adding another bridge until a specific missing capability is demonstrated.
3. Run one investigator through the hypothesis/test loop. Have a checker derive its expected values independently from source bytes or a capture. Keep the original inputs, expected hashes and acceptance code outside the worker's edit scope.
4. Retain addresses/offsets, raw observations, candidate meanings, test command/results and the remaining uncertainty. Turn the first proved relationship into a reusable example or small domain tool.
5. Repeat on a second, different sample and a deliberately incorrect interpretation. If the check rejects the wrong interpretation for the right reason, expand to a bounded batch; otherwise improve the check first.
6. Compare harnesses on the same five tasks before adopting a new stack. Suggested measures: verified facts recovered, wrong claims, time, tool failures, cost/tokens when available, and clean restart/resume behavior. This small local evaluation is a recommendation, not a published benchmark.

## Research limits and remaining questions

This report checks upstream descriptions, release metadata, selected source/workflow files and available transcripts. It does not install competing stacks, reproduce the featured demonstrations, or prove a universal best model/tool. Advertised support, observed local tool availability, static evidence and runtime evidence remain separate. Several video claims are assessed only through creator captions or metadata.

Still to test locally: whether a new integration materially improves PS2 loader/VU coverage; which backend resumes the investigation cleanly; how much shared-database mutation coordination is useful for this target; and which acceptance checks reliably distinguish a correct interpretation from an attractive approximation. These are evaluation questions, not newly established asset-recovery facts.
