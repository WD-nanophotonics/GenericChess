"""Serial actual reference-to-caller transport, never historical runner/corpus."""
import json,importlib.util,hashlib
from pathlib import Path
from unittest.mock import patch
from scripts import audit_f23v_minimal_analytic_evaluator as first
from scripts import audit_f23v_minimal_analytic_evaluator_r1 as second
spec=importlib.util.spec_from_file_location('claim58fixture','tests/development/test_exact_generic_reference_declarations.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)

class Sink:
    def __init__(self):self.rows=[]
    def put(self,value):self.rows.append(value)

def run():
    rows=[]
    for module in [first,second]:
        for outcome in ['WIN','RESTART']:
            session=fixture.counterexample(outcome);before=session.to_record();sink=Sink()
            # Injection is limited to compiled/state INPUT routing; actual v3
            # solver and actual historical worker return-field mapping execute.
            with patch.object(module,'_compile',lambda *args:session.compiled),patch.object(module,'_state',lambda *args,**kwargs:session.state):
                candidate={'group':'ACTUAL_CLAIM_FIXTURE','board_size':4,'rows':[],'side_to_move':1}
                if module is first:module._worker(sink,'ACTUAL_CLAIM_FIXTURE',candidate,'v3')
                else:module._worker(sink,candidate,'v3')
            assert len(sink.rows)==1
            result=sink.rows[0]
            assert result['strong'] is False and result['root_value'] is None
            assert result['optimal_actions']==result['action_values']==[] and result['proof_depth']==0
            assert result['stats']['states_expanded']==0 and result['unresolved_reason']=='REFERENCE_SOLVE_UNRESOLVED:declarations'
            assert session.to_record()==before
            terminal=session.declare('claim')
            rows.append(dict(caller=module.__name__,source_sha256=hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(),actual_claim=outcome,actual_winner=terminal.winner,transport=result))
    output=dict(rows=rows,scope='two direct historical worker field mappers called serially with actual public WIN/RESTART fixtures; input builders substituted explicitly, no multiprocessing/isolation, no corpus/labels/holdouts read or regenerated',new_native_go=0,training_games=0,caller_code_changes=0)
    Path(__file__).with_name('result.json').write_text(json.dumps(output,indent=2),encoding='utf-8');print(json.dumps(output,indent=2))
if __name__=='__main__':run()
