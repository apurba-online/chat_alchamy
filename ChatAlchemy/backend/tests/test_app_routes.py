from io import BytesIO
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from chatalchemy.app import app
client=TestClient(app)
def test_health_publication_flags():
    r=client.get('/api/health'); assert r.status_code==200; d=r.json(); assert d['local_pharma_database'] is False and d['evidence_state'] is True and d['publication_harness'] is True
def test_csv_parse_route():
    r=client.post('/api/data/parse',files={'file':('tiny.csv',b'drug,score\na,1\nb,2\n','text/csv')}); assert r.status_code==200 and r.json()['rows'][1]['drug']=='b'
def test_xlsx_export_route():
    r=client.post('/api/data/export_xlsx',json={'headers':['drug','score'],'rows':[['a',1],['b',2]]}); assert r.status_code==200; wb=load_workbook(BytesIO(r.content),read_only=True); assert list(wb.active.values)==[('drug','score'),('a',1),('b',2)]
def test_biomedical_extract_has_offline_fallback():
    r=client.post('/api/biomedical/extract',json={'text':'EGFR and TP53 were evaluated in lung cancer. Results were significant.'}); assert r.status_code==200 and 'EGFR' in r.json()['genes'] and 'suggested_diseases' in r.json()
def test_title_has_offline_fallback():
    r=client.post('/api/title',json={'text':'EGFR inhibitors for lung cancer'}); assert r.status_code==200 and r.json()['title']
