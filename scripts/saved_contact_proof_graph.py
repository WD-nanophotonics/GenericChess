"""One explicit partial cached public proof graph; holes are epistemic frontiers."""
from fractions import Fraction as F
from types import SimpleNamespace
from scripts.research_state_replay import read_game_state
from scripts.public_goal_intervals import PublicGame
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset

class SavedContactProofGraph:
    def __init__(self, original, continuation, depth2, method):
        if method not in ('contact','unit','zero'):raise ValueError('declared method required')
        self.game=PublicGame(compile_ruleset_for_execution(build_western_chess_ruleset()))
        self.states={():read_game_state(original['root'])}
        self.edges={};self.full_actions={():tuple(original['all_root_actions'])}
        def edge(parent,action,encoded):
            node=parent+(action,);state=read_game_state(encoded)
            if node in self.states and self.states[node]!=state:raise ValueError('conflicting saved edge')
            self.states[node]=state;self.edges[parent,action]=node;return node
        for key,value in original['children'].items():edge((),key,value)
        contact=original['selections_before_labels']['contact']['selected']
        parent=(contact,);self.full_actions[parent]=tuple(original['candidate_all_replies'])
        first=original['candidate_replies'][0]
        child=edge(parent,first['enemy_action'],first['enemy_child'])
        self.full_actions[child]=tuple(first['all_own_replies'])
        mate=continuation['candidate_mate'];edge(child,mate['action'],mate['state'])
        for key,branch in continuation['baseline_counterbranches'].items():
            parent=(key,);self.full_actions[parent]=tuple(branch['all_enemy_replies'])
            child=edge(parent,branch['enemy_action'],branch['enemy_child'])
            self.full_actions[child]=tuple(branch['all_own_replies'])
            for row in branch['own_rows']:edge(child,row['action'],row['state'])
        rook=depth2['rook_capture'];parent=(rook['parent'],)
        self.full_actions[parent]=tuple(rook['all_enemy_replies'])
        edge(parent,rook['all_enemy_replies'][0],rook['state'])
        zero=depth2['positive_depth2']['zero'];parent=(zero,)
        self.full_actions[parent]=tuple(depth2['zero_all_replies'])
        for row in depth2['zero_rows']:edge(parent,row['action'],row['state'])
        for node,state in self.states.items():
            terminal=self.game.terminal(state)
            if terminal.is_terminal and node in self.full_actions:raise ValueError('terminal expansion in saved graph')
        picks=original['selections_before_labels']
        if method=='contact':order=[contact]+sorted(k for k in self.full_actions[()] if k!=contact)
        elif method=='unit':
            scores={k:F(v) for k,v in picks['unit']['scores'].items()}
            order=sorted(self.full_actions[()],key=lambda k:(-scores[k],k))
        else:order=sorted(self.full_actions[()])
        self.root_order=tuple(order)

    def terminal(self,node):
        if node not in self.states:
            return SimpleNamespace(is_terminal=True,unresolved=True,status='missing_successor',winner=None)
        t=self.game.terminal(self.states[node])
        if t.is_terminal:return t
        if node not in self.full_actions:
            return SimpleNamespace(is_terminal=True,unresolved=True,status='missing_expansion',winner=None)
        return t

    def owner(self,node):return self.states[node].position.side_to_move
    def actions(self,node,checkpoint):
        for action in self.root_order if node==() else sorted(self.full_actions[node]):
            checkpoint();yield action
    def successor(self,node,action):
        if action not in self.full_actions[node]:raise ValueError('not a saved complete legal identity')
        return self.edges.get((node,action),node+(action,))
    def is_materialization(self,action):return False
