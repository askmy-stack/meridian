# MISTAKES.md — Errors, Learnings, and Understanding

> Read this before writing code. Every entry here was expensive.
> Agent: check this file when you hit a wall — the answer may already be here.
> Owner: add entries whenever something breaks, a decision turns out wrong, or an assumption was invalid.

---

## Entry Format

```
### [M-NNN] — [DATE] — [Short title]
**Phase:** [Which build phase]
**Type:** Architecture / Data / ML / Infra / Product / Process
**What happened:** [Specific description of the mistake or false assumption]
**Why it happened:** [Root cause]
**Impact:** [What it cost — time, rework, design change]
**Fix / Learning:** [What was done or should be done differently]
**Prevents:** [What future mistake this entry prevents]
```

---

## MISTAKES LOG

### [M-001] — 2026-05-09 — Assuming GDELT event schema is stable
**Phase:** Phase 0 (pre-build)
**Type:** Data
**What happened:** Architecture assumed GDELT events would have consistent schema. GDELT actually has two different data formats (GDELT 1.0 events and GDELT 2.0 GKG — Global Knowledge Graph) with completely different schemas and update frequencies.
**Why it happened:** Designed data model without fetching and inspecting actual GDELT output.
**Impact:** Entity resolution design may need revision once real schema is confirmed.
**Fix / Learning:** Before writing any producer, fetch 10 real events from the source and inspect actual field names, types, and nullability. Never design against documentation alone.
**Prevents:** Building parsers against wrong schemas, silent data loss from unexpected null fields.

---

### [M-002] — 2026-05-09 — Architecture over-scoped for MVP
**Phase:** Phase 0 (planning)
**Type:** Product / Process
**What happened:** Full architecture includes TGN, HMM, DoWhy causal inference, Node2Vec, RL agent, fine-tuned LLM, RAG — all in the initial design. Risk: building infrastructure for 6 months and never shipping a demo.
**Why it happened:** Optimizing for technical depth (portfolio signal) over shipping speed (job search timeline).
**Impact:** None yet — caught in planning. But classic pattern: build everything, demo nothing.
**Fix / Learning:** MVP must be demoable in 6 weeks with: Kafka ingestion (GDELT + AIS) + Neo4j graph + XGBoost risk scorer + basic Mapbox dashboard. TGN, HMM, causal inference are Phase 6+ — document them in architecture but don't block MVP on them.
**Prevents:** 3-month build with no demo, zero GitHub stars, zero recruiter signal.

---

### [M-003] — 2026-05-09 — Conflating "interesting architecture" with "recruiter legible"
**Phase:** Phase 0 (planning)
**Type:** Product / Process
**What happened:** TGN and causal inference are genuinely novel — but a recruiter looking at the repo in 30 seconds needs to understand what the project does, not how the ML works. README was initially too technical.
**Why it happened:** Writing for ML engineers, not for the first 30 seconds of recruiter attention.
**Impact:** README revised to lead with problem statement and use case, not architecture.
**Fix / Learning:** README structure: Problem → Demo GIF (add this) → What it does → Tech stack → Quickstart. Architecture details go in ARCHITECTURE.md, not README.
**Prevents:** Technically impressive repo that nobody stars because they don't understand it in 30 seconds.

---

### [M-004] — 2026-05-09 — No demo video / GIF planned in initial scope
**Phase:** Phase 0 (planning)
**Type:** Product
**What happened:** Launch plan mentioned HN post and LinkedIn post but no demo video or animated GIF for README.
**Why it happened:** Focused on technical build, not distribution.
**Impact:** Open-source repos without demo GIFs get significantly fewer stars. HN posts without demos get fewer upvotes.
**Fix / Learning:** Week 6 deliverable must include: 60-second Loom demo video + animated GIF of disruption simulator for README. Plan this in advance — don't bolt it on after the fact.
**Prevents:** Shipping a working product that nobody engages with because there's no hook.

---

### [M-005] — 2026-05-09 — AIS free tier limitations not validated
**Phase:** Phase 0 (planning)
**Type:** Data
**What happened:** Architecture assumes AISHub free tier provides sufficient vessel position data for meaningful risk signals. Free tier may have rate limits, geographic coverage gaps, or delayed data that make it unsuitable for real-time risk scoring.
**Why it happened:** Assumed free tier would be sufficient without reading AISHub's actual tier comparison.
**Impact:** May need to redesign AIS ingestion to work with delayed / sampled data rather than real-time.
**Fix / Learning:** Before Phase 1: register AISHub account, test actual free tier data quality and latency. If insufficient: use MarineTraffic free tier, or scrape public vessel tracking sites, or use VesselFinder API (freemium).
**Prevents:** Building real-time AIS pipeline that gets throttled or blocked on day 1.

---

## LEARNINGS (positive — things that worked well)

### [L-001] — 2026-05-09 — Graph-first thinking unlocks the whole product
**What:** Framing the entire problem as a knowledge graph (Supplier → Port → Chokepoint → Conflict) rather than a feature table immediately makes the disruption propagation and alternative supplier recommendation tractable. The graph is not just storage — it IS the product logic.
**Why it matters:** Keeps all risk propagation in Neo4j Cypher queries, which are readable and auditable. Avoids building complex application-layer traversal logic that would be brittle and hard to explain.
**Apply to:** Every new feature — ask "can this be a graph query?" before writing application code.

---

### [L-002] — 2026-05-09 — SHAP as product feature, not just ML hygiene
**What:** SHAP explainability was initially framed as a technical requirement. Reframed as a user-facing product feature: every risk score shows the top 3 drivers in plain English. This transforms the product from "alert system" to "intelligence system."
**Why it matters:** Procurement teams don't act on opaque scores. They act on scores they can defend to their CFO. SHAP output IS the justification for the sourcing decision.
**Apply to:** Any ML model output that feeds into user-visible recommendations.

---

### [L-003] — 2026-05-09 — Causal inference as trust mechanism
**What:** DoWhy causal inference isn't just better ML — it's the mechanism that prevents false positive alerts that destroy user trust. One bad alert that procurement acts on and finds wrong = system abandoned.
**Why it matters:** Supply chain risk tools live or die on trust. Statistical correlation models produce false positives at scale. Causal models are harder to build but produce alerts that hold up under scrutiny.
**Apply to:** Any risk signal before it triggers an alert. Always ask: is this causal or correlational?

---

### [L-004] — 2026-05-09 — Open-source distribution is a force multiplier for portfolio
**What:** A working open-source project with GitHub stars, a HN Show HN post, and community engagement is worth more than a private portfolio project for job search signal — especially for AI/ML Engineer roles at Series B+ startups.
**Why it matters:** Recruiters at target companies (Palantir, Anduril, Scale AI, Cohere, etc.) look at GitHub. Stars and forks are social proof that the technical work is real and valued.
**Apply to:** Every build decision — ask "would this make a better open-source project?" not just "does this demonstrate my skills?"
