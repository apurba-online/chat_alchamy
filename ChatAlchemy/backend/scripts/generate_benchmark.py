from __future__ import annotations
import argparse, random, yaml
from pathlib import Path

DRUGS=['pembrolizumab','osimertinib','afatinib','gefitinib','erlotinib','cetuximab','panitumumab','nivolumab','atezolizumab','trastuzumab','imatinib','crizotinib','alectinib','lorlatinib','dabrafenib','trametinib','olaparib','rucaparib','sotorasib','adagrasib']
BRANDS=['Tylenol','Advil','Keytruda','Tagrisso','Herceptin','Gleevec','Tarceva','Iressa','Opdivo','Tecentriq']
TARGETS=['EGFR','ALK','MET','BRAF','KRAS','ERBB2','PARP1','PDCD1','CD274','VEGFA']
DISEASES=['non-small-cell lung cancer','breast cancer','melanoma','colorectal cancer','ovarian cancer','prostate cancer','glioblastoma','pancreatic cancer','renal cell carcinoma','head and neck cancer']
PHASES=['PHASE1','PHASE2','PHASE3','PHASE4']; STATUSES=['RECRUITING','ACTIVE_NOT_RECRUITING','COMPLETED','NOT_YET_RECRUITING']

def single(case_id,q,intent,source,action,args,tags):
    return {'id':case_id,'question':q,'intent':intent,'required_sources':[source],'oracle':{'source':source,'action':action,'arguments':args},'tags':tags}

def generate(seed=17):
    rng=random.Random(seed); cases=[]; templates=[]
    for b in BRANDS: templates.append((f'What is the generic identity of {b}?','identity','rxnorm','resolve',{'drug':b},['single-source','identity']))
    for d in DRUGS: templates += [(f'What DailyMed label records are available for {d}?','label','dailymed','labels',{'drug':d,'max_results':20},['single-source','label']),(f'What FDA approval information is available for {d}?','approval','openfda','approvals',{'drug':d,'max_results':20},['single-source','fda']),(f'What is the PubChem SMILES and IUPAC name for {d}?','compound','pubchem','compound',{'name':d},['single-source','compound'])]
    for t in TARGETS: templates.append((f'Which drugs target {t}?','target_drugs','chembl','target_drugs',{'target':t,'max_results':20},['single-source','target']))
    for disease in DISEASES: templates.append((f'Using Open Targets, show genes associated with {disease}.','disease_targets','opentargets','disease_targets',{'disease':disease,'max_results':20},['single-source','gene-disease']))
    while len(cases)<300:
        q,intent,s,a,args,tags=rng.choice(templates); cases.append(single(f'single_{len(cases):04d}',q,intent,s,a,args,tags))
    for n in range(350):
        target=rng.choice(TARGETS); disease=rng.choice(DISEASES); phase=rng.choice(PHASES); status=rng.choice(STATUSES)
        cases.append({'id':f'cross_{n:04d}','question':f"Which FDA-approved drugs targeting {target} also have {status.replace('_',' ').title()} {phase.replace('PHASE','Phase ')} trials for {disease}?",'intent':'cross_source','required_sources':['chembl','openfda','clinicaltrials'],'oracle':{'kind':'cross_source','target':target,'condition':disease,'phase':phase,'status':status,'max_results':20},'tags':['cross-source','composition']})
    for n in range(250):
        drug=rng.choice(DRUGS); disease=rng.choice(DISEASES); cases.append({'id':f'conflict_{n:04d}','question':f'Compare current evidence for {drug} in {disease} and identify contextual differences without treating distinct trials as contradictions.','intent':'trials','required_sources':['clinicaltrials'],'oracle':{'source':'clinicaltrials','action':'search','arguments':{'drug':drug,'condition':disease,'max_results':20}},'tags':['conflict','context']})
    for n in range(250):
        target=rng.choice(TARGETS); disease=rng.choice(DISEASES); cases.append({'id':f'user_{n:04d}','question':f'Which live drug candidates are relevant to uploaded evidence mentioning target {target} and disease {disease}?','intent':'target_drugs','required_sources':['chembl'],'oracle':{'source':'chembl','action':'target_drugs','arguments':{'target':target,'max_results':20}},'tags':['user-evidence','fusion'],'user_evidence':{'subject':'uploaded_document','predicate':'mentions_target','value':target,'context':{'disease':disease}}})
    for n in range(200):
        drug=rng.choice(DRUGS); disease=rng.choice(DISEASES); phase=rng.choice(PHASES); cases.append({'id':f'temporal_{n:04d}','question':f"List current {phase.replace('PHASE','Phase ')} trials involving {drug} for {disease}.",'intent':'trials','required_sources':['clinicaltrials'],'oracle':{'source':'clinicaltrials','action':'search','arguments':{'drug':drug,'condition':disease,'phase':phase,'max_results':20}},'tags':['temporal','drift']})
    for n in range(150):
        brand=rng.choice(BRANDS); cases.append({'id':f'counterfactual_{n:04d}','question':f'Using only the supplied evidence, identify the canonical drug identity for {brand}.','intent':'identity','required_sources':['rxnorm'],'oracle':{'source':'rxnorm','action':'resolve','arguments':{'drug':brand}},'tags':['counterfactual','failure','grounding']})
    assert len(cases)==1500; return cases

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',default='benchmark/livebioevidencebench_1500.yaml'); p.add_argument('--seed',type=int,default=17); a=p.parse_args(); Path(a.output).write_text(yaml.safe_dump(generate(a.seed),sort_keys=False)); print(f'wrote 1500 cases to {a.output}')
