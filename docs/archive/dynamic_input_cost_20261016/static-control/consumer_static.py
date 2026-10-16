from pathlib import Path
import sys,json,runpy,time
B=Path(sys.argv[1]).resolve();sys.argv=['consumer.py',str(B)];code=(B/'consumer.py').read_text().replace("'consumer-result.json'","'consumer-base-for-static.json'");ns={'__name__':'base_receipt_consumer','__file__':str(B/'consumer.py')};exec(compile(code,str(B/'consumer.py'),'exec'),ns)
for row in json.loads((B/'static-results.json').read_bytes())['rows']:
 ss,nr=ns['root'](row['seed'],True);ns['query'](ss,nr,row['result'])
counts=dict(ns['counts']);assert counts['query_receipts']==392;x=dict(complete=True,counts=counts,scope='Actualsourcebound360base+32latestaticreceiptconsumer, nosearch/game/fit/oldclockauthentication; samefinalsourceaspreviousrebuild.');(B/'static-consumer-result.json').write_bytes((json.dumps(x,indent=2)+'\n').encode());print('LATE_STATIC_REPLAY',counts)
