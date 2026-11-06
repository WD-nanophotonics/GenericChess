"""Research-only shared pure-Leaper value network; Core owns game semantics.

No piece-name embedding table, board-size-specific weights or new move engine.
Geometry below is read from Core's compiled leap tables. The network observes
current repetition and the remaining clock, not the entire repetition map;
full replay records remain attached to samples, so this is a partial observer.
"""
from dataclasses import dataclass
import math
import torch
from torch import nn
from scripts.leaper_neural_rules import admitted,rule_signature


@dataclass
class Graph:
    offsets: torch.Tensor
    offset_types: torch.Tensor
    type_features: torch.Tensor
    node_types: torch.Tensor
    nodes: torch.Tensor
    edges: torch.Tensor
    relations: torch.Tensor
    globals: torch.Tensor


def graph_from_session(rules,session):
    admitted(rules)
    c=session.compiled;pos=session.state.position;w,h=rules.board_shape.width,rules.board_shape.height
    ids={p.type_id:i for i,p in enumerate(rules.piece_types)};tokens=[];token_types=[];type_features=[]
    for ti,p in enumerate(rules.piece_types):
        moves=rule_signature(p)[1]
        type_features.append([float(p.is_anchor),len(moves)/32])
        for dx,dy in moves:
            tokens.append([dx/18,dy/18,dx/(w-1),dy/(h-1),1.,1.])
            token_types.append(ti)
    node_types=[];nodes=[];edges=[];relations=[]
    stm=pos.side_to_move
    legal={(a.from_square.rank*w+a.from_square.file,a.to_square.rank*w+a.to_square.file) for a in session.legal_actions()}
    for src,piece in enumerate(pos.board):
        x,y=src%w,src//w
        node_types.append(-1 if piece is None else ids[piece.current_type_id])
        nodes.append([x/18,y/18,x/(w-1),y/(h-1),w/19,h/19,float(piece is not None),
                      0. if piece is None else (1. if piece.owner==stm else -1.),
                      0. if piece is None else float(rules.piece_types[ids[piece.current_type_id]].is_anchor),1. if stm==0 else -1.])
        # Local geometric relations include empty squares. They are not moves.
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
            if 0<=x+dx<w and 0<=y+dy<h:
                edges.append((src,(y+dy)*w+x+dx));relations.append([dx/18,dy/18,dx/(w-1),dy/(h-1),0.,1.,0.,0.,0.,0.])
        if piece is None:continue
        # Reuse immutable compiled geometry. Occupancy relations are features,
        # not a replacement for Core's legality/royal/terminal decisions.
        targets={sq.rank*w+sq.file for atom in c.leap_targets[piece.current_type_id][piece.owner][src] for sq in atom}
        for dst in sorted(targets):
            q=pos.board[dst];dx,dy=dst%w-x,dst//w-y
            edges.append((src,dst));relations.append([dx/18,dy/18,dx/(w-1),dy/(h-1),1.,0.,float(q is None),float(q is not None and q.owner!=piece.owner),float(q is not None and q.owner==piece.owner),float((src,dst) in legal)])
    counts=[sum(p is not None and p.owner==owner for p in pos.board) for owner in (stm,1-stm)]
    rep=dict(session.state.repetition_counts).get(session.state.history[-1].position_key,1)
    global_features=[w/19,h/19,w*h/361,counts[0]/16,counts[1]/16,
                     session.state.ply_count/max(1,rules.max_ply),
                     (rules.max_ply-session.state.ply_count)/128,rep/max(1,rules.repetition_limit),float(rules.stalemate_result=='loss')]
    return Graph(torch.tensor(tokens,dtype=torch.float32).reshape(-1,6),torch.tensor(token_types,dtype=torch.long),
        torch.tensor(type_features,dtype=torch.float32),torch.tensor(node_types,dtype=torch.long),torch.tensor(nodes,dtype=torch.float32),
        torch.tensor(edges,dtype=torch.long).reshape(-1,2).T.contiguous(),torch.tensor(relations,dtype=torch.float32).reshape(-1,10),torch.tensor(global_features,dtype=torch.float32))


def batch_graphs(graphs):
    offsets=[];offset_types=[];types=[];node_types=[];nodes=[];edges=[];relations=[];node_graph=[];globals_=[];nt=nnodes=0
    for gi,g in enumerate(graphs):
        offsets.append(g.offsets);offset_types.append(g.offset_types+nt);types.append(g.type_features)
        node_types.append(torch.where(g.node_types>=0,g.node_types+nt,g.node_types));nodes.append(g.nodes)
        edges.append(g.edges+nnodes);relations.append(g.relations);node_graph.append(torch.full((len(g.nodes),),gi,dtype=torch.long));globals_.append(g.globals)
        nt+=len(g.type_features);nnodes+=len(g.nodes)
    return dict(offsets=torch.cat(offsets),offset_types=torch.cat(offset_types),types=torch.cat(types),node_types=torch.cat(node_types),nodes=torch.cat(nodes),
                edges=torch.cat(edges,dim=1),relations=torch.cat(relations),node_graph=torch.cat(node_graph),globals=torch.stack(globals_))


class LeaperValueNet(nn.Module):
    """Deep Sets structural encoder +2 shared relation rounds + W/D/L head."""
    def __init__(self,hidden=24,rounds=2):
        super().__init__();self.hidden=hidden
        self.phi=nn.Sequential(nn.Linear(6,hidden),nn.SiLU(),nn.Linear(hidden,hidden))
        self.rho=nn.Sequential(nn.Linear(hidden+2,hidden),nn.SiLU())
        self.node_encoder=nn.Sequential(nn.Linear(hidden+10,hidden),nn.SiLU())
        self.messages=nn.ModuleList(nn.Sequential(nn.Linear(hidden*2+10,hidden),nn.SiLU(),nn.Linear(hidden,hidden)) for _ in range(rounds))
        self.updates=nn.ModuleList(nn.Sequential(nn.Linear(hidden*2+1,hidden),nn.SiLU(),nn.Linear(hidden,hidden)) for _ in range(rounds))
        self.value_head=nn.Sequential(nn.Linear(hidden+9,hidden),nn.SiLU(),nn.Linear(hidden,3))

    def forward(self,b):
        pooled=b['offsets'].new_zeros((len(b['types']),self.hidden))
        pooled.index_add_(0,b['offset_types'],self.phi(b['offsets']))
        embeddings=self.rho(torch.cat((pooled,b['types']),dim=1))
        occupied=(b['node_types']>=0).to(b['nodes'].dtype).unsqueeze(1)
        rules=embeddings[b['node_types'].clamp_min(0)]*occupied
        h=self.node_encoder(torch.cat((rules,b['nodes']),dim=1));src,dst=b['edges']
        degree=torch.bincount(dst,minlength=len(h)).to(h.dtype).unsqueeze(1)
        for message,update in zip(self.messages,self.updates):
            msg=message(torch.cat((h[src],h[dst],b['relations']),dim=1));agg=torch.zeros_like(h);agg.index_add_(0,dst,msg)
            h=h+update(torch.cat((h,agg/degree.clamp_min(1),torch.log1p(degree)),dim=1))
        ngraphs=len(b['globals']);out=h.new_zeros((ngraphs,self.hidden));out.index_add_(0,b['node_graph'],h)
        count=torch.bincount(b['node_graph'],minlength=ngraphs).to(h.dtype).unsqueeze(1)
        return self.value_head(torch.cat((out/count,b['globals']),dim=1))

    @torch.no_grad()
    def probabilities(self,rules,session):
        result=session.result
        if result.status.value not in ('ongoing','no_contest'):
            label=1 if result.winner is None else 2 if result.winner==session.state.position.side_to_move else 0
            return torch.nn.functional.one_hot(torch.tensor(label),3).float()
        return self(batch_graphs([graph_from_session(rules,session)])).softmax(-1)[0]


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.rules.compiler import compile_ruleset
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import deserialize_game_record
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True);p.add_argument('--input',required=True);a=p.parse_args()
    raw=json.loads(Path(a.input).read_text(encoding='utf-8'));rules=ruleset_from_dict(raw['rules']);c=compile_ruleset(rules)
    session=GameSession.replay(c,deserialize_game_record(json.dumps(raw['record'])))
    checkpoint=torch.load(a.checkpoint,map_location='cpu',weights_only=True)
    model=LeaperValueNet(checkpoint['hidden'],checkpoint['rounds']);model.load_state_dict(checkpoint['state_dict']);model.eval()
    prob=model.probabilities(rules,session)
    print(json.dumps(dict(probability_LDW=prob.tolist(),bounded_value=float(10000*(prob[2]-prob[0])),Core_status=session.result.status.value,
        limitation='class-weighted softmax estimates are uncalibrated, not exactWDL; full history is retained byCore, network observes only clock/current repetition')))
