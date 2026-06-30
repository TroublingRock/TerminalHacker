# TerminalHacker

Educational cybersecurity training simulator with a desktop GUI and terminal hacking gameplay.

## Run (GUI — default)

```bash
python3 main.py
```

Resumes from `~/.terminalhacker/save.json` automatically if present.

Opens a simulated desktop with icons for:

- **Terminal** — scan, connect, crack, VPN, privesc, and more
- **Mail** — NPC messages from trainers, brokers, and rivals (unread badge)
- **Job Board** — contracts, daily challenges, weekly bounties, phase prep
- **Black Market** — buy CPU, firewall, and cracking tools
- **Training** — step-by-step tutorial curriculum
- **Achievements** — badges, streak, and season progress
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
3. Graduate to **career mode** (~$750+ starting wallet) for live missions and progression

### Career systems

| System | Command |
|--------|---------|
| Daily challenge | `daily` |
| Login streak | `streak` |
| 30-tier season | `season` |
| Multi-day operations | `operation` |
| Same-day prep (between op phases) | `bridge` |
| Weekly story recap | `intel` |
| Rival dossier | `rivals` |
| Reputation / ranks | `rank` |
| Achievements | `achievements` |
| Procedural contracts | `contracts` |
| Lateral movement chains | `chains` / `chains start <id>` |
| Hourly flash bounties | `hourly` |
| Mastery grades (S/A/B/C) | `grades` |
| Blue-team defense | `defend on` |
| Chaos endgame | `chaos` |
| Save / load | `save` / `load` |

Progress **auto-saves** every few commands, on milestones, and when you quit.

### Session depth (v1.3)

- **Lateral chains** — multi-hop pivot missions (`chains`) with intel files unlocking next targets
- **Mastery grades** — S/A/B/C ratings on contract completion affect payout and rep
- **Hourly flash events** — rotating 2–3x bounty contracts that expire each real-world hour

### Meta systems (v1.4)

| System | Command |
|--------|---------|
| Roguelike endless mode | `endless` / `endless start` |
| Branching story choices | `story` / `story choose <id>` |
| Darknet social boards | `board` / `board post` / `board upvote` |

### Gameplay variety (v1.5)

| Feature | How it works |
|---------|----------------|
| Per-host puzzles | Probe twice, `curl` HTTP intel, spearphish files, port 2222, honeypot decoys |
| New contract types | `social`, `timing` (command window), `pivot` (multi-host) |
| Procedural hosts | Unique companies, paths like `/data/lake/...`, random puzzles |

### Depth systems (v1.6)

| System | Command |
|--------|---------|
| Contract modifiers | Shown on contracts as `[MODS: ...]` |
| Tools | `phish`, `tunnel`, `plant`, `forge` |
| Subnet heat / rivals | `heat` |
| Specialization | `spec pick ghost\|broker\|saboteur\|architect` |
| Weekly heist arc | `heist` / `heist choose <branch>` |

Modifiers: air-gapped, honey-net, split-tunnel, deadline, no-shop, rival-race.

### Balance notes (v1.2)

- Trace chance tuned for fair early career (~28% base)
- Rival attacks eased during first career session; breach losses capped when wallet is low
- Graduation grants at least **$750** career funds
- Season, streak, and prep rewards paced for ~30 days of daily play

Type `lesson` or `help` in the terminal anytime.
