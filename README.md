# TerminalHacker

Educational cybersecurity training simulator with a desktop GUI and terminal hacking gameplay.

## Run (GUI — default)

```bash
python3 main.py
```

Opens a simulated desktop with icons for:

- **Terminal** — scan, connect, crack, VPN, privesc, and more
- **Mail** — NPC messages from trainers, brokers, and rivals (unread badge)
- **Job Board** — contracts, daily challenges, weekly bounties
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
3. Graduate to **career mode** for live missions, reputation, and upgrades

### Month-long retention (career)

Designed for **~30 days of daily play**:

| System | What it does |
|--------|----------------|
| **Login streak** | Cash + season XP every day; big bonuses at days 7, 14, 21, 30 (`streak`) |
| **30-tier season** | Earn XP from dailies, contracts, bounties; unlock rewards through the month (`season`) |
| **31 daily challenges** | Unique rotating objective each day (`daily`) |
| **Weekly bounties** | High-value contract resets each Monday |
| **3-day operations** | Multi-part story missions; next phase unlocks tomorrow (`operation`) |
| **9 operation arcs** | ~27 days of scripted multi-day content across the month |
| **Weekly story mail** | Broker + rival narrative each Monday; recap with `intel` |
| **Mission archetypes** | Exfil, ghost runs, root heists, clean sweeps — not the same job every time |

Progress saves to `~/.terminalhacker/save.json` (`save` / `load`).

Type `lesson` in the terminal for your current objective.
