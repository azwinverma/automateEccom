# AI Gateway, Model Routing, Grounding & Explanations

> v2 (2026-11-02): adds the Explanation Framework, grounding rules and AI Store Manager tools.

## Objective
No business module depends directly on Claude, OpenAI, Gemini or a media provider SDK
(implemented: `app/domains/ai/gateway.py`, ADR-006).

## Task classes
text; structured extraction; classification; translation; summarization; vision; image
generation/edit; embeddings; moderation; video generation; **insight narrative** (wording an
already-computed explanation).

## Provider interface
generate_text, generate_structured, analyze_image, generate_image, generate_video, embed,
moderate, health_check, estimate_cost.

## Routing inputs
task, modality, quality, plan, BYOK preference, capability, latency, error rate, quota, cost,
region/data policy, provider health, seller budget.

## Failover
Primary → bounded retry → circuit breaker → secondary → tertiary.

## BYOK
For Business/Enterprise: keys stored encrypted (envelope/KMS), server-side only, with test, rotate,
revoke, usage tracking and a fallback policy. Decrypted secrets are never logged.

## Structured AI
- Schema-constrained outputs, validated.
- Confidence is stored; output below threshold goes to human review.
- Commercial claims are checked by the grounding guard (implemented for Studio).

## Internal tools (grounding)
get_product, get_inventory, get_price, get_delivery_quote, get_order, create_order,
get_payment_status, get_tracking, check_return_eligibility.

Intelligence tools (Phase 6+):
get_product_brain, get_autopilot_score, get_memory_facts, get_recommendations,
get_courier_recommendation, get_cod_assessment, get_return_insights, get_supplier_economics,
get_creative_genome, get_twin_section, run_simulation (Phase 9).

**Commercial facts come from these tools, never from model memory.** A tool result carries `as_of`,
and answers state staleness when it matters.

## Explanation Framework
Every important recommendation or automated decision is a structured object:

| Field | Content |
|---|---|
| what_happened | the observed situation, in plain language |
| why | the causal reasoning (rule or model) |
| evidence[] | references to metrics/facts/records with values and windows |
| confidence | 0–1 plus a band (low/medium/high), including data completeness |
| estimated_impact | metric, point estimate and range (e.g. contribution +Rs 4,000 to 7,000/month) |
| recommended_action | a typed command the automation engine can execute after policy/approval |

- The **numbers and evidence are computed deterministically** by intelligence services.
- An LLM may only *phrase* the explanation (task `insight narrative`), constrained to the provided
  evidence. Its output is validated so it introduces no numbers absent from the evidence.
- Bad: "This product is trending." Good: "Black XL may sell out in 5 days because average daily demand
  is 3.2 units and only 16 are available."

## AI Store Manager
An operational intelligence layer, not a generic chatbot.
- **Phase 6 (basic):** answers over Product Brain, Autopilot Score, recommendations, profit, returns,
  couriers.
- **Phase 9 (full):** adds Store Twin and simulation.

Questions it must answer with tools and evidence:
- How is my store doing?
- Which products are losing money?
- What should I promote, and what should I restock?
- Why are returns increasing?
- Which courier should I use for Pokhara?
- What content style performs best, and what should I post tonight?
- Which supplier is actually more profitable?
- What needs my attention?

Answer contract:
- structured (sections plus evidence references)
- confidence and `as_of` included
- actionable items become approval-gated Recommendations
- if data is insufficient, it says so and what data would fix it

## Prompt registry
name, task, version, locale, template, tools, schema, eval score, rollout state (implemented;
DB override).

## Evals
- Product extraction (harness implemented, AIG-015)
- Nepali/English copy
- order extraction; intent; support; return decisions
- hallucination/grounding
- **explanation faithfulness** (narrative introduces no unsupported numbers)
- **recommendation quality** (offline backtest against historical outcomes)

## Cost
Every execution records provider, model, task, units, cost, charged credits, merchant, plan, latency
and result (implemented).
