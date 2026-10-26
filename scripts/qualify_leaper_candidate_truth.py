"""Small explicit-input truth handoff; reads data, never chooses a candidate."""
from __future__ import annotations
import argparse,gzip,hashlib,json
from pathlib import Path
from scripts.leaper_truth_compatibility import bind_context,digest,qualify


class PublishedTruth:
    def __init__(self, directory):
        directory=Path(directory)
        def load(name):return json.loads(gzip.decompress((directory/name).read_bytes()))
        self.inputs=load("inputs.json.gz");self.truth=load("truth.json.gz")
        if digest(self.inputs)!=self.truth["source_digest"]:
            raise ValueError("published truth/input source binding differs")
        self.families={f["fingerprint"]:f for f in self.inputs["families"] if f.get("rule")}
        self.rows={r["id"]:r for r in self.truth["roots"]}
        self.input_rows={r["state_sha256"]:r for r in self.inputs["rows"]}
        if (len(self.rows)!=len(self.truth["roots"]) or len(self.input_rows)!=len(self.inputs["rows"])
                or set(self.rows)!=set(self.input_rows)):
            raise ValueError("duplicate/missing source root")
        self.hashes={name:hashlib.sha256((directory/name).read_bytes()).hexdigest()
                     for name in ("inputs.json.gz","truth.json.gz")}
        self.compiled={}

    def check(self,candidate):
        result=dict(id=candidate.get("id"),sources=self.hashes,
                    compatibility="UNKNOWN",qualification="NOT_CHECKED",coverage=None)
        missing=[k for k in ("rule","record") if not isinstance(candidate.get(k),dict)]
        if missing:
            return dict(result,reason="MISSING_FULL_CONTEXT",missing=missing)
        try:
            target=bind_context(candidate["rule"],candidate["record"])
        except (ValueError,TypeError,KeyError) as exc:
            return dict(result,reason="INVALID_OR_UNSUPPORTED_CONTEXT",detail=str(exc))
        result["target_context"]=target.identity
        fingerprint=target.identity["ruleset_fingerprint"]
        if fingerprint not in self.families:
            return dict(result,compatibility="INCOMPATIBLE",reason="FULL_RULE_NOT_IN_SOURCE",
                        qualification="LITERAL_TARGET_REPLAY_ONLY")
        key=target.identity["state_sha256"]
        if key not in self.rows:
            return dict(result,reason="NO_MATCHING_COMPLETE_HISTORY_TRUTH",
                        qualification="LITERAL_TARGET_REPLAY_ONLY")
        source_row=self.rows[key];input_row=self.input_rows[key];family=self.families[fingerprint]
        if source_row["fingerprint"]!=fingerprint or source_row["record"]!=input_row["full_record"]:
            raise ValueError("corrupt source row binding")
        source=bind_context(family["rule"],source_row["record"],compiled=target.session.compiled)
        if source.identity["state_sha256"]!=key or digest(input_row["full_state"])!=key:
            raise ValueError("source state annotation differs from literal replay")
        checked=qualify(target,source,source_row["action_bounds"],source_row["wdl_bounds"],value_seat=0)
        result.update(compatibility=checked["compatibility"]["status"],coverage=checked["coverage"],
                      qualification="LITERAL_CONTEXT_AND_SOURCE_BINDING;WDL_SOURCE_CLAIM",
                      reason=("EXACT_CONSERVATIVE_CONTEXT_MATCH" if checked["compatibility"]["status"]=="COMPATIBLE"
                              else "CONSERVATIVE_RECORD_OR_SESSION_MISMATCH"),source_root_id=key,
                      differences=checked["compatibility"]["differences"])
        if "selected_action" in candidate and checked["coverage"] is not None:
            chosen=[r for r in checked["coverage"]["rows"] if r["action"]==candidate["selected_action"]]
            result["selected_action"]=(chosen[0] if len(chosen)==1 else
                                       dict(classification="UNKNOWN",reason="ACTION_NOT_IN_LITERAL_FRONTIER"))
        return result


def main():
    p=argparse.ArgumentParser();p.add_argument("--candidates",type=Path,required=True)
    p.add_argument("--truth-directory",type=Path,default=Path("docs/research/data/leaper_h6_initial_truth_20261023"))
    p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    candidates=json.loads(a.candidates.read_bytes());source=PublishedTruth(a.truth_directory)
    if not isinstance(candidates,list):raise ValueError("candidates must be an explicit list")
    result=dict(format="source-bound-truth-handoff-v1",rows=[source.check(c) for c in candidates],
                input_sha256=hashlib.sha256(a.candidates.read_bytes()).hexdigest(),
                scope="Provided inputs only; no generated candidates/new solver/Player/game. Source claims remain distinct from local proof verification.")
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":main()
