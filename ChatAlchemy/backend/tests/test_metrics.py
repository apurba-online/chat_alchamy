from chatalchemy.experiments.metrics import set_f1,grounded_obedience_score,parametric_memory_intrusion_rate
def test_metrics(): assert set_f1(['a','b'],['b','c'])==0.5 and grounded_obedience_score([True,False,True])==2/3 and parametric_memory_intrusion_rate([False,True])==0.5
