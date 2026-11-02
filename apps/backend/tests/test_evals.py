from __future__ import annotations

from app.domains.ai.evals.runner import load_cases, score_output
from tests.test_studio import DRAFT


def test_good_output_scores_full_marks():
    case = {
        "id": "x",
        "notes": "",
        "expect": {"category_contains": ["kurta"], "attributes": {"material": "cotton"}},
    }
    r = score_output(DRAFT, case)
    assert r["gates_passed"] and r["score"] == 1.0 and r["notes"] == []


def test_gates_zero_the_case_on_unsupported_claims():
    bad = {**DRAFT, "captions": {**DRAFT["captions"], "instagram": "Only Rs 999, free delivery!"}}
    r = score_output(bad, {"id": "x", "notes": ""})
    assert r["score"] == 0.0 and not r["gates_passed"] and r["scores"]["grounded"] == 0.0


def test_english_in_nepali_fields_and_invented_sizes_are_penalised():
    out = {
        **DRAFT,
        "title_ne": "Maroon cotton kurta",
        "suggested_options": [{"name": "Size", "values": ["S", "M"]}],
    }
    r = score_output(out, {"id": "x", "notes": "", "expect": {"sizes_known": False}})
    assert r["scores"]["nepali_is_nepali"] == 0.5 and r["scores"]["never_invents_options"] == 0.0
    assert any("title_ne" in n for n in r["notes"])


def test_suite_cases_load():
    cases = load_cases("product_extraction")
    assert {c["id"] for _, c in cases} >= {"kurta-maroon-dhaka", "kurta-with-delivery-note"}
