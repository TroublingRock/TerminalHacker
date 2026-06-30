# TerminalHacker

Educational cybersecurity training simulator with a desktop GUI and terminal hacking gameplay.

## Run (GUI — default)

```bash
python3 main.py
```

Opens a simulated desktop with icons for:

- **Terminal** — scan, connect, crack, VPN, privesc, and more
- **Mail** — NPC messages from trainers, brokers, and rivals (unread badge)
- **Job Board** — contract missions and daily challenges (unlocks after tutorial)
- **Black Market** — buy CPU, firewall, and cracking tools
- **Training** — step-by-step tutorial curriculum
- **Achievements** — badges and today's daily challenge
- **System Status** — wallet, rank, hardware, save/load

Features window open animations and sound effects (click, mail, alerts).

### Linux GUI dependency

```bash
sudo apt install python3-tk   # Debian/Ubuntu
```

## Run (CLI only)

```bash
python3 main.py --cli
```

## Gameplay

1. Start in **tutorial mode** with a $500 training budget (career money is protected)
2. Complete 13 lessons teaching networking, logs, VPN, routing, privesc, and defense
3. Graduate to **career mode** for live missions, reputation, and upgrades

### Career progression

- **Reputation & ranks** — earn rep from hacks and contracts; rank up to unlock new subnet routes (`rank` command)
- **Companies & story** — scan targets show company names and lore; hosts span NovaDyne, Helix Capital, and chaos darknet nodes
- **Procedural contracts** — complete missions to receive generated contracts (`contracts` command or Job Board button)
- **Chaos mode** — endgame high-risk targets after 750 rep + max-tier gear (`chaos` command)
- **Daily challenges** — rotating objectives like zero-trace disconnects or no-VPN cracks (`daily` command)
- **Achievements** — track milestones (`achievements` command)
- **Blue-team defense** — toggle `defend on` to earn rep blocking rival attacks while running offense
- **Save/load** — progress persists to `~/.terminalhacker/save.json` (`save` / `load` or Status window buttons)

Type `lesson` in the terminal for your current objective.
