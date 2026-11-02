# AI Gateway & Dynamic Model Routing

## Objective
No business module directly depends on Claude, OpenAI, Gemini or a media provider SDK.

## Task classes
text; structured extraction; classification; translation; summarization; vision;
image generation/edit; embeddings; moderation; video generation.

## Provider interface
generate_text
generate_structured
analyze_image
generate_image
generate_video
embed
moderate
health_check
estimate_cost

## Routing inputs
task, modality, quality, plan, BYOK preference, capability, latency, error rate,
quota, cost, region/data policy, provider health, seller budget.

## Failover
Primary → bounded retry → circuit breaker → secondary → tertiary.

## BYOK
Business/Enterprise can provide supported keys.
Requirements: encrypted/KMS storage, server-side only, test, rotate, revoke,
usage tracking, fallback policy, never log decrypted secrets.

## Structured AI
Use schema-constrained outputs; validate; store confidence; human-review below threshold.

## Internal tools
get_product, get_inventory, get_price, get_delivery_quote, get_order,
create_order, get_payment_status, get_tracking, check_return_eligibility.

Commercial facts must come from these tools, not model memory.

## Prompt registry
name, task, version, locale, template, tools, schema, eval score, rollout state.

## Evals
Product extraction; Nepali/English copy; order extraction; intent; support;
return decisions; hallucination/grounding.

## Cost
Every execution records provider, model, task, units, cost, charged credits,
merchant, plan, latency and result.
