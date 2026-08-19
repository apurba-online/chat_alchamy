from chatalchemy.experiments.enrichment import overrepresentation
from chatalchemy.experiments.gene_clustering import cluster_gene_profiles
def test_enrichment_real_hypergeom_and_fdr():
    universe={f'G{i}' for i in range(100)}; query={'G1','G2','G3','G4'}; sets={'A':{'G1','G2','G3','G5','G6'},'B':{'G50','G51'}}; r=overrepresentation(query,sets,universe); assert r and r[0].term=='A' and 0<=r[0].fdr<=1
def test_cluster_uses_profiles_not_gene_prefixes():
    p={'ABC1':{'D1','D2'},'ABC2':{'D9'},'XYZ':{'D1','D2'}}; clusters=cluster_gene_profiles(p,0.5); assert ['ABC1','XYZ'] in clusters and ['ABC2'] in clusters
