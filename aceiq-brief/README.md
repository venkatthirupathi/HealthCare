# AceIQ Health — Project Brief for Claude Code

This folder contains everything Claude Code needs to build the AceIQ Health
project autonomously. It is a complete specification, not a starter codebase.

## What's in this folder

```
aceiq-brief/
├── README.md              ← you are here (instructions for you, the user)
├── CLAUDE.md              ← auto-loaded by Claude Code as project context
├── PROJECT_BRIEF.md       ← THE master specification — what to build
├── JD_CONTEXT.md          ← original Cognizant Ace Team JD (the "why")
├── sample_data/           ← 3 synthetic drug-label XML files to ingest
│   ├── metformin.xml
│   ├── atorvastatin.xml
│   └── amoxicillin.xml
└── eval/
    └── questions.json     ← 12-question eval set (with expected answers)
```

## How to use this with Claude Code

### Option 1 — Build from scratch (recommended for learning)

```bash
# 1. Unzip this folder somewhere on your machine
unzip aceiq-brief.zip
cd aceiq-brief

# 2. Start Claude Code in this directory
claude

# 3. First message to Claude Code:
```

> Read `PROJECT_BRIEF.md` and `CLAUDE.md`, then implement Phase 0 + Phase 1
> end-to-end. Use the synthetic data in `sample_data/`. Run the eval set in
> `eval/questions.json` when you're done and show me the metrics table.

Claude Code will plan the work, create all the files, set up Docker, ingest
the data, and verify the eval suite passes — all in one conversation. You
review and merge.

### Option 2 — Use as reference alongside an existing scaffold

If you already have a partial implementation (for example, the scaffold I
built in the previous turn), point Claude Code at both:

```bash
cd your-existing-project
cp -r path/to/aceiq-brief/* docs/   # put the brief in docs/
claude
```

Then ask Claude Code to extend specific phases (e.g. "Implement Phase 3 —
the LangGraph multi-agent layer — using `docs/PROJECT_BRIEF.md` as the
spec").

## What good output looks like

When Claude Code finishes Phase 1, you should be able to run:

```bash
make install
make up
make seed
make api          # in one terminal
make ui           # in another
make eval         # in a third
```

And see the eval table print metrics like:

```
Retrieval drug match      : 100%
Section match             : 92%
Must-mention coverage     : 87%
Refusal correctness       : 100%
Avg verifier score        : 0.84
Avg latency               : 1850 ms
```

If any of those metrics are missing or below targets, Claude Code's job
isn't done.

## Tips for working with Claude Code on this project

1. **Don't try to do everything in one session.** The brief defines 4 phases.
   Each is one Claude Code session. After each phase, commit, run the eval,
   then start a fresh session for the next phase.

2. **Be specific when extending.** "Add streaming" is vague. "Add SSE
   streaming to `POST /api/v1/query` per Phase 4 of the brief" is what
   Claude Code can act on.

3. **Trust the eval set.** If you're not sure whether a change improved
   things, run `make eval` before and after and compare. The brief is
   designed so the eval set is your ground truth.

4. **Read `JD_CONTEXT.md` once.** The brief is technical; the JD reminds
   you which interview talking points you're building toward.
