#!/usr/bin/env python3
"""Phase D: consumable shop items and faction reputation meters."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main import Game, Mission, Player

FACTIONS: dict[str, dict[str, str]] = {
    "brokers": {
        "label": "Darknet Brokers",
        "desc": "Contract fixers who move money and intel.",
    },
    "rivals": {
        "label": "Rival Syndicate",
        "desc": "acid_k's crew — chaos, leverage, and heat.",
    },
    "corps": {
        "label": "Corporate Security",
        "desc": "NovaDyne, Helix, and their blue-team hunters.",
    },
}

FACTION_PERKS: dict[str, list[tuple[int, str]]] = {
    "brokers": [
        (20, "Consumable shop prices -5%"),
        (50, "+5% payout on broker contracts"),
        (100, "Free random consumable every 5 broker contracts"),
    ],
    "rivals": [
        (20, "-10% trace chance on rival subnets"),
        (50, "Chaos mode rep requirement -50"),
        (100, "Rival-race NPC advances 25% slower"),
    ],
    "corps": [
        (20, "-5% trace chance on corporate subnets"),
        (50, "+20% rep from defense blocks"),
        (100, "Honey-net decoys won't trigger IDS"),
    ],
}

CONSUMABLES: dict[str, dict[str, Any]] = {
    "burner_ip": {
        "name": "Burner IP Kit",
        "desc": "Mask egress IP for 8 commands.",
        "cost": 120,
        "commands": 8,
    },
    "zero_day": {
        "name": "Zero-day Exploit",
        "desc": "Auto-crack current SSH target once.",
        "cost": 450,
    },
    "decoy_log": {
        "name": "Decoy Log Pack",
        "desc": "6 commands of full trace immunity.",
        "cost": 200,
        "commands": 6,
    },
    "miner_payload": {
        "name": "Miner Payload",
        "desc": "Deploy crypto miner on a cracked host (infect miner).",
        "cost": 140,
    },
    "ddos_payload": {
        "name": "DDoS Payload",
        "desc": "Flood a target host (infect ddos <IP>).",
        "cost": 220,
    },
}

BROKER_NAMES = frozenset({
    "ghost_broker", "cipher7", "nullbyte", "shade_runner", "packet_queen",
})

CORP_SUBNETS = frozenset({"10.0.0.0/24", "172.16.0.0/24"})
RIVAL_SUBNETS = frozenset({"203.0.113.0/24"})

STORY_FACTION_SHIFTS: dict[str, dict[str, int]] = {
    "ghost": {"brokers": 15, "corps": 5, "rivals": -10},
    "rivals": {"rivals": 15, "brokers": -5, "corps": -10},
    "solo": {"brokers": 3, "rivals": 3, "corps": 3},
}

BOARD_FACTION_SHIFTS: dict[str, dict[str, int]] = {
    "flex": {"brokers": 2},
    "rivals": {"rivals": 2},
    "intel": {"corps": 1},
    "lfg": {"brokers": 1},
}


class FactionRepManager:
    @staticmethod
    def _rep(game: Game, faction: str) -> int:
        return game.meta.faction_rep.get(faction, 0)

    @staticmethod
    def shift(game: Game, deltas: dict[str, int]) -> None:
        for faction, amount in deltas.items():
            if faction not in FACTIONS:
                continue
            cur = game.meta.faction_rep.get(faction, 0)
            game.meta.faction_rep[faction] = max(-20, min(150, cur + amount))
        FactionRepManager._check_thresholds(game)

    @staticmethod
    def _check_thresholds(game: Game) -> None:
        from main import success

        for faction, perks in FACTION_PERKS.items():
            rep = FactionRepManager._rep(game, faction)
            if rep >= 50:
                ach = {"brokers": "faction_broker", "rivals": "faction_rival", "corps": "faction_corp"}.get(faction)
                if ach:
                    game.achievements.unlock(ach)
            for threshold, label in perks:
                key = f"faction_{faction}_{threshold}"
                if rep >= threshold and key not in game.meta.faction_perks_unlocked:
                    game.meta.faction_perks_unlocked.add(key)
                    success(f"FACTION PERK [{FACTIONS[faction]['label']}]: {label}")

    @staticmethod
    def has_perk(game: Game, faction: str, threshold: int) -> bool:
        return FactionRepManager._rep(game, faction) >= threshold

    @staticmethod
    def on_story_choice(game: Game, choice_key: str) -> None:
        deltas = STORY_FACTION_SHIFTS.get(choice_key, {})
        if deltas:
            FactionRepManager.shift(game, deltas)

    @staticmethod
    def on_contract_complete(game: Game, mission: Mission) -> None:
        deltas: dict[str, int] = {"brokers": 0, "rivals": 0, "corps": 0}
        if mission.broker in BROKER_NAMES:
            deltas["brokers"] += 5
        server = game.network.get_server(mission.target_ip)
        subnet = server.subnet if server else ""
        if subnet in CORP_SUBNETS:
            deltas["corps"] -= 3
            deltas["rivals"] += 2
        elif subnet in RIVAL_SUBNETS or getattr(server, "chaos_only", False):
            deltas["rivals"] += 3
        FactionRepManager.shift(game, deltas)
        if FactionRepManager.has_perk(game, "brokers", 100) and mission.broker in BROKER_NAMES:
            game.meta.contracts_since_free_consumable += 1
            if game.meta.contracts_since_free_consumable >= 5:
                game.meta.contracts_since_free_consumable = 0
                key = random.choice(list(CONSUMABLES.keys()))
                ConsumableManager.add_to_inventory(game, key, 1)
                from main import success
                success(f"Broker perk: free {CONSUMABLES[key]['name']} added to inventory.")

    @staticmethod
    def on_board_post(game: Game, board: str) -> None:
        deltas = BOARD_FACTION_SHIFTS.get(board, {})
        if deltas:
            FactionRepManager.shift(game, deltas)

    @staticmethod
    def payout_mult(game: Game, mission: Mission) -> float:
        if mission.broker in BROKER_NAMES and FactionRepManager.has_perk(game, "brokers", 50):
            return 1.05
        return 1.0

    @staticmethod
    def consumable_discount(game: Game) -> float:
        if FactionRepManager.has_perk(game, "brokers", 20):
            return 0.95
        return 1.0

    @staticmethod
    def trace_reduction(game: Game, server) -> float:
        if not server:
            return 0.0
        subnet = getattr(server, "subnet", "")
        bonus = 0.0
        if subnet in RIVAL_SUBNETS and FactionRepManager.has_perk(game, "rivals", 20):
            bonus += 0.10
        if subnet in CORP_SUBNETS and FactionRepManager.has_perk(game, "corps", 20):
            bonus += 0.05
        return bonus

    @staticmethod
    def defense_rep_mult(game: Game) -> float:
        if FactionRepManager.has_perk(game, "corps", 50):
            return 1.2
        return 1.0

    @staticmethod
    def rival_race_slow_mult(game: Game) -> float:
        if FactionRepManager.has_perk(game, "rivals", 100):
            return 0.75
        return 1.0

    @staticmethod
    def chaos_rep_reduction(game: Game) -> int:
        if FactionRepManager.has_perk(game, "rivals", 50):
            return 50
        return 0

    @staticmethod
    def honey_net_immunity(game: Game) -> bool:
        return FactionRepManager.has_perk(game, "corps", 100)

    @staticmethod
    def status_lines(game: Game) -> list[str]:
        lines = ["  Faction standing (-20 to 150):"]
        for key, info in FACTIONS.items():
            rep = FactionRepManager._rep(game, key)
            bar_len = max(0, min(20, rep // 5))
            bar = "#" * bar_len + "." * (20 - bar_len)
            lines.append(f"    {info['label']:<22} [{bar}] {rep}")
            for threshold, label in FACTION_PERKS[key]:
                mark = "+" if rep >= threshold else "-"
                lines.append(f"      {mark} {threshold}: {label}")
        return lines


class ConsumableManager:
    @staticmethod
    def inventory_count(game: Game, key: str) -> int:
        return game.meta.inventory.get(key, 0)

    @staticmethod
    def add_to_inventory(game: Game, key: str, amount: int = 1) -> None:
        game.meta.inventory[key] = game.meta.inventory.get(key, 0) + amount

    @staticmethod
    def buy(game: Game, key: str) -> bool:
        from main import error, success

        spec = CONSUMABLES.get(key)
        if not spec:
            error(f"Unknown consumable '{key}'.")
            return False
        cost = int(spec["cost"] * FactionRepManager.consumable_discount(game))
        if not game.player.spend(cost, spec["name"]):
            return False
        if game.player._game_ref:
            from session_content import MasteryGrader
            MasteryGrader.on_shop_spend(game, cost)
        ConsumableManager.add_to_inventory(game, key, 1)
        success(f"Purchased {spec['name']} — use 'use {key}' when ready.")
        return True

    @staticmethod
    def _track_use(game: Game) -> None:
        if game.meta.consumables_used >= 10:
            game.achievements.unlock("consumable_user")

    @staticmethod
    def use(game: Game, key: str) -> bool:
        from main import Console, divider, error, success, teach

        spec = CONSUMABLES.get(key)
        if not spec:
            error(f"Unknown consumable '{key}'.")
            return False
        if ConsumableManager.inventory_count(game, key) < 1:
            error(f"No {spec['name']} in inventory. Buy with: buy {key}")
            return False

        if key == "burner_ip":
            game.meta.inventory[key] -= 1
            game.meta.consumables_used += 1
            game.meta.burner_commands_left = spec["commands"]
            game.meta.burner_mask_ip = f"198.18.{random.randint(1, 254)}.{random.randint(1, 254)}"
            divider("BURNER IP KIT")
            Console.out(f"  Egress masked as {game.meta.burner_mask_ip} for {spec['commands']} commands.")
            success("Burner active — victims log the fake IP.")
            teach("VPN still works; burner overrides the logged egress IP.")
            ConsumableManager._track_use(game)
            return True

        if key == "zero_day":
            s = game.remote_server() if hasattr(game, "remote_server") else None
            if not s or game.player.connected_port != 22:
                error("Connect to an SSH target (port 22) before using zero-day.")
                return False
            if s.cracked and game.player.has_remote_shell:
                error("Target already cracked.")
                return False
            game.meta.inventory[key] -= 1
            game.meta.consumables_used += 1
            s.cracked = True
            game.player.has_remote_shell = True
            divider("ZERO-DAY EXPLOIT")
            success(f"Instant shell on {s.hostname} — exploit burned.")
            game.player.session_cracked = True
            from retention import RetentionManager
            RetentionManager.on_crack(game, s.ip, s.security_level)
            from session_content import LateralManager
            LateralManager.on_crack(game, s.ip)
            teach("One-shot only. Logs still show activity unless you clean up.")
            ConsumableManager._track_use(game)
            return True

        if key == "decoy_log":
            game.meta.inventory[key] -= 1
            game.meta.consumables_used += 1
            game.meta.decoy_trace_immunity = spec["commands"]
            divider("DECOY LOG PACK")
            success(f"Trace immunity for {spec['commands']} commands.")
            teach("Disconnects won't trigger forensic traces; contracts count logs as clean.")
            ConsumableManager._track_use(game)
            return True

        error("Consumable not implemented.")
        return False

    @staticmethod
    def has_trace_immunity(game: Game) -> bool:
        return game.meta.decoy_trace_immunity > 0

    @staticmethod
    def logs_clean_enough(game: Game) -> bool:
        return game.meta.decoy_trace_immunity > 0

    @staticmethod
    def on_post_command(game: Game) -> None:
        if game.meta.burner_commands_left > 0:
            game.meta.burner_commands_left -= 1
            if game.meta.burner_commands_left <= 0:
                game.meta.burner_mask_ip = ""
        if game.meta.decoy_trace_immunity > 0:
            game.meta.decoy_trace_immunity -= 1

    @staticmethod
    def inventory_lines(game: Game) -> list[str]:
        lines = ["  Consumables:"]
        any_owned = False
        for key, spec in CONSUMABLES.items():
            count = ConsumableManager.inventory_count(game, key)
            if count:
                any_owned = True
            lines.append(f"    {key:<12} {spec['name']:<20} x{count}")
        if game.meta.burner_commands_left:
            lines.append(f"    (burner active: {game.meta.burner_commands_left} cmds → {game.meta.burner_mask_ip})")
        if game.meta.decoy_trace_immunity:
            lines.append(f"    (decoy immunity: {game.meta.decoy_trace_immunity} cmds)")
        if not any_owned and not game.meta.burner_commands_left and not game.meta.decoy_trace_immunity:
            lines.append("    none — buy burner_ip | zero_day | decoy_log at shop")
        return lines

    @staticmethod
    def shop_lines() -> list[str]:
        return [f"    {k:<12} {v['name']:<20} ${v['cost']}" for k, v in CONSUMABLES.items()]
