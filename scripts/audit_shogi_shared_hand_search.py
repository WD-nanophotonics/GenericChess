"""Exact all-box certificate before one actual changed-hand integration run."""
import hashlib,json,sys
from pathlib import Path
from fractions import Fraction as F
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.shogi_static_inventory import StaticInventory,SCALE
from scripts.shogi_exact_contact_family import exact_board_means
from scripts.material_leaf_choice import inventory_features
from scripts.research_state_replay import read_game_state
from scripts.audit_shogi_promotion_use import selections
OLD=ROOT/'scripts/audit_shogi_static_search.py';DATA=ROOT/'docs/research/data';OUT=DATA/'shogi_shared_hand_search_20261006.json'
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('one changed-hand point only')
    prior=json.loads((DATA/'shogi_static_search_20261006.json').read_text());assert prior['complete'] and prior['searches'][0]['statistics']['runtime_pushes']==49
    for p,pin in prior['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin
    tree=json.loads((DATA/'shogi_promotion_use_20261005.json').read_text());means=exact_board_means('geometric_half');weights={t:means[t]/means['TR'] for t in ('P','TP','R')};e=StaticInventory(weights)
    features={key:{reply:inventory_features(read_game_state(leaf['state']).position,{'K'}) for reply,leaf in branch['leaves'].items()} for key,branch in tree['branches'].items()}
    certificate=selections(features,{t:F(value,SCALE) for t,value in e.weights.items()});assert certificate['tie_set']==tree['selections_before_goal']['geometric_half']['tie_set']
    code=OLD.read_text().replace('shogi_static_search_20261006.json','shogi_shared_hand_search_20261006.json')
    code=code.replace('from scripts.shogi_static_inventory import StaticInventory,SCALE','from scripts.shogi_static_inventory import SCALE\nfrom scripts.shogi_shared_hand_inventory import SharedHandInventory as StaticInventory')
    code=code.replace("SOURCES=('scripts/audit_shogi_static_search.py',", "SOURCES=('scripts/audit_shogi_shared_hand_search.py','scripts/shogi_shared_hand_inventory.py','docs/research/SHOGI_SHARED_HAND_SEARCH_PROTOCOL.md','docs/research/data/shogi_static_search_20261006.json','scripts/audit_shogi_promotion_use.py','scripts/audit_shogi_static_search.py',")
    code=code.replace('(ROOT/SOURCES[3])',"(ROOT/'docs/research/data/shogi_promotion_use_20261005.json')")
    code=code.replace("(('geometric_half',weights),('unit',{t:F(1) for t in weights}))", "(('geometric_half',weights),)").replace("len(r['searches'])==2", "len(r['searches'])==1")
    code=code.replace('monotonic()-start>=15','monotonic()-start+0.125>=15').replace("r['runtime_pushes']>=128","r['runtime_pushes']+49>=128").replace("r['candidates']+r['returned_actions']>5000","r['candidates']+r['returned_actions']+1130>5000")
    code=code.replace('push=SearchPathRuntime.push;', "r['shared_hand_box_certificate']=certificate;r['held_point']={'P':0,'R':0};push=SearchPathRuntime.push;")
    code=code.replace("r['seconds']=monotonic()-start;", "r['baseline_pushes']=49;r['paired_pushes']=49+r['runtime_pushes'];r['conservative_enumeration_charge']=1130+r['candidates']+r['returned_actions'];r['cumulative_seconds']=monotonic()-start+0.125;r['seconds']=monotonic()-start;")
    exec(compile(code,str(OLD),'exec'),{'__name__':'__main__','__file__':str(OLD),'certificate':certificate})
