from __future__ import annotations
from ..models import EvidenceItem
from .base import LiveSource
class OpenTargetsSource(LiveSource):
    name="Open Targets";endpoint="https://api.platform.opentargets.org/api/v4/graphql"
    async def gene_details(self,gene:str,max_results:int=10)->list[EvidenceItem]:
        search='''query Search($q: String!) { search(queryString: $q, entityNames: ["target"]) { hits { id object { ... on Target { id approvedSymbol approvedName } } } } }''';found=await self._post_json(self.endpoint,{"query":search,"variables":{"q":gene}});hits=(((found.get("data") or {}).get("search") or {}).get("hits") or [])
        if not hits:return[]
        target=hits[0].get("object") or {};tid=target.get("id")
        if not tid:return[]
        q='''query Target($id: String!) { target(ensemblId: $id) { id approvedSymbol approvedName associatedDiseases(page:{index:0,size:10}) { rows { disease { id name } score } } knownDrugs { rows { drug { id name } disease { id name } phase status } } } }''';obj=((await self._post_json(self.endpoint,{"query":q,"variables":{"id":tid}})).get("data") or {}).get("target") or {};symbol=obj.get("approvedSymbol") or gene;out=[EvidenceItem.build(subject=symbol,predicate="gene_identity",value=obj.get("approvedName") or symbol,qualifiers={"ensembl_id":tid},source=self.name,source_record_id=tid,source_url=f"https://platform.opentargets.org/target/{tid}")]
        for row in ((obj.get("associatedDiseases") or {}).get("rows") or [])[:max_results]:
            d=row.get("disease") or {};out.append(EvidenceItem.build(subject=symbol,predicate="gene_disease_association",value=d.get("name"),qualifiers={"efo_id":d.get("id"),"score":row.get("score")},source=self.name,source_record_id=d.get("id"),source_url=f"https://platform.opentargets.org/disease/{d.get('id')}" if d.get("id") else None))
        for row in ((obj.get("knownDrugs") or {}).get("rows") or [])[:max_results]:
            drug=row.get("drug") or {};disease=row.get("disease") or {};out.append(EvidenceItem.build(subject=symbol,predicate="known_drug",value=drug.get("name"),qualifiers={"chembl_id":drug.get("id"),"disease":disease.get("name"),"efo_id":disease.get("id"),"phase":row.get("phase"),"status":row.get("status")},source=self.name,source_record_id=drug.get("id"),source_url=f"https://platform.opentargets.org/target/{tid}"))
        return out
    async def disease_genes(self,disease:str,max_results:int=20)->list[EvidenceItem]:
        search='''query Search($q: String!) { search(queryString: $q, entityNames: ["disease"]) { hits { id object { ... on Disease { id name } } } } }''';found=await self._post_json(self.endpoint,{"query":search,"variables":{"q":disease}});hits=(((found.get("data") or {}).get("search") or {}).get("hits") or [])
        if not hits:return[]
        dobj=hits[0].get("object") or {};did=dobj.get("id")
        if not did:return[]
        q='''query Disease($id: String!) { disease(efoId: $id) { id name associatedTargets(page:{index:0,size:50}) { rows { target { id approvedSymbol approvedName } score } } } }''';obj=((await self._post_json(self.endpoint,{"query":q,"variables":{"id":did}})).get("data") or {}).get("disease") or {};out=[]
        for row in ((obj.get("associatedTargets") or {}).get("rows") or [])[:max_results]:
            t=row.get("target") or {};out.append(EvidenceItem.build(subject=obj.get("name") or disease,predicate="disease_gene_association",value=t.get("approvedSymbol"),qualifiers={"ensembl_id":t.get("id"),"gene_name":t.get("approvedName"),"efo_id":did,"score":row.get("score")},source=self.name,source_record_id=t.get("id"),source_url=f"https://platform.opentargets.org/disease/{did}"))
        return out
