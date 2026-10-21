"""Finite-roster opportunity diagnostic; no evaluator/default/game claims."""
from __future__ import annotations
from collections import Counter
from fractions import Fraction as F
from itertools import combinations
from math import comb
from pathlib import Path
import json
import sys
import time

ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tests'))
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, RayAtom, atom_targets
from generic_chess.ai.evaluation.mobility import analytic_mobility_at_density

ORTH = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIAG = ((1, 1), (1, -1), (-1, 1), (-1, -1))
KNIGHT = tuple((a*s, b*t) for a, b in ((1, 2), (2, 1)) for s in (-1, 1) for t in (-1, 1))
TEMPLATES = {
    'ortho_ray': tuple(RayAtom(x) for x in ORTH),
    'diag_ray': tuple(RayAtom(x) for x in DIAG),
    'leap21': tuple(LeapAtom(x) for x in KNIGHT),
    'step8': tuple(LeapAtom(x) for x in ORTH + DIAG),
    'ortho2': tuple(RayAtom(x, 2) for x in ORTH),
    'omni_ray': tuple(RayAtom(x) for x in ORTH + DIAG),
    'ortho_screen': tuple(RayAtom(x) for x in ORTH),
}
BOARDS = (3, 4, 5, 6, 8, 12)
PLAN = {
    'question': 'Can fixed rule-roster counts change opportunity ranks, not just scale?',
    'boards': BOARDS, 'templates': tuple(TEMPLATES),
    'rosters': 'all equal per-owner counts n=2..floor(area/2); own actor conditioned present',
    'A': 'iid remaining density d=(2n-1)/(area-1), enemy d/2, empty 1-d',
    'B': 'same iid occupancy d, enemy n/(area-1), friend (n-1)/(area-1)',
    'C': 'uniform fixed counts n-1 friend,n enemy,area-2n empty over remaining cells',
    'decision': 'Strict rank reversal means count law is a separate candidate axis; otherwise inspect ratio-only sensitivity. No product/default or utility claim.',
    'validation': 'A vs existing analytic mobility and semantic cannon; C vs independent full 3x3 occupancy enumeration',
    'scope': 'Uniform source, simple quiet/target capture and one-screen orthogonal cannon. Anchor safety, reachable-state law, promotion/drop/auxiliary effects and price calibration excluded explicitly; full generic target unchanged.',
}

def choose(n, k):
    return comb(n, k) if 0 <= k <= n else 0

def events(n, atoms, source):
    result = []
    for atom in atoms:
        targets = atom_targets(n, 0, Square(source % n, source // n), atom)
        path = []
        for target in targets:
            index = target.rank * n + target.file
            result.append((index, tuple(path) if isinstance(atom, RayAtom) else ()))
            path.append(index)
    assert len({t for t, _ in result}) == len(result)
    return result

def expectation(n, roster, histogram, screen=False):
    area=n*n; M=area-1; K=2*roster-1; Z=area-2*roster
    d=F(K,M); u=F(Z,M); ea=d/2; eb=F(roster,M)
    totals=[F(0), F(0), F(0)]
    for L, count in histogram.items():
        quiet=u**(L+1)
        independent = L*d*u**(L-1) if screen and L else F(0) if screen else u**L
        qfixed=F(choose(Z,L+1),choose(M,L+1))
        numerator=(K-1)*choose(Z,L-1) if screen and L else 0 if screen else choose(Z,L)
        cfixed=eb*F(numerator,choose(M-1,L))
        for j,v in enumerate((quiet+ea*independent, quiet+eb*independent, qfixed+cfixed)):
            totals[j] += count*v/area
    return tuple(totals)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'plan.json').write_bytes((json.dumps(PLAN,indent=2)+'\n').encode())
    start=time.perf_counter(); cases=[]; exact={}; max_iid_error=0.
    for n in BOARDS:
        hist={name:Counter(len(path) for source in range(n*n) for _,path in events(n,atoms,source)) for name,atoms in TEMPLATES.items()}
        for roster in range(2,n*n//2+1):
            values={name:expectation(n,roster,hist[name],name=='ortho_screen') for name in TEMPLATES}
            for name,atoms in TEMPLATES.items():
                if name!='ortho_screen':
                    observed=analytic_mobility_at_density(n,atoms,(2*roster-1)/(n*n-1))
                    max_iid_error=max(max_iid_error,abs(observed-float(values[name][0])))
            exact[n,roster]=values
            cases.append({'board':n,'per_owner_count':roster,'density':(2*roster-1)/(n*n-1),'opportunity':{k:dict(zip(('A','B','C'),map(float,v))) for k,v in values.items()}})
    assert max_iid_error<1e-10,max_iid_error
    from rule_semantics_ir_fixtures import cannon_ruleset
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.ai.evaluation.semantic import semantic_opportunity
    from generic_chess.ai.evaluation.config import EvaluationConfig
    cannon=compile_ruleset_for_execution(cannon_ruleset()); n=cannon.board_shape.width
    hist=Counter(len(p) for s in range(n*n) for _,p in events(n,TEMPLATES['ortho_screen'],s))
    cannon_errors=[]
    for density in (0.,.125,.25,.5):
        row=semantic_opportunity(cannon,'C',EvaluationConfig(density_points=(density,),density_weights=(1.,)))
        expected=sum(count*((1-density)**(L+1)+(density/2*L*density*(1-density)**(L-1) if L else 0)) for L,count in hist.items())/(n*n)
        cannon_errors.append(abs(row['raw']-expected))
    assert max(cannon_errors)<1e-10,cannon_errors
    # Independent enumeration assigns friend/enemy subsets, then directly tests events.
    enumeration=[]
    for roster in (2,3,4):
        totals={k:0 for k in TEMPLATES}; configs=0
        for source in range(9):
            other=tuple(i for i in range(9) if i!=source)
            ev={k:events(3,a,source) for k,a in TEMPLATES.items()}
            for friends in combinations(other,roster-1):
                remaining=tuple(i for i in other if i not in friends)
                for enemy_tuple in combinations(remaining,roster):
                    enemies=set(enemy_tuple); occupied=set(friends)|enemies;configs+=1
                    for name,es in ev.items():
                        for target,path in es:
                            inside=sum(i in occupied for i in path)
                            totals[name] += int((target not in occupied and inside==0) or (target in enemies and inside==(1 if name=='ortho_screen' else 0)))
        for name,total in totals.items():
            assert F(total,configs)==exact[3,roster][name][2],(roster,name,F(total,configs),exact[3,roster][name][2])
        enumeration.append({'roster':roster,'source_configurations':configs,'templates':len(totals)})
    reversals={k:[] for k in ('AB','AC','BC')}; ties={k:0 for k in reversals}; max_ratio={k:(0.,None) for k in ('screen/ray','ray/leap21')}
    for (n,roster),values in exact.items():
        for pair,indices in (('AB',(0,1)),('AC',(0,2)),('BC',(1,2))):
            a,b=indices
            for x,y in combinations(TEMPLATES,2):
                da=values[x][a]-values[y][a];db=values[x][b]-values[y][b]
                if da*db<0:reversals[pair].append({'board':n,'roster':roster,'types':[x,y],'first':[float(values[x][a]),float(values[y][a])],'second':[float(values[x][b]),float(values[y][b])]})
                elif (da==0)!=(db==0):ties[pair]+=1
        for label,x,y in (('screen/ray','ortho_screen','ortho_ray'),('ray/leap21','ortho_ray','leap21')):
            ra=values[x][0]/values[y][0];rc=values[x][2]/values[y][2];change=abs(float(rc/ra)-1)
            if change>max_ratio[label][0]:max_ratio[label]=(change,{'board':n,'roster':roster,'A_ratio':float(ra),'C_ratio':float(rc)})
    result={'plan':PLAN,'cases':cases,'validation':{'iid_max_error':max_iid_error,'cannon_errors':cannon_errors,'fixed_count_enumeration':enumeration},'strict_reversal_counts':{k:len(v) for k,v in reversals.items()},'strict_reversals':reversals,'tie_status_changes':ties,'max_ratio_change':max_ratio,'elapsed_seconds':time.perf_counter()-start}
    (OUT/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps({k:v for k,v in result.items() if k not in ('cases','strict_reversals','plan')},indent=2))
    print('First reversals:',json.dumps({k:v[:3] for k,v in reversals.items()},indent=2))

if __name__=='__main__':main()
