from chatalchemy.benchmark import generate_cases
from chatalchemy.planner import RuleBasedPlanner


def _entity(plan, kind):
    return next((entity.text for entity in plan.entities if entity.type == kind), None)


def test_planner_core_intents():
    p = RuleBasedPlanner()
    assert p.plan("What is the generic identity of Tylenol?").intent == "identity"
    assert p.plan("Resolve Tylenol to its canonical generic drug identity.").intent == "identity"
    assert p.plan("Identify Tylenol using RxNorm.").entities[0].text == "Tylenol"
    assert p.plan("What DailyMed label records are available for pembrolizumab?").intent == "label"
    assert p.plan("What FDA approval information is available for pembrolizumab?").intent == "approval"
    assert p.plan("List Phase 3 trials involving pembrolizumab for non-small-cell lung cancer.").intent == "trials"
    use_plan = p.plan("Which Phase 3 studies use osimertinib for non-small-cell lung cancer?")
    assert _entity(use_plan, "drug") == "osimertinib"
    assert _entity(use_plan, "condition") == "non-small-cell lung cancer"
    assert p.plan("Which drugs target EGFR?").intent == "target_drugs"
    assert p.plan("Which FDA-approved drugs targeting EGFR also have recruiting Phase 3 trials for non-small-cell lung cancer?").intent == "cross_source"
    assert p.plan("What diseases are associated with gene EGFR in Open Targets?").intent == "gene"
    assert p.plan("What are the PubChem compound properties of gefitinib?").intent == "compound"


def test_natural_disease_gene_questions_use_live_disease_route():
    p = RuleBasedPlanner()
    examples = {
        "What gene is associated with cancer?": "cancer",
        "What genes are associated with cancer?": "cancer",
        "Which genes are responsible for breast cancer?": "breast cancer",
        "What genes are linked with non-small-cell lung cancer?": "non-small-cell lung cancer",
        "Which genes drive melanoma?": "melanoma",
    }
    for question, disease in examples.items():
        plan = p.plan(question)
        assert plan.intent == "disease", (question, plan)
        assert (_entity(plan, "condition") or "").lower() == disease.lower(), (question, plan)
        assert plan.operations[0].source == "opentargets"
        assert plan.operations[0].action == "disease_genes"

    assert p.plan("What gene is associated with cancer?").entities[0].text != "IS"


def test_uploaded_list_queries_keep_correct_condition_and_target():
    p = RuleBasedPlanner()
    plan = p.plan("Which drugs in my uploaded list have recruiting Phase 3 trials for non-small-cell lung cancer?")
    assert plan.intent == "trials"
    assert plan.filters["condition"] == "non-small-cell lung cancer"
    assert plan.filters["phase"] == "PHASE3"
    assert plan.filters["status"] == "RECRUITING"
    assert p.plan("Which drugs in my uploaded list target EGFR?").intent == "target_drugs"


def test_every_frozen_benchmark_task_routes_and_extracts_required_state():
    planner = RuleBasedPlanner()
    cases = generate_cases(1500, 1729)
    for case in cases:
        plan = planner.plan(case.question)
        assert plan.intent == case.expected_operation, (case.id, case.family, case.question, plan)

        if case.family == "identity":
            assert (_entity(plan, "drug") or "").lower() == case.params["drug"].lower(), case.id
        elif case.family in {"label", "approval"}:
            assert (_entity(plan, "drug") or "").lower() == case.params["drug"].lower(), case.id
        elif case.family == "trials":
            assert (_entity(plan, "drug") or "").lower() == case.params["drug"].lower(), case.id
            assert (plan.filters.get("condition") or "").lower() == case.params["condition"].lower(), case.id
            assert plan.filters.get("phase") == case.params["phase"], case.id
            assert plan.filters.get("status") is None, case.id
        elif case.family == "target":
            assert (_entity(plan, "target") or "").upper() == case.params["target"].upper(), case.id
        elif case.family == "cross":
            assert (_entity(plan, "target") or "").upper() == case.params["target"].upper(), case.id
            assert (plan.filters.get("condition") or "").lower() == case.params["condition"].lower(), case.id
            assert plan.filters.get("phase") == case.params["phase"], case.id
            assert plan.filters.get("status") == case.params["status"], case.id
        elif case.family == "gene":
            assert (_entity(plan, "gene") or "").upper() == case.params["gene"].upper(), case.id
        elif case.family == "compound":
            assert (_entity(plan, "compound") or "").lower() == case.params["compound"].lower(), case.id
        elif case.family == "user_approval":
            assert plan.intent == "approval"
        elif case.family == "user_trials":
            assert _entity(plan, "drug") is None, case.id
            assert (plan.filters.get("condition") or "").lower() == case.params["condition"].lower(), case.id
            assert plan.filters.get("phase") == case.params["phase"], case.id
            assert plan.filters.get("status") == case.params["status"], case.id
        elif case.family == "user_target":
            assert (_entity(plan, "target") or "").upper() == case.params["target"].upper(), case.id
