from __future__ import annotations
from typing import Any
from .sources.opentargets import OpenTargetsSource
from .sources.chembl import ChEMBLSource
from .sources.gprofiler import GProfilerSource
from .experiments.gene_clustering import cluster_gene_profiles

class BiomedicalService:
    def __init__(self):
        self.ot=OpenTargetsSource(); self.chembl=ChEMBLSource(); self.gprofiler=GProfilerSource()

    async def analyze(self, genes:list[str], query:str|None=None, suggested_diseases:list[str]|None=None, paper_summary:str|None=None)->dict[str,Any]:
        genes=sorted({g.strip().upper() for g in genes if g and g.strip()}); evidence=[]
        if query:
            disease_ev,_=await self.ot.disease_targets(query,max_results=50); evidence.extend(disease_ev)
            live_genes=[str(e.value).upper() for e in disease_ev if e.value]
            genes=[g for g in genes if g in live_genes] if genes else live_genes
        rows=[]; nodes={}; edges=[]; profiles={g:set() for g in genes}
        for gene in genes[:50]:
            disease_ev,_=await self.ot.gene_diseases(gene,max_results=15); evidence.extend(disease_ev); scores=[]; disease_labels=[]; nodes[f'gene:{gene}']={'data':{'id':f'gene:{gene}','label':gene,'type':'gene'}}; ensembl=''
            for e in disease_ev:
                ensembl=e.identifiers.get('ensembl_id',ensembl); d=str(e.value); did=e.identifiers.get('efo_id') or d; score=float(e.context.get('association_score') or 0); scores.append(score); profiles[gene].add(d); disease_labels.append(f"{d} [{did}] [{score:.3f}]"); nodes[f'disease:{did}']={'data':{'id':f'disease:{did}','label':d,'type':'disease'}}; edges.append({'data':{'source':f'gene:{gene}','target':f'disease:{did}','label':'associated','weight':max(1.0,score*5),'type':'disease-gene'}})
            try: drug_ev,_=await self.chembl.target_drugs(gene,max_results=8)
            except Exception: drug_ev=[]
            evidence.extend(drug_ev)
            for d in drug_ev:
                name=str(d.value); mid=d.identifiers.get('chembl_id') or name; nodes[f'drug:{mid}']={'data':{'id':f'drug:{mid}','label':name,'type':'drug'}}; edges.append({'data':{'source':f'drug:{mid}','target':f'gene:{gene}','label':'targets','weight':1.5,'type':'drug-gene'}})
            rows.append([gene,gene,ensembl,f"{sum(scores)/len(scores):.3f}" if scores else '0.000',', '.join(disease_labels) or 'No disease associations found'])
        clusters=[{'id':i+1,'genes':c,'description':'Genes grouped by shared live disease-association profiles'} for i,c in enumerate(cluster_gene_profiles(profiles,threshold=0.25) if genes else [])]
        try: enrichment,_=await self.gprofiler.enrich(genes) if genes else ([],0.0)
        except Exception: enrichment=[]
        enrichment_results=[{'term':r.get('term_name') or r.get('term_id'),'genes':r.get('intersection') or [],'pValue':r.get('p_value'),'adjustedPValue':r.get('p_value'),'source':r.get('source')} for r in enrichment[:25]]
        explanation=f"Analyzed {len(genes)} gene(s) using live Open Targets and ChEMBL evidence."+(f" The analysis was restricted to associations with {query}." if query else '')
        return {'genes':genes,'paperSummary':paper_summary,'suggestedDiseases':suggested_diseases or [],'explanation':explanation,'tableData':{'headers':['Gene Symbol','Gene Name','Ensembl ID','Avg. Association Score','Top Associated Diseases [EFO ID] [Score]'],'rows':rows,'caption':f'Gene Associations for {query}' if query else 'Gene Details'},'clusters':clusters,'enrichmentResults':enrichment_results,'networkData':list(nodes.values())+edges,'evidence':[e.model_dump(mode='json') for e in evidence]}
