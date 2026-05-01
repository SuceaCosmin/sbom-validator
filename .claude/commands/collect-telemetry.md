Run the telemetry collection script for a release cycle and report what was collected.

Arguments: $ARGUMENTS

Parse the arguments to extract:
- The release version (e.g. `v0.7.0`) — required
- One or more `--session UUID` values, OR a `--date-from`/`--date-to` range
- An optional `--out PATH` override

Then run:
```
python scripts/collect_telemetry.py --release <version> [<remaining args>]
```

If the user provided no session or date filter, ask them to provide one before running.

After the script completes, report:
1. Which sessions were collected (session ID prefix, date, branch, turn count)
2. Total agent dispatches found
3. The output file path
4. A note: "The token analyst can now read `docs/releases/telemetry-<release>.json` using the Read tool to produce a fully measured token report."

If the script fails (usage.db not found, no matching sessions), report the error clearly and suggest the correct flags.
