from chatalchemy.benchmark.temporal import compare_runs


def test_temporal_comparison_detects_change_and_adaptation():
    earlier = {
        "cases": [
            {
                "id": "x",
                "oracle_available": True,
                "oracle": ["A"],
                "prediction": ["A"],
                "task_score": 1.0,
            }
        ]
    }
    later = {
        "cases": [
            {
                "id": "x",
                "oracle_available": True,
                "oracle": ["B"],
                "prediction": ["B"],
                "task_score": 1.0,
            }
        ]
    }
    result = compare_runs(earlier, later)
    assert result["changed_oracle_cases"] == 1
    assert result["temporal_adaptation_score"] == 1.0
    assert result["stale_prediction_rate"] == 0.0
