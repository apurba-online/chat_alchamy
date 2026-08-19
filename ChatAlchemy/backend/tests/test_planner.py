from chatalchemy.planner import RuleBasedPlanner


def test_planner_core_intents():
    p = RuleBasedPlanner()
    assert p.plan("What is the generic identity of Tylenol?").intent == "identity"
    assert p.plan("Resolve Tylenol to its canonical generic drug identity.").intent == "identity"
    assert p.plan("What DailyMed label records are available for pembrolizumab?").intent == "label"
    assert p.plan("What FDA approval information is available for pembrolizumab?").intent == "approval"
    assert p.plan("List Phase 3 trials involving pembrolizumab for non-small-cell lung cancer.").intent == "trials"
    assert p.plan("Which drugs target EGFR?").intent == "target_drugs"
    assert p.plan("Which FDA-approved drugs targeting EGFR also have recruiting Phase 3 trials for non-small-cell lung cancer?").intent == "cross_source"
    assert p.plan("What diseases are associated with gene EGFR in Open Targets?").intent == "gene"
    assert p.plan("What are the PubChem compound properties of gefitinib?").intent == "compound"


def test_uploaded_list_queries_keep_correct_condition_and_target():
    p = RuleBasedPlanner()
    plan = p.plan("Which drugs in my uploaded list have recruiting Phase 3 trials for non-small-cell lung cancer?")
    assert plan.intent == "trials"
    assert plan.filters["condition"] == "non-small-cell lung cancer"
    assert plan.filters["phase"] == "PHASE3"
    assert plan.filters["status"] == "RECRUITING"
    assert p.plan("Which drugs in my uploaded list target EGFR?").intent == "target_drugs"
