"""Hash-bound source review; no compilation or mature execution."""
import hashlib,json
from pathlib import Path
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent
SOURCE=ROOT/".local_agent/material-selfplay"
PIN="9f778da667f6e07dae1e85d3e2ea204fc6dee94d"
base=json.loads((ROOT/"results/dev_aux/task091/declaration.json").read_bytes())
files={};checks=[]
for name,digest in base["files"].items():
    actual=hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()
    if actual!=digest:raise AssertionError(name+" changed")
    files[name]=dict(sha256=actual,origin="existing Task091 copied entry")
    checks.append("unchanged "+name)
def locate(name,fragments):
    path=SOURCE/"source-review"/name
    text=path.read_text();rows=text.splitlines()
    locations={}
    for fragment in fragments:
        matches=[i+1 for i,line in enumerate(rows) if fragment in line]
        if not matches:raise AssertionError(name+":"+fragment)
        locations[fragment]=matches;checks.append("source witness "+name+":"+fragment)
    files[name]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        url="https://raw.githubusercontent.com/fairy-stockfish/Fairy-Stockfish/"+PIN+"/src/"+name,locations=locations)
locate("parser.cpp",['"pieceValueMg"','"pieceValueEg"',"toupper(token)","v->pieceValue[phase][idx]"])
locate("ucioption.cpp",["variants.parse<false>(path)",'Options["UCI_Variant"].set_combo','std::find(comboValues.begin()','return *this;',"PSQT::init(v)"])
locate("variant.cpp",["Unable to open file","parser.get_errors().empty()","Variant template"])
locate("search.cpp",["eval = evaluate(pos)","pos.non_pawn_material(us)","futility_margin(depth","Threads.nodes_searched() >= (uint64_t)Limits.nodes"])
checks.append("patched pure leaf uses EvalPieceValue")
assert "material += EvalPieceValue[MG][pt]" in (SOURCE/"evaluate.cpp").read_text()
assert "EvalPieceValue[MG][pc] = EvalPieceValue[MG][~pc] = mg_value(score)" in (SOURCE/"psqt.cpp").read_text()
assert "PieceValue[MG][pos.piece_on(to_sq(m))]" in (SOURCE/"movepick.cpp").read_text()
assert "int swap = PieceValue[MG][piece_on(to)] - threshold" in (SOURCE/"position.cpp").read_text()
checks.append("retained fixed SEE/order/nonpawn priors")
result=dict(complete=True,source_pin=PIN,checks=checks,check_count=len(checks),files=files,
            findings=[
              "Variant file parse failure or an invalid combo can leave the old variant selected; readyok is not parameter acceptance. Task109 now requires the auxiliary variant acknowledgement and checks five independent type leaf values on each fresh game process.",
              "The parser accepts case-insensitive piece letters for MG/EG entries. Positive explicit PNBRQ values override inherited price transformations before EvalPieceValue assignment; K remains excluded.",
              "The patched leaf returns material before the classical/NNUE route. Capture ordering, SEE, nonpawn-material bookkeeping and pruning thresholds still retain mature engine priors. This is conditional material-leaf learning, not unaided rule-only value discovery.",
              "go nodes1024 is a configured bound observed by engine polling. Record final reported nodes separately, including missing information/overshoot; do not claim exactly1024 visited nodes.",
            ],mature_games_executed=0,
            limitations="Static source witnesses are not execution or source-to-binary attestation. Text retrieval required a shell fallback after web fetch cache misses; exact downloaded-byte hashes are retained. No builds, blocked launches, security changes or product modifications.")
(OUT/"result.json").write_bytes((json.dumps(result,indent=2)+"\n").encode());print(json.dumps({k:v for k,v in result.items() if k!="files"}))
