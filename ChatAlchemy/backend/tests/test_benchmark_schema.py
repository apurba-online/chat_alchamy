from pathlib import Path
import yaml
from chatalchemy.benchmark.schema import BenchmarkCase
def test_seed_benchmark_validates():
    path=Path(__file__).parents[1]/'benchmark'/'live_cases.yaml'; cases=[BenchmarkCase.model_validate(x) for x in yaml.safe_load(path.read_text())]; assert len(cases)>=6 and len({c.id for c in cases})==len(cases)
