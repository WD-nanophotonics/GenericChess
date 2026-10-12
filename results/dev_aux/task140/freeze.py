"""Predeclare matchedsamebinaryalignmentlearning; no resultadaptiveextension."""
import json,hashlib,sys,importlib.util,math
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task140';O.mkdir(exist_ok=True)
s=importlib.util.spec_from_file_location('score140',R/'results/dev_aux/task104/short_game.py');G=importlib.util.module_from_spec(s);s.loader.exec_module(G)
if (O/'declaration.json').exists():raise FileExistsError('frozen')
fixtures={}
for phase in ('train','heldout'):
 for i in range(192 if phase=='train' else 8):
  seed=(1007000 if phase=='train' else 1009000)+i
  try:
   moves=G.opening(seed,plies=24);terminal=False;termination=None
  except ValueError:
   import random,chess
   b=chess.Board();rng=random.Random(seed);moves=[]
   for _ in range(24):
    if b.is_game_over(claim_draw=False):break
    m=rng.choice(sorted(b.legal_moves,key=lambda m:m.uci()));b.push(m);moves.append(m.uci())
   terminal=b.is_game_over(claim_draw=False);assert terminal;termination=b.outcome(claim_draw=False).termination.name
  fixtures[str(seed)]=dict(seed=seed,moves=moves,terminal=terminal,termination=termination,phase=phase)
qualified=json.loads((R/'results/dev_aux/task139/result.json').read_bytes());assert qualified['complete'] and len(qualified['rows'])==64
decl=dict(task_id='140',question='Does synchronizingcandidatePNBRQsearchtables causallychange shortobjective learning/heldout/human-referencebehavior under matchedsamebinary conditions?',new_premise='Task132sourceidentifiedinheritedstandardprices; Task139samebinary0vs1actualacks320leafreadbacks64searches17pairedactionschange. No inference from shallowregret. Directtablecontrolledlearning nowjustified.',start_seeds=[203,204,205],alignment_arms=[0,1],seed_alignment_order=[[203,0],[203,1],[204,1],[204,0],[205,0],[205,1]],updates=24,sweeps=6,coordinates=['N','B','R','Q'],steps=[math.log(64)/2**(i+1) for i in range(6)],weight_bounds=[52,3328],P=208,K=0,arms_per_update=3,training_openings_per_update=8,colors=[True,False],training_slots=6912,heldout_slots=192,total_slots=7104,opening_plies=24,postopening_cap=16,train_opening_seeds=[1007000,1007191],train_random_seeds=[1107000,1107191],heldout_opening_seeds=list(range(1009000,1009008)),heldout_random_seeds=list(range(1109000,1109008)),selection='OriginalTask108strictincumbentties coordinatecurrent/+/- ; sameTask131domainstep; nohumanvalues inupdates',reward='OriginalTask104 terminal±100 plusboundedmatespeed orcutoffunit-count/15',terminalinput='Preflightall200fixedroots; exclude terminalinput identicalacrossallarms/colors/starts/alignments withNone result and0 selectioncontribution; noresampling or enginegame.',terminal_input_seeds=[k for k,v in fixtures.items() if v['terminal']],reuse='onefreshownprocessperalignment/profile48gameblock, immutableprofile;5leafprobes+exactMG/EGtableack+ucinewgamepergame; fullinitialorthodoxhistory1024nodes1thread16MiB',binary_sha256=qualified['binary_sha256'],qualification_result_sha256=hashlib.sha256((R/'results/dev_aux/task139/result.json').read_bytes()).hexdigest(),deadline_seconds=1800,cost='7104slot matchedbatch estimated12-20minutes fromactual0.12-0.17s/game;1800sinclusivefuse. Completecounts nottimeclaim, serialoneengine. Noaddedworker/fee or expected>1hprojectrun.',freeze='ALL6endpoints frozen and endpoints.json writtenbeforeANYheldout; noheldoutfeedback',human_reference=dict(P=1,N=3,B=3,R=5,Q=9),human_reference_source='https://www.chess.com/terms/chess-piece-value',reference_metric='meanabsolute ln((actualprice/P)/reference) NBRQ; allinitial/finalvalues independentlydescriptiveonly; no fitting/selection/extension',scope='Freshstart/game seeds withinmethoddesignedfromexposedearlierfailures; conditionalmatureenginepriorsstillremain, notexpertfree discovery/universalvalues. Samebinary+leaf+candidateconditions isolatesjointsearch-table family; notSEE-only.',decision='Consistent3startreferencecontraction pluspairedheldoutbenefit wouldsupportscopedquicklearning; feedbackbenefitwithoutreferencecontraction isproxygain. Dispersed/negativeends limitthischeaproute andhelpcost/difficultyassessment. Noautomaticrerun/defaultpromotion.')
(O/'fixtures.json').write_text(json.dumps(fixtures,indent=2),encoding='utf-8');decl['fixtures_sha256']=hashlib.sha256((O/'fixtures.json').read_bytes()).hexdigest()
(O/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8');print(json.dumps(dict(frozen=True,total_slots=decl['total_slots'],terminal_inputs=decl['terminal_input_seeds'],expected_minutes='12-20',fuse=1800)))
