from chatalchemy.benchmark import generate_cases
def test_publication_scale_generator_is_deterministic():
    a=generate_cases(1500,42);b=generate_cases(1500,42);assert len(a)==1500;assert a==b;assert len({x.id for x in a})==1500;assert {x.family for x in a}>={"identity","label","approval","trials","target","cross","gene","compound"}
