"""Observed nonexact graph-rank/tree-height boundary, on actual S4 mate."""
from dataclasses import replace
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from scripts.generic_session_win_proof import verify_session_certificate
from results.dev_aux.task2199.semantic_graph import prove_graph,verify_graph
from results.dev_aux.task2200.controls import mate_rules,unroll
from results.dev_aux.task2219.diagnose import exact_height_tree

def test_valid_upper_rank_requires_exact_height_when_converted_to_tree():
 s=GameSession(compile_ruleset_for_execution(mate_rules()),initial_setup_key='quiet_mate')
 r=prove_graph(s,max_nodes=512,seconds=2.);cert=r.certificate;assert cert is not None
 upper=replace(cert,nodes=(replace(cert.nodes[0],rank=3),)+cert.nodes[1:])
 assert verify_graph(s,upper,seconds=2.)['verified']
 assert not verify_session_certificate(s,unroll(s,upper),seconds=2.)['verified']
 exact,gaps=exact_height_tree(s,upper);assert gaps and exact.tree.rank==1
 assert verify_session_certificate(s,exact,seconds=2.)['verified']
 assert exact.tree.edges[0][0]==cert.nodes[0].edges[0][0]
