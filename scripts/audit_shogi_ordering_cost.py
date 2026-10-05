"""One new ordering intervention; frozen no-ordering control reused."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OLD=ROOT/'scripts/audit_shogi_static_search.py';DATA=ROOT/'docs/research/data';OUT=DATA/'shogi_ordering_cost_20261006.json'
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('one ordering intervention only')
    old=json.loads((DATA/'shogi_static_search_20261006.json').read_text());assert old['complete']
    baseline=old['searches'][0];assert baseline['law']=='geometric_half' and baseline['statistics']['runtime_pushes']==49
    for p,pin in old['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin
    code=OLD.read_text().replace('shogi_static_search_20261006.json','shogi_ordering_cost_20261006.json')
    code=code.replace('from scripts.shogi_static_inventory import StaticInventory,SCALE','from scripts.shogi_static_inventory import SCALE\nfrom scripts.shogi_ordering_inventory import OrderingInventory as StaticInventory')
    code=code.replace("SOURCES=('scripts/audit_shogi_static_search.py',", "SOURCES=('scripts/audit_shogi_ordering_cost.py','scripts/shogi_ordering_inventory.py','docs/research/SHOGI_ORDERING_COST_PROTOCOL.md','docs/research/data/shogi_static_search_20261006.json','scripts/audit_shogi_static_search.py',")
    code=code.replace("(('geometric_half',weights),('unit',{t:F(1) for t in weights}))", "(('geometric_half',weights),)").replace('use_ordering=False','use_ordering=True').replace("len(r['searches'])==2", "len(r['searches'])==1")
    code=code.replace('monotonic()-start>=15','monotonic()-start+0.125>=15').replace("r['runtime_pushes']>=128","r['runtime_pushes']+49>=128").replace("r['candidates']+r['returned_actions']>5000","r['candidates']+r['returned_actions']+1130>5000")
    code=code.replace("r['seconds']=monotonic()-start;", "r['baseline_pushes']=49;r['paired_pushes']=49+r['runtime_pushes'];r['conservative_enumeration_charge']=1130+r['candidates']+r['returned_actions'];r['cumulative_seconds']=monotonic()-start+0.125;r['seconds']=monotonic()-start;")
    exec(compile(code,str(OLD),'exec'),{'__name__':'__main__','__file__':str(OLD)})
