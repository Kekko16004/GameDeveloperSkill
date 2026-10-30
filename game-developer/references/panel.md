# Panel: the owner's local view of the game

`scripts/panel.py` serves one page on 127.0.0.1 with five sections: Overview, Todo, Media, Performance, Launch. Standard library only, any game and any engine. Every value is read from the project on each request; a section with no data says so. The server binds no other address and does not accept another `Host`.

## What it reads

| Section | Source | How it is labelled |
|---|---|---|
| Tasks, Next, Done | `GAME_TASKS.md` rows, columns found by header name | `[/]` or `[~]` is running; an open row with a `docs/progress/` note is "inferred" |
| Needs you | `[WAIT-USER]` or a note saying the owner picks or decides | inferred from registry notes |
| Done times | changed time of the evidence or progress file | "file changed", never a completion time |
| Gates, Decisions, Engine gaps | `docs/gates`, `DECISIONI.md`, `engine_issues:` lines | as written in the file |
| Media | `screenshots`, `captures`, `docs/screens` | type guessed from file names, task inferred from progress notes |
| Performance | `GPU x ms / CPU y ms` in gates and progress notes, bench JSON in `docs`, target from `GDD.md` | source file and its time; a warning when the CPU figure sits on a display refresh |
| Launch | `launch/` and the installed `game-launch-strategist` skill | real state or "not started" |

## How the parent runs it

```sh
python scripts/panel.py --project PROJECT            # background; prints the URL, first free port from 8765 (or --port N)
python scripts/panel.py --project PROJECT --heartbeat        # touch .gds/panel-listening once, at every step
python scripts/panel.py --project PROJECT --heartbeat 600    # or every 30 s for 600 s, then exit: for long waits
python scripts/panel.py --project PROJECT --drain            # print the waiting commands, one JSON per line, and empty the queue
```

- **Listening.** The buttons work only while `.gds/panel-listening` is younger than 2 minutes. Without a heartbeat the panel is view-only and says so. A long wait with no heartbeat also shows view-only, so start a bounded `--heartbeat SECONDS` before one.
- **Drain at every step**, and before reporting to the owner.
- **Commands.** `{"id", "ts", "type": "answer", "task", "question", "text"}` is the owner's answer: record it in `DECISIONI.md` and act on it. `{"id", "ts", "type": "market_check"}` asks for the market check of `game-launch-strategist`, which writes only in `launch/`.
- **Nothing runs by itself.** The server never executes a command. It writes only `.gds/panel-commands.jsonl`, only while listening, and accepts only a question the registry currently asks or a market check that is actually available.
- Add `.gds/` to the game's `.gitignore`.
