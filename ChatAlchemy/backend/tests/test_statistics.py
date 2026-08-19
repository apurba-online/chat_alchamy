from chatalchemy.experiments.statistics import paired_bootstrap_ci,mcnemar_exact,holm_bonferroni
def test_bootstrap_difference_positive():
    obs,lo,hi=paired_bootstrap_ci([1,1,1,0],[0,0,1,0],n_boot=1000,seed=1); assert obs==0.5 and lo<=obs<=hi
def test_mcnemar():
    r=mcnemar_exact([1,1,1,0],[0,0,1,1]); assert r['a_only']==2 and r['b_only']==1 and 0<=r['p_value']<=1
def test_holm():
    r=holm_bonferroni([0.001,0.02,0.2]); assert r[0]['reject'] and not r[2]['reject']
