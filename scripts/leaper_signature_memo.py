"""Exact public-action canonical signature memo, research-only pure Leaper consumer."""

import ast,copy,inspect,textwrap,json

from dataclasses import fields

from generic_chess.core.coordinates import Square

from contextlib import contextmanager

from generic_chess.core import search_runtime as runtime

from generic_chess.core.actions import SemanticBoardMove

BASE=runtime.SearchPathRuntime

COUNTERS={'runtimes':0,'hits':0,'misses':0,'fallbacks':0,'clears':0,'peak_entries':0}



def canonical(action):

    return json.dumps(runtime.action_to_dict(action),sort_keys=True,separators=(',',':'))



_ACTION_SCHEMA=(SemanticBoardMove.__dataclass_params__.frozen and Square.__dataclass_params__.frozen and {f.name for f in fields(SemanticBoardMove)}=={'pattern_id','geometry_id','actor_type_id','from_square','to_square','promotion_target_id'} and {f.name for f in fields(Square)}=={'file','rank'})

def admitted_action(action):

    return (_ACTION_SCHEMA and type(action) is SemanticBoardMove

            and all(type(getattr(action,k)) is str for k in ('pattern_id','geometry_id','actor_type_id'))

            and (action.promotion_target_id is None or type(action.promotion_target_id) is str)

            and all(type(q) is Square and type(q.file) is int and type(q.rank) is int for q in (action.from_square,action.to_square)))



def signature_for(owner,action):
    if not owner._signature_admitted:
        COUNTERS['fallbacks']+=1;return canonical(action)
    cache=owner._signature_cache;key=id(action);entry=cache.get(key)
    # A retained strong reference rules out id reuse; no dataclass equality
    # shortcut can alias bool/int public fields or distinct literal syntax.
    if entry is not None and entry[0] is action:
        COUNTERS['hits']+=1;return entry[1]
    if not admitted_action(action):
        COUNTERS['fallbacks']+=1;return canonical(action)
    COUNTERS['misses']+=1;value=canonical(action)
    if len(cache)>=4096:cache.clear();COUNTERS['clears']+=1
    cache[key]=(action,value)
    COUNTERS['peak_entries']=max(COUNTERS['peak_entries'],len(cache))
    return value

def derive():

    original=ast.parse(textwrap.dedent(inspect.getsource(BASE._push_impl)))

    tree=copy.deepcopy(original);old=[]

    class Rewrite(ast.NodeTransformer):

        def visit_Assign(self,node):

            self.generic_visit(node)

            if len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='signature':

                expected=ast.parse("json.dumps(action_to_dict(action), sort_keys=True, separators=(',', ':'))",mode='eval').body

                assert ast.dump(node.value)==ast.dump(expected),'canonical serializer source drift'

                old.append(copy.deepcopy(node.value))

                node.value=ast.Call(ast.Name('_exact_signature_memo',ast.Load()),[ast.Name('self',ast.Load()),ast.Name('action',ast.Load())],[])

            return node

    tree=Rewrite().visit(tree);assert len(old)==1

    inverse=copy.deepcopy(tree)

    class Restore(ast.NodeTransformer):

        def visit_Call(self,node):

            if isinstance(node.func,ast.Name) and node.func.id=='_exact_signature_memo':return copy.deepcopy(old[0])

            return self.generic_visit(node)

    inverse=Restore().visit(inverse);assert ast.dump(inverse)==ast.dump(original),'changed transaction outside serializer'

    namespace=dict(vars(runtime));namespace['_exact_signature_memo']=signature_for

    ast.fix_missing_locations(tree);exec(compile(tree,'<research-exact-signature-memo>','exec'),namespace)

    return namespace['_push_impl']



class SignatureRuntime(BASE):

    def __init__(self,*args,**kwargs):

        super().__init__(*args,**kwargs)

        self._signature_cache={}

        self._signature_admitted=runtime._plain_leaper_hash_patterns(self.compiled) is not None

        COUNTERS['runtimes']+=1

    _push_impl=derive()



@contextmanager

def installed():

    import generic_chess.ai.alphabeta.search as search

    original=search.SearchPathRuntime

    assert original is BASE,'another research runtime already installed'

    try:

        search.SearchPathRuntime=SignatureRuntime

        yield COUNTERS

    finally:search.SearchPathRuntime=original



def reset():

    for key in COUNTERS:COUNTERS[key]=0


