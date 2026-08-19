from chatalchemy.planner.rule_based import RuleBasedPlanner
p=RuleBasedPlanner()
def test_identity():
    plan=p.plan('What is the generic identity of Tylenol?'); assert plan.intent=='identity' and plan.operations[0].source=='rxnorm'
def test_trial_filters():
    plan=p.plan('List recruiting Phase 3 trials involving pembrolizumab for non-small-cell lung cancer.'); assert plan.intent=='trials'; assert plan.filters['phase']=='PHASE3'; assert plan.filters['status']=='RECRUITING'
def test_cross_source():
    plan=p.plan('Which FDA-approved drugs targeting EGFR also have recruiting Phase 3 trials for non-small-cell lung cancer?'); assert plan.intent=='cross_source'; assert [x.source for x in plan.operations]==['chembl','openfda','clinicaltrials']
def test_open_targets(): assert p.plan('Using Open Targets, show genes associated with lung cancer.').intent=='disease_targets'
def test_pubchem(): assert p.plan('What is the PubChem SMILES and IUPAC name for osimertinib?').intent=='compound'
