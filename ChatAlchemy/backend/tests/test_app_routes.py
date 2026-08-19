from io import BytesIO
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from chatalchemy.app import app

def test_health_and_data_routes():
    with TestClient(app) as client:
        h=client.get('/api/health'); assert h.status_code==200 and h.json()['local_pharma_database'] is False
        r=client.post('/api/data/parse',files={'file':('tiny.csv',b'drug,score\na,1\nb,2\n','text/csv')}); assert r.status_code==200 and r.json()['rows'][1]['drug']=='b'
        x=client.post('/api/data/export_xlsx',json={'headers':['drug','score'],'rows':[['a',1],['b',2]]}); assert x.status_code==200; wb=load_workbook(BytesIO(x.content),read_only=True); assert list(wb.active.values)==[('drug','score'),('a',1),('b',2)]

def test_title_and_biomedical_extract_without_browser_secret():
    with TestClient(app) as client:
        t=client.post('/api/title',json={'text':'EGFR inhibitors for lung cancer'}); assert t.status_code==200 and t.json()['title']
        b=client.post('/api/biomedical/extract',json={'text':'EGFR and TP53 were evaluated in lung cancer.'}); assert b.status_code==200 and 'EGFR' in b.json()['genes']
