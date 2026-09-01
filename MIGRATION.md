# Windows two-machine handoff

GenericChess and ChatCourier use GitHub as the only durable progress and
ownership authority. Only one machine may own the workflow at a time. There is
no timer, daemon, shared browser profile, or copied runtime directory.

## First setup on a target machine

Clone the product repository as `GenericChess`, create its sibling sandbox
worktree from `origin/sandbox`, and clone ChatCourier as sibling
`GmailCourier` from its `origin/sandbox` branch:

```powershell
git clone https://github.com/WD-nanophotonics/GenericChess.git GenericChess
git -C GenericChess fetch origin master sandbox workflow-state
git -C GenericChess worktree add -b sandbox ..\GenericChess-sandbox origin/sandbox
git clone --branch sandbox https://github.com/WD-nanophotonics/agent-relay-read-wake.git GmailCourier
py -3.12 -m venv GmailCourier\.venv
GmailCourier\.venv\Scripts\python.exe -m pip install -e GmailCourier
py -3.12 -m venv GenericChess-sandbox\.venv
GenericChess-sandbox\.venv\Scripts\python.exe -m pip install -e "GenericChess-sandbox[dev]"
```

Sign in once to ChatGPT in the Courier-owned profile. Obtain the existing Chat
URL from the user and register it with the documented two-step ChatCourier
registration. The URL and profile are local-only.

Then configure and claim the released workflow:

```powershell
GenericChess-sandbox\generic-chess-flow.cmd machine-setup --host-id standby
GenericChess-sandbox\generic-chess-flow.cmd handoff-claim --host-id standby
GenericChess-sandbox\generic-chess-flow.cmd work
```

Start the target Codex task with Luna High and a durable `/goal`. The restored
session prints the exact next action; for a `SUBMIT_CLOSEOUT` capsule it points
to the locally reconstructed closeout file.

## Release from the active machine

Wait for the worker task to be idle and release only after both worktrees and
Courier are synchronized. For an implemented work order, preserve its closeout:

```powershell
generic-chess-flow.cmd handoff-release --to standby --closeout-file <report.md>
generic-chess-flow.cmd handoff-status
```

After the release push, all mutating flow commands on the source machine fail
until a later released generation is claimed back. Never force-push
`workflow-state`. Old `.generic_chess_flow`, `.courier_outbox`, `.venv`, cache,
binary, benchmark, process-lock, browser-profile, and thread-ID state is not
portable and must not be copied.
