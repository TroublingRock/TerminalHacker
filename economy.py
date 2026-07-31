#!/usr/bin/env python3
"""Contract payouts, progression scaling, broker fees, and economy tuning."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Game, Mission

# Low-security hosts pay poorly; high-security scales up sharply.
SECURITY_PAYOUT: dict[int, float] = {
    1: 0.42,
    2: 0.62,
    3: 0.90,
    4: 1.18,
    5: 1.42,
    6: 1.72,
    7: 2.05,
}

REP_TIER_THRESHOLDS: tuple[int, ...] = (0, 150, 400, 750, 1200)

BROKER_FEE_RATE = 0.08
BROKER_FEE_MIN = 8

DAILY_CASH_MULT = 0.72
SEASON_CASH_MULT = 0.65

# Type bonuses on top of procedural base (before security/progression mult at payout).
TYPE_CASH_BONUS: dict[str, int] = {
    "ghost": 70,
    "root_heist": 110,
    "clean_sweep": 50,
}

TYPE_REP_BONUS: dict[str, int] = {
    "root_heist": 18,
}


def rep_tier(rep: int) -> int:
    tier = 0
    for idx, threshold in enumerate(REP_TIER_THRESHOLDS):
        if rep >= threshold:
            tier = idx
    return tier


def progression_mult(rep: int, sec: int) -> float:
    """Higher rep raises pay on hard targets; easy lab boxes stay cheap."""
    tier = rep_tier(rep)
    mult = 0.80 + tier * 0.13
    if sec <= 2:
        return min(mult, 0.86)
    if sec >= 5:
        mult += 0.08
    return mult


def procedural_security(rep: int, spawn_index: int) -> int:
    """Scale procedural host difficulty with player reputation."""
    floor = 1 + min(5, rep_tier(rep) + 1)
    bump = min(2, spawn_index // 5)
    sec = floor + bump
    if random.random() < 0.22:
        sec += 1
    return max(1, min(7, sec))


class EconomyManager:
    @staticmethod
    def target_security(game: Game, mission: Mission) -> int:
        server = game.network.get_server(mission.target_ip)
        if server:
            return server.security_level
        return 3

    @staticmethod
    def payout_multiplier(game: Game, mission: Mission) -> float:
        sec = EconomyManager.target_security(game, mission)
        sec_m = SECURITY_PAYOUT.get(sec, 1.0)
        prog_m = progression_mult(game.player.reputation, sec)
        return sec_m * prog_m

    @staticmethod
    def broker_cut(gross: int) -> int:
        if gross <= 0:
            return 0
        return max(BROKER_FEE_MIN, int(gross * BROKER_FEE_RATE))

    @staticmethod
    def apply_broker_fee(game: Game, gross: int, broker: str) -> tuple[int, int]:
        """Return (net_payout, fee). Tutorial/endless brokers exempt."""
        if gross <= 0 or broker in ("training_officer", "system"):
            return gross, 0
        fee = EconomyManager.broker_cut(gross)
        return gross - fee, fee

    @staticmethod
    def classic_base(sec: int) -> int:
        return 110 + sec * sec * 32 + random.randint(0, 55)

    @staticmethod
    def classic_rep(sec: int) -> int:
        return 18 + sec * 9

    @staticmethod
    def build_classic_reward(sec: int, mtype: str) -> tuple[int, int]:
        reward = EconomyManager.classic_base(sec) + TYPE_CASH_BONUS.get(mtype, 0)
        rep = EconomyManager.classic_rep(sec) + TYPE_REP_BONUS.get(mtype, 0)
        return reward, rep

    @staticmethod
    def social_reward(sec: int) -> int:
        return 175 + sec * 48 + random.randint(0, 40)

    @staticmethod
    def timing_reward(sec: int) -> int:
        return 195 + sec * 52 + random.randint(0, 45)

    @staticmethod
    def pivot_reward(sec: int) -> int:
        return 240 + sec * 62 + random.randint(0, 50)

    @staticmethod
    def crack_bounty(sec: int, rep: int) -> int:
        raw = 12 + sec * 14
        mult = SECURITY_PAYOUT.get(sec, 1.0) * progression_mult(rep, sec)
        return max(8, int(raw * mult))

    @staticmethod
    def host_pick_weights(rep: int, security_level: int) -> int:
        """Bias contract targets: easy when new, harder when established."""
        if rep < 150:
            return max(1, 4 - security_level)
        if rep < 400:
            return max(1, security_level)
        return max(1, security_level * security_level)
