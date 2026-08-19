from chatalchemy.biomedical.service import BiomedicalService
def test_bh_monotonic_by_sorted_p():
    p=[0.01,0.04,0.03,0.2];q=BiomedicalService.benjamini_hochberg(p);assert all(0<=x<=1 for x in q);pairs=sorted(zip(p,q));assert all(pairs[i][1]<=pairs[i+1][1] for i in range(len(pairs)-1))
def test_hypergeom_reasonable():assert 0<=BiomedicalService.hypergeom_tail(3,20,10,1000)<=1
