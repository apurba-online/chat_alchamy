from __future__ import annotations
import argparse,json,pathlib,yaml

def perturb_identity(value:str)->str: return f"COUNTERFACTUAL_{value.replace(' ','_').upper()}"
def main(cases_path,output):
    raw=yaml.safe_load(pathlib.Path(cases_path).read_text()); cases=[x for x in raw if 'counterfactual' in x.get('tags',[])]; rows=[]
    for case in cases:
        drug=case['oracle']['arguments']['drug']; rows.append({'id':case['id'],'original_entity':drug,'counterfactual_value':perturb_identity(drug),'grounded_obedience':None,'parametric_memory_intrusion':None})
    pathlib.Path(output).write_text(json.dumps({'protocol':'in-memory-only; upstream APIs are never modified','cases':rows},indent=2)); print(f'wrote {len(rows)} counterfactual protocol cases')
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--cases',default='benchmark/livebioevidencebench_1500.yaml'); p.add_argument('--output',default='counterfactual_protocol.json'); a=p.parse_args(); main(a.cases,a.output)
