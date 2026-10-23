"""Bind a saved repeat2 context to one actual original-mu full history."""
import json
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_explorer_truth import load
from scripts.leaper_design import state_sha
from scripts.research_record import record_value
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_from_dict
from scripts.leaper_cooperative_certificate import decode_position


class ContextBinder:
    def __init__(self,directory):
        self.inputs=load(directory/'inputs.json.gz');self.truth=load(directory/'truth.json.gz');self.adj=load(directory/'adjacent-pairs.json.gz');self.directory=directory;self.cache={}

    def family(self,familyid):
        if familyid not in self.cache:
            f=next(f for f in self.inputs['families']if f['family']==familyid)
            source=next(x for x in self.inputs['rows']if x['family']==familyid);c=admit(f,source);d=load(self.directory/f'domain{familyid}.json.gz')
            positions=[decode_position(z,c.initial_position)for z in d['positions']]
            ids=[]
            for pair in self.adj['pairs']:
                for field,key in(('left_family','left_id'),('right_family','right_id')):
                    if pair[field]==familyid:ids.extend(r[key]for r in pair['rows'])
            sources=sorted([r for r in self.truth['roots']if r['id']in set(ids)],key=lambda r:r['id'])
            self.cache[familyid]=(f,c,d,positions,sources)
        return self.cache[familyid]

    def bind(self,candidate):
        f,c,d,positions,sources=self.family(candidate['family']);target=candidate['vertex'];prior=set(candidate['prior_vertices']);length=6-candidate['h']
        if len(prior)!=len(candidate['prior_vertices'])or len(prior)!=length:raise ValueError('repeat2 nonterminal prefix must be injective')
        if any(type(i)is not int or not 0<=i<len(positions)for i in prior|{target}):raise ValueError('invalid context vertex')
        if positions[target].side_to_move!=0 or target in prior:raise ValueError('not an ongoing seat0 context')
        def find(i,path,seen):
            if len(path)==length:return path if i==target and seen==prior else None
            if i not in prior or i in seen:return None
            for k,j in enumerate(d['edges'][i]):
                result=find(j,path+[d['actions'][i][k]],seen|{i})
                if result is not None:return result
            return None
        for source in sources:
            if source['root_index']not in prior:continue
            path=find(source['root_index'],[],set())
            if path is None:continue
            s=GameSession.replay(c,deserialize_game_record(json.dumps(source['record'])))
            for a in path:s.submit(action_from_dict(a))
            if s.state.position!=positions[target]or s.state.ply_count!=length or s.result.status.value!='ongoing':raise ValueError('full source prefix mismatch')
            return s,dict(candidate,source_id=source['id'],source_record=source['record'],prefix=path,record=record_value(s.to_record()),state_sha=state_sha(s.state))
        raise ValueError('no actual source-mu full history matches context')
