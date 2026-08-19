from __future__ import annotations
import asyncio
from typing import Any
from ..evidence import analyze_conflicts
from ..generation import verify_claims
from ..llm import LLMClient
from ..models import Claim,EvidenceItem,QueryResponse,TablePayload
from ..planner import RuleBasedPlanner
from ..sources import ChEMBLSource,ClinicalTrialsSource,DailyMedSource,OpenFDASource,OpenTargetsSource,PubChemSource,RxNormSource
class ChatAlchemyEngine:
    def __init__(self,*,llm:LLMClient|None=None,sources:dict[str,Any]|None=None,use_conflict:bool=True,use_verifier:bool=True):
        self.planner=RuleBasedPlanner();self.use_conflict=use_conflict;self.use_verifier=use_verifier;self.llm=llm or LLMClient();self.sources=sources or {"rxnorm":RxNormSource(),"dailymed":DailyMedSource(),"openfda":OpenFDASource(),"clinicaltrials":ClinicalTrialsSource(),"chembl":ChEMBLSource(),"opentargets":OpenTargetsSource(),"pubchem":PubChemSource()}
    async def close(self):await asyncio.gather(*(s.close() for s in self.sources.values()),return_exceptions=True);await self.llm.close()
    def _finish(self,answer,plan,claims,evidence,traces,warnings,table=None):
        conflicts=analyze_conflicts(evidence) if self.use_conflict else []
        if self.use_verifier:claims,supported=verify_claims(claims,evidence)
        else:supported=1.0 if not claims else sum(bool(c.support_ids) for c in claims)/len(claims)
        return QueryResponse(answer=answer,plan=plan,claims=claims,evidence=evidence,conflicts=conflicts,traces=traces,supported_claim_rate=supported,warnings=list(dict.fromkeys(warnings)),table=table)
    async def answer(self,question:str,max_results:int=20,conversation:list[dict[str,str]]|None=None,user_evidence:list[dict[str,Any]]|None=None)->QueryResponse:
        plan=self.planner.plan(question);evidence=[];traces=[];warnings=[];claims=[];table=None
        if user_evidence:
            for item in user_evidence:evidence.append(EvidenceItem.build(subject=str(item.get("subject") or "user data"),predicate=str(item.get("predicate") or "user_evidence"),value=item.get("value"),qualifiers=item.get("qualifiers") or {},source="UserEvidence",source_record_id=str(item.get("id")) if item.get("id") else None,evidence_type="user"))
        candidates=list(dict.fromkeys(str(x.get("subject") or x.get("value") or "").strip() for x in (user_evidence or []) if x.get("predicate")=="candidate_drug" and str(x.get("subject") or x.get("value") or "").strip()))
        if candidates and plan.intent in {"approval","trials","target_drugs"}:
            answer,ev,tr,claims,table,ws=await self._user_candidate_join(plan,candidates,max_results);evidence.extend(ev);traces.extend(tr);warnings.extend(ws);return self._finish(answer,plan,claims,evidence,traces,warnings,table)
        if plan.intent=="general":
            answer=await self._general_answer(question,conversation or [],user_evidence or []);return QueryResponse(answer=answer,plan=plan,claims=[],evidence=evidence,conflicts=[],traces=[],supported_claim_rate=1.0,warnings=[])
        try:
            if plan.intent=="identity":
                drug=self._first_entity(plan,"drug");result,trace=await self.sources["rxnorm"].traced("resolve",self.sources["rxnorm"].resolve(drug));traces.append(trace);evidence.extend(result)
                if result:
                    e=result[0];answer=f"According to live RxNorm data, **{drug}** resolves to **{e.value}**"+(f" (RxCUI {e.qualifiers['rxcui']})." if e.qualifiers.get("rxcui") else ".");claims=[Claim(text=answer,support_ids=[e.id])]
                else:answer=f"I could not resolve **{drug}** in the live RxNorm service.";warnings.append("No live identity evidence was returned.")
            elif plan.intent=="label":
                drug=self._first_entity(plan,"drug");rows,tr=await self.sources["dailymed"].traced("label_records",self.sources["dailymed"].label_records(drug,max_results=max_results));traces.append(tr);evidence.extend(rows)
                if rows:answer=f"DailyMed returned **{len(rows)} label record(s)** for **{drug}**.";claims=[Claim(text=answer,support_ids=[e.id for e in rows])];table=TablePayload(headers=["Set ID","Label","Published","SPL Version"],rows=[[e.source_record_id,e.value,e.qualifiers.get("published_date"),e.qualifiers.get("spl_version")] for e in rows],caption=f"DailyMed label records for {drug}")
                else:answer=f"No DailyMed label records were returned for **{drug}**."
            elif plan.intent=="approval":
                drug=self._first_entity(plan,"drug");rows,tr=await self.sources["openfda"].traced("approval_records",self.sources["openfda"].approval_records(drug,max_results=max_results));traces.append(tr);evidence.extend(rows)
                if rows:answer=f"Drugs@FDA/openFDA returned **{len(rows)} application record(s)** associated with **{drug}**.";claims=[Claim(text=answer,support_ids=[e.id for e in rows])];table=TablePayload(headers=["Application","Sponsor","Brand names"],rows=[[e.value,e.qualifiers.get("sponsor"),", ".join(e.qualifiers.get("brand_names") or [])] for e in rows],caption=f"FDA application records for {drug}")
                else:answer=f"No Drugs@FDA/openFDA application records were returned for **{drug}**."
            elif plan.intent=="trials":
                drug=self._first_entity(plan,"drug",True);condition=plan.filters.get("condition");phase=plan.filters.get("phase");status=plan.filters.get("status");rows,tr=await self.sources["clinicaltrials"].traced("search_trials",self.sources["clinicaltrials"].search_trials(drug,condition,phase,status,max_results));traces.append(tr);evidence.extend(rows);label=" ".join(x for x in [status.replace("_"," ").title() if status else None,phase.replace("PHASE","Phase ") if phase else None,"trials",f"involving {drug}" if drug else None,f"for {condition}" if condition else None] if x);answer=f"ClinicalTrials.gov returned **{len(rows)} {label.strip()}**."
                if rows:claims=[Claim(text=answer,support_ids=[e.id for e in rows])];table=TablePayload(headers=["NCT ID","Title","Phase","Status","Conditions"],rows=[[e.value,e.qualifiers.get("title"),", ".join(e.qualifiers.get("phases") or []),e.qualifiers.get("status"),", ".join(e.qualifiers.get("conditions") or [])] for e in rows],caption="Live ClinicalTrials.gov results")
            elif plan.intent=="target_drugs":
                target=self._first_entity(plan,"target");rows,tr=await self.sources["chembl"].traced("target_drugs",self.sources["chembl"].target_drugs(target,max_results=max_results));traces.append(tr);evidence.extend(rows);names=[str(e.value) for e in rows];answer=f"ChEMBL returned **{len(names)} drug candidate(s)** with mechanisms linked to **{target}**."+(" Examples: "+", ".join(names[:10])+"." if names else "")
                if rows:claims=[Claim(text=answer,support_ids=[e.id for e in rows])];table=TablePayload(headers=["Drug","ChEMBL ID","Mechanism","Action"],rows=[[e.value,e.qualifiers.get("molecule_chembl_id"),e.qualifiers.get("mechanism"),e.qualifiers.get("action_type")] for e in rows],caption=f"ChEMBL candidates targeting {target}")
            elif plan.intent=="gene":
                gene=self._first_entity(plan,"gene");rows,tr=await self.sources["opentargets"].traced("gene_details",self.sources["opentargets"].gene_details(gene,max_results=max_results));traces.append(tr);evidence.extend(rows);ident=next((e for e in rows if e.predicate=="gene_identity"),None);assoc=[e for e in rows if e.predicate=="gene_disease_association"];known=[e for e in rows if e.predicate=="known_drug"]
                if ident:answer=f"Open Targets resolved **{gene}** as **{ident.value}** and returned **{len(assoc)} disease association(s)** and **{len(known)} known-drug record(s)** in this query.";claims=[Claim(text=answer,support_ids=[e.id for e in rows])]
                else:answer=f"Open Targets returned no target record for **{gene}**."
                table=TablePayload(headers=["Type","Value","Score / Phase","Identifier"],rows=[["Disease",e.value,e.qualifiers.get("score"),e.qualifiers.get("efo_id")] for e in assoc]+[["Drug",e.value,e.qualifiers.get("phase"),e.qualifiers.get("chembl_id")] for e in known],caption=f"Open Targets evidence for {gene}") if rows else None
            elif plan.intent=="disease":
                disease=self._first_entity(plan,"condition");rows,tr=await self.sources["opentargets"].traced("disease_genes",self.sources["opentargets"].disease_genes(disease,max_results=max_results));traces.append(tr);evidence.extend(rows);answer=f"Open Targets returned **{len(rows)} associated target gene(s)** for **{disease}**."
                if rows:claims=[Claim(text=answer,support_ids=[e.id for e in rows])];table=TablePayload(headers=["Gene","Gene name","Ensembl ID","Association score"],rows=[[e.value,e.qualifiers.get("gene_name"),e.qualifiers.get("ensembl_id"),e.qualifiers.get("score")] for e in rows],caption=f"Open Targets genes associated with {disease}")
            elif plan.intent=="compound":
                name=self._first_entity(plan,"compound");rows,tr=await self.sources["pubchem"].traced("compound",self.sources["pubchem"].compound(name));traces.append(tr);evidence.extend(rows)
                if rows:p=rows[0].value;answer=f"PubChem reports CID **{p.get('cid')}** for **{name}**, with canonical SMILES `{p.get('canonical_smiles')}` and IUPAC name **{p.get('iupac_name')}**.";claims=[Claim(text=answer,support_ids=[rows[0].id])];table=TablePayload(headers=["CID","Canonical SMILES","IUPAC name"],rows=[[p.get("cid"),p.get("canonical_smiles"),p.get("iupac_name")]],caption=f"PubChem properties for {name}")
                else:answer=f"PubChem returned no compound properties for **{name}**."
            elif plan.intent=="cross_source":
                answer,ev,tr,claims,table,ws=await self._cross_source(plan,max_results);evidence.extend(ev);traces.extend(tr);warnings.extend(ws)
            else:answer="I could not map that question to a supported evidence operation.";warnings.append("Planner abstained.")
        except Exception as exc:answer="I could not complete the live biomedical query. I will not substitute an unsupported biomedical fact.";warnings.append(str(exc))
        for t in traces:
            if not t.ok:warnings.append(f"{t.source} failed during {t.operation}: {t.error}")
        return self._finish(answer,plan,claims,evidence,traces,warnings,table)
    async def _user_candidate_join(self,plan,candidates,max_results):
        evidence=[];traces=[];warnings=[];rows=[];support_ids=[];accepted=[]
        if plan.intent=="approval":
            async def check(name):return name,await self.sources["openfda"].traced("approval_records",self.sources["openfda"].approval_records(name,3))
            for name,(apps,tr) in await asyncio.gather(*(check(n) for n in candidates[:40])):
                traces.append(tr);evidence.extend(apps)
                if apps:accepted.append(name);support_ids.extend(e.id for e in apps);rows.append([name,", ".join(str(e.value) for e in apps)])
            answer=f"From the uploaded candidate list, **{len(accepted)} drug(s)** had live Drugs@FDA/openFDA application records: "+(", ".join(accepted) if accepted else "none")+".";table=TablePayload(headers=["Uploaded drug","FDA application record(s)"],rows=rows,caption="Uploaded data × live FDA records") if rows else None
        elif plan.intent=="trials":
            condition=plan.filters.get("condition");phase=plan.filters.get("phase");status=plan.filters.get("status")
            async def check(name):return name,await self.sources["clinicaltrials"].traced("search_trials",self.sources["clinicaltrials"].search_trials(name,condition,phase,status,10))
            for name,(trs,tr) in await asyncio.gather(*(check(n) for n in candidates[:30])):
                traces.append(tr);evidence.extend(trs)
                if trs:accepted.append(name);support_ids.extend(e.id for e in trs);rows.append([name,", ".join(str(e.value) for e in trs)])
            answer=f"From the uploaded candidate list, **{len(accepted)} drug(s)** had matching live ClinicalTrials.gov records: "+(", ".join(accepted) if accepted else "none")+".";table=TablePayload(headers=["Uploaded drug","Matching trial(s)"],rows=rows,caption="Uploaded data × live ClinicalTrials.gov") if rows else None
        else:
            target=self._first_entity(plan,"target");drugs,tr=await self.sources["chembl"].traced("target_drugs",self.sources["chembl"].target_drugs(target,max_results=50));traces.append(tr);evidence.extend(drugs);live={str(e.value).lower():e for e in drugs}
            for name in candidates:
                hit=live.get(name.lower())
                if hit:accepted.append(name);support_ids.append(hit.id);rows.append([name,hit.qualifiers.get("molecule_chembl_id"),hit.qualifiers.get("mechanism")])
            answer=f"From the uploaded candidate list, **{len(accepted)} drug(s)** matched live ChEMBL mechanisms for **{target}**: "+(", ".join(accepted) if accepted else "none")+".";table=TablePayload(headers=["Uploaded drug","ChEMBL ID","Mechanism"],rows=rows,caption=f"Uploaded data × ChEMBL target {target}") if rows else None
        return answer,evidence,traces,[Claim(text=answer,support_ids=support_ids)] if support_ids else [],table,warnings
    async def _cross_source(self,plan,max_results):
        target=self._first_entity(plan,"target");condition=plan.filters.get("condition");phase=plan.filters.get("phase");status=plan.filters.get("status");evidence=[];traces=[];warnings=[];candidates,tr=await self.sources["chembl"].traced("target_drugs",self.sources["chembl"].target_drugs(target,max_results=min(max_results,15)));traces.append(tr);evidence.extend(candidates);names=[str(e.value) for e in candidates]
        async def check(name):
            (apps,ta),(trs,tt)=await asyncio.gather(self.sources["openfda"].traced("approval_records",self.sources["openfda"].approval_records(name,max_results=3)),self.sources["clinicaltrials"].traced("search_trials",self.sources["clinicaltrials"].search_trials(name,condition,phase,status,10)));return name,apps,trs,ta,tt
        accepted=[];support_ids=[];rows=[]
        for name,apps,trs,ta,tt in (await asyncio.gather(*(check(n) for n in names[:10])) if names else []):
            traces.extend([ta,tt]);evidence.extend(apps);evidence.extend(trs)
            if apps and trs:accepted.append(name);support_ids.extend(e.id for e in apps+trs);rows.append([name,", ".join(str(e.value) for e in apps),", ".join(str(e.value) for e in trs)])
        answer=f"Using live ChEMBL, Drugs@FDA/openFDA, and ClinicalTrials.gov evidence, **{len(accepted)} candidate(s)** satisfied all requested constraints"+((": "+", ".join(accepted)+".") if accepted else ".");return answer,evidence,traces,[Claim(text=answer,support_ids=support_ids)] if accepted else [],TablePayload(headers=["Drug","FDA application record(s)","Matching trial(s)"],rows=rows,caption=f"Live cross-source intersection for {target}") if rows else None,warnings
    async def _general_answer(self,question,conversation,user_evidence):
        if self.llm.available:
            context="\n".join(f"{m.get('role','user')}: {m.get('content','')}" for m in conversation[-8:]);evidence="\n".join(str(x) for x in user_evidence[:30]);return await self.llm.text("You are ChatAlchemy, a biomedical and pharmaceutical research assistant. Be clear about when you are explaining general knowledge versus using supplied user evidence. Do not invent live database facts; questions requiring current database state should be handled by the evidence engine.",f"Conversation:\n{context}\n\nUser evidence:\n{evidence}\n\nQuestion:\n{question}")
        if user_evidence:return f"I found {len(user_evidence)} supplied evidence item(s). Configure the server-side OPENAI_API_KEY to enable natural-language synthesis of uploaded evidence; deterministic live database queries remain available without it."
        return "I can answer supported live pharmaceutical/biomedical database questions without an LLM. Configure the server-side OPENAI_API_KEY to enable broader conversational explanations."
    @staticmethod
    def _first_entity(plan,entity_type,optional=False):
        for e in plan.entities:
            if e.type==entity_type:return e.text
        if optional:return None
        raise ValueError(f"Planner did not resolve a {entity_type} entity")
