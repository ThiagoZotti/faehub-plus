"""Read-only warmed Flask route timings; excludes browser rendering and network."""
import statistics
import time
from unittest.mock import patch
import database
from app import app

def measure():
    original=database.sqlite3.connect
    for user,role,path in [('gilberto','admin','/usuarios'),('gilberto','admin','/configuracoes'),('aline','professor','/exercicios'),('thiago.zotti','aluno','/painel')]:
        client=app.test_client()
        with client.session_transaction() as s:s.update(username=user,role=role,aluno_id='23081',display_name=user)
        client.get(path)
        connections=[];times=[]
        def connect(*args,**kwargs):
            connections.append(1)
            return original(*args,**kwargs)
        with patch.object(database.sqlite3,'connect',side_effect=connect):
            for _ in range(20):
                start=time.perf_counter();response=client.get(path);times.append((time.perf_counter()-start)*1000)
                assert response.status_code==200,(path,response.status_code)
        print(f'{role:10} {path:16} median={statistics.median(times):.2f}ms connections/request={len(connections)/20:.1f}')

if __name__=='__main__':measure()
