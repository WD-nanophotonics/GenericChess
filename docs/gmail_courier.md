# Gmail courier setup

1. In Google Cloud, enable the Gmail API and create a **Desktop app** OAuth client.
2. Save its downloaded JSON as `%LOCALAPPDATA%\\GenericChessBridge\\oauth-client.json`.
3. From this worktree's installed environment run `gc-bridge auth`; approve the
   browser prompt for `icywoods.1@gmail.com`.
4. Run `gc-bridge ensure` and `gc-bridge sync`. Runtime state lives in `.bridge/`.

`gc-bridge install-autostart` creates the per-user Windows Task Scheduler task
`GenericChess Gmail Bridge`; `gc-bridge uninstall-autostart` removes it. Attachments
are stored as data only and are never executed.
