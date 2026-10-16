from tools.local_agent.slack_transport import _payload_matches

def test_observed_numbered_prose_only():
 assert _payload_matches('TYPE=AGENT_REQUEST\n1. Same body\n2. Next body','TYPE=AGENT_REQUEST\n1) Same body\n2) Next body')
 assert not _payload_matches('TYPE=AGENT_REQUEST\n1. Changed body','TYPE=AGENT_REQUEST\n1) Same body')
 assert not _payload_matches('TYPE=DIFFERENT\n1. Same body','TYPE=AGENT_REQUEST\n1) Same body')

def test_snapshot_and_fenced_code_not_rewritten():
 assert not _payload_matches('```python\n1. Same body\n```','```python\n1) Same body\n```')
 assert not _payload_matches('LOCAL_CODE_SNAPSHOT=x\n1. Same body','LOCAL_CODE_SNAPSHOT=x\n1) Same body')
 assert not _payload_matches(' 1. Same body',' 1) Same body')
