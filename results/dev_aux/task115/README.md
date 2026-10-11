# Separate16ply mature pilot

Run only with an already permitted, actually qualified Fairy material entry:

```powershell
.venv/Scripts/python.exe results/dev_aux/task115/pilot16.py --binary <qualified-entry> --qualification <actual-probe-json> --output results/dev_aux/<fresh-run>
```

The entry rejects failed qualification before transport. Existing4551 binary is not retried.
Four games only; cap16, total pilot120s, six random opening plies, paired profiles/colors/seeds.
No automatic training. Report parameter effect, first action divergence, reward components and cost.
This new predeclared pilot does not modify Task10964ply/480-stage or qualify Yane USI.

`validate.py` uses finite mock transport and saved non-mature trajectories. It never launches a binary.
Its CLI missing qualification output is synthetic, not a new actual runtime failure.
See declaration.json and the segment12 report for exact conditions, limits and source provenance.