# TerminalHacker

Educational cybersecurity training simulator with a desktop GUI and terminal hacking gameplay.

## Run (GUI — default)

```bash
python3 main.py
```

Opens a simulated desktop with icons for:

- **Terminal** — scan, connect, crack, VPN, privesc, and more
- **Mail** — NPC messages from trainers, brokers, and rivals (unread badge)
- **Job Board** — contract missions (unlocks after tutorial)
- **Black Market** — buy CPU, firewall, and cracking tools
- **Training** — step-by-step tutorial curriculum
- **System Status** — wallet, hardware, network info

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
3. Graduate to **career mode** for live missions and upgrades

Type `lesson` in the terminal for your current objective.
