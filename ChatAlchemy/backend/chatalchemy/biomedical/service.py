from __future__ import annotations
import math,re
from collections import defaultdict
from typing import Any
from ..llm import LLMClient
from ..models import BiomedicalExtractResponse,EvidenceItem
from ..sources import OpenTargetsSource
COMMON_GENE_EXCLUSIONS={"DNA","RNA","PCR","CT","MRI","FDA","WHO","USA","COVID","HIV","ATP","ADP","AND","THE"};GENE_RE=re.compile(r"\b[A-Z][A-Z0-9-]{1,10}\b")
class BiomedicalService:
    def __init__(self,llm:LLMClient,opentargets:OpenTargetsSource):self.llm=llm;self.opentargets=opentargets
    async def extract_document(self,text:str,filename:str|None=None)->BiomedicalExtractResponse:
        cleaned=" ".join(text.split())
        if self.llm.available:
            schema={"type":"object","additionalProperties":False,"properties":{"summary":{"type":"string"},"genes":{"type":"array","items":{"type":"string"}},"suggested_diseases":{"type":"array","items":{"type":"string"}}},"required":["summary","genes","suggested_diseases"]};result=await self.llm.json("You are a biomedical research extraction system. Summarize the supplied document and extract only explicitly mentioned human gene symbols and explicitly mentioned diseases/conditions. Do not infer genes that are not written in the document.",cleaned[:100000],"biomedical_document",schema);return BiomedicalExtractResponse(summary=result.get("summary",""),genes=sorted(set(g.upper() for g in result.get("genes",[]) if g)),suggested_diseases=sorted(set(result.get("suggested_diseases",[]))))
        genes=sorted({g for g in GENE_RE.findall(cleaned) if g not in COMMON_GENE_EXCLUSIONS})[:50];sentences=re.split(r"(?<=[.!?])\s+",cleaned);summary=" ".join(sentences[:5])[:1800] or f"Processed {filename or 'document'}; no textual summary was available.";return BiomedicalExtractResponse(summary=summary,genes=genes,suggested_diseases=[])
    @staticmethod
    def benjamini_hochberg(p_values:list[float])->list[float]:
        n=len(p_values);order=sorted(range(n),key=lambda i:p_values[i]);adjusted=[1.0]*n;prev=1.0
        for rank_from_end,idx in enumerate(reversed(order),start=1):rank=n-rank_from_end+1;val=min(prev,p_values[idx]*n/rank);adjusted[idx]=min(1.0,val);prev=val
        return adjusted
    @staticmethod
    def hypergeom_tail(k:int,K:int,n:int,N:int)->float:
        if any(x<0 for x in [k,K,n,N]) or K>N or n>N:return 1.0
        denom=math.comb(N,n)
        if denom==0:return 1.0
        return min(1.0,sum(math.comb(K,i)*math.comb(N-K,n-i) for i in range(k,min(K,n)+1) if n-i<=N-K)/denom)
    async def analyze(self,genes:list[str],query:str|None,paper_summary:str|None=None)->dict[str,Any]:
        genes=sorted({g.strip().upper() for g in genes if g.strip()});evidence=[]
        if query:
            de=await self.opentargets.disease_genes(query,max_results=50);evidence.extend(de);symbols={str(e.value).upper() for e in de};genes=[g for g in genes if g in symbols] if genes else list(symbols)
        gene_rows=[];graph_nodes={};graph_edges=[];disease_to_genes=defaultdict(set)
        for gene in genes[:50]:
            ev=await self.opentargets.gene_details(gene,max_results=10);evidence.extend(ev);ident=next((x for x in ev if x.predicate=="gene_identity"),None);assoc=[x for x in ev if x.predicate=="gene_disease_association"];avg=sum(float(x.qualifiers.get("score") or 0) for x in assoc)/len(assoc) if assoc else 0.0;ensembl=ident.qualifiers.get("ensembl_id") if ident else None;disease_text=", ".join(f"{x.value} [{x.qualifiers.get('efo_id','')}] [{float(x.qualifiers.get('score') or 0):.3f}]" for x in assoc);gene_rows.append([gene,ident.value if ident else "",ensembl or "",f"{avg:.3f}",disease_text or "No disease associations found"]);graph_nodes[f"gene:{gene}"]={"data":{"id":f"gene:{gene}","label":gene,"type":"gene"}}
            for a in assoc:
                disease=str(a.value);did=str(a.qualifiers.get("efo_id") or disease);disease_to_genes[disease].add(gene);graph_nodes[f"disease:{did}"]={"data":{"id":f"disease:{did}","label":disease,"type":"disease"}};graph_edges.append({"data":{"source":f"gene:{gene}","target":f"disease:{did}","label":"associated","weight":max(1.0,float(a.qualifiers.get("score") or 0)*5),"type":"disease-gene"}})
            for d in [x for x in ev if x.predicate=="known_drug"]:
                name=str(d.value);chembl=str(d.qualifiers.get("chembl_id") or name);graph_nodes[f"drug:{chembl}"]={"data":{"id":f"drug:{chembl}","label":name,"type":"drug"}};graph_edges.append({"data":{"source":f"drug:{chembl}","target":f"gene:{gene}","label":"targets","weight":max(1,int(d.qualifiers.get("phase") or 1)),"type":"drug-gene"}})
        profiles={g:set() for g in genes}
        for disease,gs in disease_to_genes.items():
            for g in gs:profiles.setdefault(g,set()).add(disease)
        parent={g:g for g in genes}
        def find(x):
            while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
            return x
        def union(a,b):
            ra,rb=find(a),find(b)
            if ra!=rb:parent[rb]=ra
        for i,a in enumerate(genes):
            for b in genes[i+1:]:
                A,B=profiles.get(a,set()),profiles.get(b,set())
                if A and B and len(A&B)/len(A|B)>=0.25:union(a,b)
        clusters_map=defaultdict(list)
        for g in genes:clusters_map[find(g)].append(g)
        clusters=[{"id":i+1,"genes":gs,"description":"Genes grouped by shared Open Targets disease-association profiles"} for i,gs in enumerate(clusters_map.values())]
        N=20000;n=max(1,len(genes));raw=[]
        for disease,gs in disease_to_genes.items():
            overlap=sorted(set(genes)&gs)
            if overlap:K=max(len(gs),len(overlap));raw.append({"term":disease,"genes":overlap,"pValue":self.hypergeom_tail(len(overlap),K,n,N)})
        qvals=self.benjamini_hochberg([r["pValue"] for r in raw]) if raw else [];enrichment=[{**r,"adjustedPValue":q} for r,q in zip(raw,qvals)];enrichment.sort(key=lambda r:r["adjustedPValue"]);explanation=f"Analyzed {len(genes)} gene(s) using live Open Targets evidence."+(f" The analysis was restricted to associations with {query}." if query else "")+(" Results can be continued in chat together with the uploaded paper summary." if paper_summary else "")
        return {"genes":genes,"paperSummary":paper_summary,"explanation":explanation,"tableData":{"headers":["Gene Symbol","Gene Name","Ensembl ID","Avg. Association Score","Top Associated Diseases [EFO ID] [Score]"],"rows":gene_rows,"caption":f"Gene Associations for {query}" if query else "Gene Details"},"clusters":clusters,"enrichmentResults":enrichment[:25],"networkData":list(graph_nodes.values())+graph_edges,"evidence":[e.model_dump() for e in evidence]}
