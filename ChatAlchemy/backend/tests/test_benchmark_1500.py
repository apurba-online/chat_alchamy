import importlib.util
from pathlib import Path
def test_generator_has_exact_publication_scale():
    path=Path(__file__).parents[1]/'scripts'/'generate_benchmark.py'; spec=importlib.util.spec_from_file_location('genbench',path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); cases=mod.generate(17); assert len(cases)==1500; tags=[t for c in cases for t in c['tags']]; assert tags.count('cross-source')==350 and tags.count('temporal')==200 and tags.count('counterfactual')==150
