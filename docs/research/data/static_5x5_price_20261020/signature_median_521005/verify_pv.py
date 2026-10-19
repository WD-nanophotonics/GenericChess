import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT))
from generic_chess.core.actions import action_from_dict
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from scripts.research_record import write_record
HERE=Path(__file__).resolve().parent
DATA=HERE.parent
def opening_action(item):
    if "kind" in item:return action_from_dict(item)
    d=dict(item);to=d.pop("to_square");d["to"]=[to["file"],to["rank"]]
    if "from_square" in d:
        fr=d.pop("from_square");d["from"]=[fr["file"],fr["rank"]];d["kind"]="semantic_board"
    elif "base_type_id" in d:d["kind"]="semantic_drop"
    else:raise ValueError("UNRECOGNIZED_SAVED_ACTION")
    return action_from_dict(d)
def main():
    rule=deserialize_ruleset((DATA/"rule-521005.json").read_text(encoding="utf-8"))
    c=compile_legacy_ruleset_for_semantic_execution(rule)
    manifest=json.loads((DATA/"roots.json").read_text(encoding="utf-8"))
    roots={r["root_id"]:r for r in manifest if r["rule_id"]=="521005"}
    result=json.loads((HERE/"result.json").read_text(encoding="utf-8"))
    rows=[]
    for r in result["roots"]:
        checks={}
        for arm, data in r["arms"].items():
            s=GameSession(c)
            for a in roots[r["root_id"]]["opening"]:s.submit(opening_action(a))
            assert s.result.status.value=="ongoing"
            for i,a in enumerate(data["pv"]):
                parsed=action_from_dict(a)
                legal=s.legal_actions()
                assert parsed in legal,(r["root_id"],arm,i,a)
                s.submit(parsed)
                assert s.result.status.value=="ongoing" or i==len(data["pv"])-1
            checks[arm]={"pv_plies":len(data["pv"]),"legal_actions_all":True,"ending_status":s.result.status.value,"final_ply":s.state.ply_count}
        assert checks["current_all_type_median"]["pv_plies"]==checks["counterfactual_one_per_exact_signature"]["pv_plies"]
        rows.append({"root_id":r["root_id"],"arms":checks,"same_pv":r["pv_equal"]})
    out={"schema":"primary-signature-median-choice-pv-replay-v1","result_sha256":hashlib.sha256((HERE/"result.json").read_bytes()).hexdigest(),"roots":[{"root_id":r["root_id"],"root_sha256":roots[r["root_id"]]["root_sha256"]} for r in result["roots"]],"checks":rows,"status":"COMPLETE"}
    write_record(HERE/"pv_replay.json",out)
    print(json.dumps(out,separators=(",",":")))
if __name__=="__main__":main()