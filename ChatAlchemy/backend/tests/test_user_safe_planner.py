from chatalchemy.planner import RuleBasedPlanner


def _entity(plan, kind):
    return next((entity.text for entity in plan.entities if entity.type == kind), None)


def test_natural_disease_gene_question_routes_to_disease_associations():
    planner = RuleBasedPlanner()

    plural = planner.plan("What genes are responsible for cancer?")
    assert plural.intent == "disease"
    assert _entity(plural, "condition") == "cancer"

    singular = planner.plan("Which gene is responsible for lung cancer?")
    assert singular.intent == "disease"
    assert _entity(singular, "condition") == "lung cancer"


def test_grammar_words_are_not_parsed_as_gene_symbols():
    planner = RuleBasedPlanner()
    plan = planner.plan("Tell me which gene is important here.")
    assert _entity(plan, "gene") is None


def test_explicit_gene_symbol_still_routes_normally():
    planner = RuleBasedPlanner()
    plan = planner.plan("What diseases are associated with gene EGFR in Open Targets?")
    assert plan.intent == "gene"
    assert _entity(plan, "gene") == "EGFR"
