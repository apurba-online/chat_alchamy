from chatalchemy.planner import RuleBasedPlanner


def test_identity_plan():
    plan = RuleBasedPlanner().plan("What is the generic identity of Tylenol?")
    assert plan.intent == "identity"
    assert plan.entities[0].type == "drug"
    assert plan.entities[0].text == "Tylenol"
    assert [op.source for op in plan.operations] == ["rxnorm"]


def test_trial_plan():
    plan = RuleBasedPlanner().plan("How many recruiting Phase 3 trials involve pembrolizumab for non-small-cell lung cancer?")
    assert plan.intent == "trials"
    assert plan.filters["phase"] == "PHASE3"
    assert plan.filters["status"] == "RECRUITING"
    assert next(e.text for e in plan.entities if e.type == "drug") == "pembrolizumab"
    assert next(e.text for e in plan.entities if e.type == "condition") == "non-small-cell lung cancer"
    assert plan.final_operation == "count"


def test_cross_source_plan():
    plan = RuleBasedPlanner().plan("Which FDA-approved drugs targeting EGFR also have recruiting Phase 3 trials for non-small-cell lung cancer?")
    assert plan.intent == "cross_source"
    assert next(e.text for e in plan.entities if e.type == "target") == "EGFR"
    assert plan.filters["phase"] == "PHASE3"
    assert plan.filters["status"] == "RECRUITING"
    assert {op.source for op in plan.operations} == {"chembl", "openfda", "clinicaltrials"}


def test_dailymed_label_plan():
    plan = RuleBasedPlanner().plan("What DailyMed label records are available for pembrolizumab?")
    assert plan.intent == "label"
    assert {op.source for op in plan.operations} == {"rxnorm", "dailymed"}
