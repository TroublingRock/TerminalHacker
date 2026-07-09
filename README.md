# TerminalHacker

Educational cybersecurity training simulator with a desktop GUI and terminal hacking gameplay.

## Play instantly (no terminal)

| Platform | What to double-click |
|----------|----------------------|
| **Windows** | `Play Security Simulator.vbs` |
| **macOS** | `Play Security Simulator.command` |
| **Linux** | `play-security-simulator.sh` or `Security Simulator.desktop` |

Download the repo (**Code → Download ZIP**), unzip, and open the launcher for your OS.  
Python 3.10+ is checked automatically; Windows can install it for you via winget.

See **[INSTALL.md](INSTALL.md)** for step-by-step setup and troubleshooting.

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
2. Complete 12 lessons teaching networking, logs, VPN, routing, privesc, and defense
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

### Consumables & factions (v1.7)

| System | Command |
|--------|---------|
| Consumables | `buy burner_ip\|zero_day\|decoy_log` then `use <item>` |
| Faction rep | `factions` — brokers / rivals / corps meters with perks at 20/50/100 |

Consumables: **Burner IP Kit** (mask egress for 8 commands), **Zero-day Exploit** (instant SSH crack), **Decoy Log Pack** (6 commands trace immunity), **Miner Payload** / **DDoS Payload** (botnet deploy).

### Botnet payloads (v2.0)

| System | Command |
|--------|---------|
| Deploy miner | `buy miner_payload` → crack host → `infect miner [IP]` |
| Deploy DDoS | `buy ddos_payload` → `infect ddos <IP>` |
| Status / cash out | `botnet` / `botnet collect` |
| GUI | Dock **Botnet** (⊛) window |

Miners accrue modest passive income each command (collect with `botnet collect`). DDoS softens target firewall and slows rival-race NPCs for ~14 commands. Loud nets spike **subnet heat**; rivals may **purge nodes** or **siphon** uncollected revenue. Saboteur spec gets +15% miner income.

Faction rep shifts from story choices, contract targets, and board posts. Perks include shop discounts, payout bonuses, trace reduction, and broker freebies.

### Longevity expansion (v1.8)

| System | What's new |
|--------|------------|
| Tool puzzles | `phish_gate`, `tunnel_jump`, `plant_backdoor`, `forge_cover` — require phish/tunnel/plant/forge |
| New hosts | 8 hosts on 10.50/60/70/80 subnets — weeklies & hourlies use expanded 16-entry pools |
| Story arcs | 3-part exclusive contracts per story branch (ghost / rivals / solo) |
| Operations | All 9 ops reachable — fixed `op-vault` → `op-treasury`, added shadow/research/hr |
| Season cycles | Monthly season reset with carryover bonus; **12 heists**, **4 active/month**, 3-month cycle |
| Rival counters | Procedural hosts may spawn rival-race counter-missions |
| Endless depth | 6 floor archetypes, 5 modifiers, boss floors every 5 with tool puzzles |
| Heist retention | First-clear consumable + faction rep; branch mastery bonuses; repeat payout scales down |

### LLM dynamic content (v1.9, optional)

Use **OpenAI** (recommended) or **Groq** for flavor text **and** structured generation.

```bash
mkdir -p ~/.terminalhacker
cp llm.json.example ~/.terminalhacker/llm.json
# Edit api_key in the file, OR export env vars:
export OPENAI_API_KEY="sk-..."
# optional: export LLM_PROVIDER=openai
```

Never commit API keys to the repo — `llm.json` and `.env` are gitignored.

| Command | Purpose |
|---------|---------|
| `llm` | Status — provider, flavor + struct call budgets, caches |
| `llm test` | Verify flavor + JSON struct layer |
| `llm on` / `llm off` | Toggle without deleting config |
| `world` | Current weekly world event (heat, bounties, trace) |
| `board post lfg <title> \| <body>` | Spawns a real LLM-authored contract from your post |

**Call budgets (per calendar day):** 12 flavor calls + 3 structural calls. All responses cached in your save.

**Structural hooks:** AI picks mission type + dual puzzle combo + modifiers + loot path (validated against real hosts/files); LFG board posts become contracts; weekly world-event JSON tweaks heat, bounties, and rival aggression.

Defaults: OpenAI `gpt-4o-mini`, 12 flavor + 3 struct calls/session. Falls back to templates if no key.

### Balance notes (v1.2)

- Trace chance tuned for fair early career (~28% base)
- Rival attacks eased during first career session; breach losses capped when wallet is low
- Graduation grants at least **$750** career funds
- Season, streak, and prep rewards paced for ~30 days of daily play

Type `lesson` or `help` in the terminal anytime.
