"""Small typed guard falsifier; preserve actual all-action lists."""
from dataclasses import replace,asdict
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleSet,RuleSemanticAction,RuleGeometrySpec,RuleActionEffect,RuleSquareRef,RuleReplaceSelector,RuleStateGuard,RuleTypeRef,RuleSpatialSelector
from scripts.shared_contact_prefix import Profile
from scripts.nonpromotable_contact_prefix import NonpromotableContactPrefix
from scripts.full_contact_distances import qualify_target_free
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/contact_target_type_falsifier_20261005.json'
SOURCES=('scripts/audit_contact_target_type_falsifier.py','docs/research/CONTACT_TARGET_TYPE_FALSIFIER_PROTOCOL.md','scripts/nonpromotable_contact_prefix.py','scripts/shared_contact_prefix.py','scripts/full_contact_distances.py','generic_chess/rules/schema.py','generic_chess/core/semantic_executor.py','docs/research/data/contact_typed_geometry_valid_20261005.json')
def build(guarded):
    ref=lambda kind:RuleSquareRef(kind)
    rows=[[None]*3 for _ in range(3)]
    rows[1][0]=Piece(0,'K','K');rows[1][2]=Piece(1,'K','K')
    guard=RuleStateGuard('count','opponent',RuleTypeRef('explicit','V'),'current','no','board',RuleSpatialSelector('exact',refs=(ref('target'),)),comparison='eq',value=1,subject_ref=ref('target'))
    actions=[]
    for relation in ('empty','enemy'):
        effects=(RuleActionEffect('move',from_ref=ref('source'),to_ref=ref('target')),)
        if relation=='enemy':effects=(RuleActionEffect('remove',square_ref=ref('target'),piece_owner='opponent',disposition='remove_from_game'),)+effects
        actions.append(RuleSemanticAction('opaque_'+relation,('X',),RuleGeometrySpec('leap',offset=(-1,0)),relation,
          composition='replace_legacy',replace_selector=RuleReplaceSelector(('X',),'board',relation,geometry_kind='leap',replace_all_matching=True),
          state_guards=(guard,) if guarded and relation=='enemy' else (),effects=effects))
    types=(PieceType('X','X',(LeapAtom((-1,0)),)),PieceType('V','V',()),PieceType('W','W',()),PieceType('K','K',(),is_anchor=True))
    return RuleSet(board_size=3,piece_types=types,initial_position=tuple(tuple(row) for row in rows),
       drop_allowed={t:((False,)*9,)*2 for t in ('X','V','W')},semantic_actions=tuple(actions),capture_disposition='remove_from_game')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen target guard study')
    start=monotonic();r=dict(complete=False,rows=[],qualification=[],public_transitions=0,source_queries=0,enumerated=0,candidates=0,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec')
    try:
        for guarded in (False,True):
            c=compile_ruleset_for_execution(build(guarded));e=semantic_engine_for(c);initial=initial_state(c).position
            for owner in (0,1):
                check();admitted=False;error=None
                try:
                    kernel=NonpromotableContactPrefix(c,(Profile('X','X'),),owner=owner,checkpoint=check)
                    r['candidates']+=kernel.stats['geometry_candidates'];qualify_target_free(kernel);admitted=True
                except ValueError as err:error=str(err)
                r['qualification'].append(dict(guarded=guarded,owner=owner,admitted=admitted,error=error))
                if admitted==guarded:raise ValueError('qualification expectation failed')
                for target_type in ('V','W'):
                    s,d,b=(1,0,4) if owner==0 else (7,8,4)
                    board=list(initial.board);board[s]=Piece(owner,'X','X');board[d]=Piece(1-owner,target_type,target_type);board[b]=Piece(owner,'W','W')
                    p=replace(initial,board=tuple(board),side_to_move=owner)
                    actions=e.legal_actions(p,checkpoint=check);r['enumerated']+=len(actions)
                    if len(actions)>128 or r['enumerated']+r['candidates']>5000:raise ValueError('cap')
                    actual=any(a.source==s and a.target==d for a in actions)
                    r['rows'].append(dict(guarded=guarded,owner=owner,target_type=target_type,source=s,target=d,blocker=b,actual=actual,all_actions=[asdict(a) for a in actions]))
                    write_record(OUT,r)
                    if actual!=(not guarded or target_type=='V'):raise ValueError('membership mismatch')
        r['complete']=len(r['rows'])==8
    except Exception as err:r['error']=f'{type(err).__name__}: {err}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','source_sha256')}))
