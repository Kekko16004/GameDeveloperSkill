---
description: Open the local web panel of the game (tasks, media, performance, launch) and listen for its buttons.
---

Call Skill tool `game-developer` FIRST.

Follow [references/panel.md](../references/panel.md): start `scripts/panel.py --project PROJECT` in the background, give the owner the printed URL, keep the heartbeat alive and drain the queue at every step. A command from the queue is a request to read, never something to execute blindly.
