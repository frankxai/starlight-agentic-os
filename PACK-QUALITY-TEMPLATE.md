# Pack Quality Template — the copy-me "Improve" pattern

*How a pack moves from `install=done` to `improve=done`. This is the reusable bar every pack
copies. First worked example: **`agentic-creator-os`**, worked skill **`acos-meta`**.*

> **"Improve" = hardened to the quality bar = evals + rails + provenance + observability.**
> A pack is not `improve=done` until at least its flagship skills pass the three gates below in CI.

---

## What "hardened" means — three artifacts + one env

Copy these four things into any pack:

| Artifact | Path in the pack | Purpose |
|---|---|---|
| **Eval config** | `evals/promptfooconfig.yaml` | promptfoo skill gate: `skill-used` assertion + the three thresholds, with a 2–3 case golden set per gated skill. |
| **CI workflow** | `.github/workflows/skill-evals.yml` | runs the gate on **skill VERSION bumps** (the version is the contract) and enforces thresholds. |
| **Provenance** | `pack.meta.yaml` | source · license · checksum · lifecycle status · gated-skills list. Mirrors the central `registry.yaml`. |
| **Observability env** | `CLAUDE_CODE_ENABLE_TELEMETRY=1` | native Claude Code OTel → self-hosted **Langfuse** (reference stack). Set in CI and in the operator's shell. |

---

## The three gates (research-derived, non-negotiable)

| Metric | Threshold | Question it answers |
|---|:--:|---|
| `SkillDispatchCorrectness` | **≥ 0.85** | Did the *right* skill get selected? (incl. NOT firing on unrelated asks) |
| `SkillInternalTrajectory` | **≥ 0.90** | Did it follow the skill's *intended steps*? |
| `SkillOutputIntegration` | **≥ 0.80** | Did the output *integrate* the skill's guidance? |

Failure classes to watch: **wrong-skill**, **trajectory-drift**, **integration-skip**.

---

## The golden-set shape (per skill)

Minimum **2 positive + 1 negative** cases per gated skill:
- **Positive** — a prompt that *should* trigger the skill → assert `skill-used` + trajectory + integration rubrics.
- **Negative** — an unrelated prompt that *must not* trigger it → assert `not-skill-used` (dispatch precision).

See the worked example: [`agentic-creator-os/evals/promptfooconfig.yaml`](https://github.com/frankxai/agentic-creator-os/blob/main/evals/promptfooconfig.yaml)
(gating `acos-meta` with exactly this shape).

---

## Copy-me steps for a new pack

1. `mkdir evals && cp <this-repo>/../agentic-creator-os/evals/promptfooconfig.yaml evals/` — change
   `value:` to your skill name, rewrite the 2–3 golden cases for that skill's real triggers.
2. Copy `.github/workflows/skill-evals.yml` — no edits needed (path-triggered on `SKILL.md` + the config).
3. Copy `pack.meta.yaml` — set `name/repo/version/license/origin`, list each gated skill + its
   `skill_version`.
4. Set `CLAUDE_CODE_ENABLE_TELEMETRY=1` in CI env and your shell; point OTel at your Langfuse.
5. Flip the pack's central status: `registry.yaml` → `status.improve: in-progress` while cases are
   being written, `done` once all flagship skills pass the gate in CI.

---

## The skill VERSION is the contract

CI re-runs the gate whenever a skill's `version:` frontmatter changes. Bump the version when you
change a skill's behavior; the gate proves the new version still clears the bar. This is why
`improve=done` can't silently rot — a behavior change *forces* a re-eval.

---

## Portability caveats (author-time honesty)

The worked config carries a **PORTABILITY NOTE**: the exact promptfoo assertion type name
(`skill-used`) and its negation form come from the research corpus, not first-party verification.
Confirm both against your installed promptfoo before the first run; a javascript fallback assertion
is provided inline in the config. **The worked example was authored but NOT executed** on the
constrained authoring machine — see the run command below.

---

## Run it (when on a machine with headroom)

```bash
cd ~/agentic-creator-os
export ANTHROPIC_API_KEY=...            # required by the anthropic provider
export CLAUDE_CODE_ENABLE_TELEMETRY=1   # traces -> self-hosted Langfuse
npx --yes promptfoo@latest eval --config evals/promptfooconfig.yaml --output results.json
npx --yes promptfoo@latest view        # inspect per-metric scores vs the three gates
```

CI does the same automatically on skill-version bumps (`.github/workflows/skill-evals.yml`).
