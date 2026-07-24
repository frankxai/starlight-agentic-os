# Production Domain Inventory

**Date:** 2026-07-24 · **Source of truth:** live Vercel account (`vercel project ls` +
`vercel domains ls`, scope `starlight-intelligence`, user `frankx-eth`) — the authoritative
current state, not a stale doc.

> **Method note:** The named baseline `production-baseline-2026-07-20.md` was **not found on
> disk** (only unrelated `FrankX/.frankx/machine/agent-quality-baseline-2026-06-11.json` and
> `FrankX/docs/design/VITALS_BASELINE_2026-04-23.md` exist). This inventory is therefore built
> from the **live Vercel API** as the authoritative source. Repo mappings are from known
> ecosystem memory; any marked `(verify)` need a repo confirmation.

---

## 🚫 SCOPE GUARDRAIL for the audit swarm

- **`frankx.ai` HOMEPAGE (`/`) — APPROVED, DO NOT TOUCH.**
- **`arcanea.ai` HOMEPAGE (`/`) — APPROVED, DO NOT TOUCH.**
- **In scope for review:** every **subpage** of those two domains (`/anything` except `/`),
  **and all other domains/sites below** in full.

25 custom domains are registered; ~60 Vercel projects exist (many are `v0-*` experiments with no
production domain — bucketed at the end).

---

## Tier 1 — Flagship live domains (highest audit priority)

| Domain | Vercel project | Repo | Status | Audit scope |
|---|---|---|---|---|
| **frankx.ai** / www | `frankx-ai-vercel-website` | `frankxai/frankx.ai-vercel-website` | 🟢 live (updated 15h) | **Homepage OFF-LIMITS**; all subpages in scope |
| **arcanea.ai** | `arcanea-ai-app` | `frankxai/arcanea-ai-app` | 🟢 live | **Homepage OFF-LIMITS**; all subpages in scope |
| starlightintelligence.org | `site` | `frankxai/Starlight-Intelligence-System` (site/) | 🟢 live | full |
| gencreator.ai | `gencreator-ai` | `frankxai/gencreator.ai` | 🟢 live | full |
| agenticincome.ai / www | `agenticincome` | income trinity (`~/income`) | 🟢 live | full |
| go.agenticincome.ai | `go-agenticincome` | income trinity | 🟢 live | full |
| agenticpassiveincome.com / www | `agenticpassiveincome` | income trinity | 🟢 live | full |
| disruptivepassiveincome.com | `disruptivepassiveincome` / `dpi-open-core` | dpi (`~/income` dpi) | 🟢 live (dpi-open-core on *.vercel.app) | full |
| animelegends.ai / www | `anime-legends` | AnimeLegends studio repo (verify) | 🟢 live | full |
| realityarchitect.ai / www | `realityarchitect` | `realityarchitect-vault` (verify) | 🟢 live | full |
| oceanintelligence.app | `ocean-intelligence` | Ocean/marine repo (`marine-agent-skills` adjacent, verify) | 🟢 live | full |

## Tier 2 — Arcanea ecosystem domains

| Domain | Vercel project | Repo | Status | Audit scope |
|---|---|---|---|---|
| arcanea.dev | `arcanea-domain-portals` | arcanea ecosystem (verify) | 🟢 live | full |
| arcanea.academy | `arcanea-academy` | arcanea ecosystem (verify) | 🟢 live | full |
| lobe.arcanea.ai | `arcanea-lobechat-labs` | LobeChat fork (verify) | 🟢 live | full |
| arcanean.org | (portal) | arcanea ecosystem (verify) | 🟡 domain reg, portal | full |
| arcanealabs.com | (portal) | arcanea ecosystem (verify) | 🟡 domain reg, portal | full |

## Tier 3 — Other live product/community domains

| Domain | Vercel project | Repo | Status | Audit scope |
|---|---|---|---|---|
| cecilia.chat | `cecilia-chat` | cecilia (client, verify) | 🟢 live | full |
| anaceciliacancino.com | `ana` | cecilia/ana (client, verify) | 🟢 live | full |
| aiarchitectacademy.com | `aiarchitectacademy` | AI Architect Academy (verify) | 🟢 live | full |
| starlightintelligence.academy | `starlight-intelligence-academy` | SIS academy (verify) | 🟢 live | full |
| gencreator.community | `gencreator-community` | gencreator (verify) | 🟢 live | full |
| bluelifecommons.org | `blue-life-commons` | blue-life-commons (verify) | 🟢 live | full |
| vibeclubs.ai | `vibeclubs-web` | vibeclubs (verify) | 🟢 live | full |

## Tier 4 — Registered but parked / newly-acquired (verify intent before audit)

| Domain | Notes |
|---|---|
| starlightintelligence.ai | registered 6d ago — parked/redirect? (verify) |
| starlight.you / starlight.technology / starlight.domains | registered 6d ago — Starlight brand land-grab, likely parked |
| *(no separate project seen)* | confirm each resolves before auditing |

## Bucket — Experiments / templates (no production domain; low audit priority)

`*.vercel.app`-only or no-deploy projects: `agentic-intelligence-system`, `starlight-intelligence`,
`ana` variants, `dpi-open-core` (\*.vercel.app), `arcanea-ai-app(x)` staging, `vibeclubs-web`,
`agentic-gym-os`, `frankx-community-hub`, `author-os`, `ag-student-os`, `web`,
`family-intelligence-os`, `rova-resort`, `anime-studio-landing`, `trinityaicoaching`,
`saas-ai-architect-academy`, `lobe-chat-*`, `frankx-lobe-chat`, `my-library`, and ~15 `v0-*`
prototypes (`v0-ai-misuse-mitigation`, `v0-opus-landing-page`, `v0-nano-banana-pro-playground`,
`v0-audio-visualizer`, `v0-agent-builder`, `v0-ai-gateway-starter`, etc.).
No-prod-deploy projects (`--`): `frankx-codex-plugins-team-blog`, `frankx-ai-architecture-20260712`,
`grok-creative-studio`, `agentmail-template-starkhq`, `frankx-vision-deploy`, and several dated snapshots.

**Recommendation:** the audit swarm's first wave targets Tier 1 (subpages only for frankx.ai /
arcanea.ai), then Tier 2–3. Skip Tier 4/experiments unless a domain is being promoted to production.

---

## Full custom-domain list (25 — for the swarm seed)

`frankx.ai` · `arcanea.ai` · `starlightintelligence.org` · `gencreator.ai` · `agenticincome.ai` ·
`agenticpassiveincome.com` · `disruptivepassiveincome.com` · `animelegends.ai` ·
`realityarchitect.ai` · `oceanintelligence.app` · `arcanea.dev` · `arcanea.academy` ·
`arcanean.org` · `arcanealabs.com` · `aiarchitectacademy.com` · `starlightintelligence.academy` ·
`gencreator.community` · `bluelifecommons.org` · `vibeclubs.ai` · `cecilia.chat` ·
`anaceciliacancino.com` · `starlightintelligence.ai` · `starlight.you` · `starlight.technology` ·
`starlight.domains`

*(Subdomain in use: `go.agenticincome.ai`, `lobe.arcanea.ai`.)*
