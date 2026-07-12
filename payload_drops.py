#!/usr/bin/env python3
"""Anonymous AI dead-drop payloads — hunt IPs from mail instead of buying botnet kits."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main import Game

from botnet_system import PAYLOAD_SPECS

SENDER = "shard@null.dark"

# shop_key, remote path, short label for mail
DROP_ROTATION: tuple[tuple[str, str, str], ...] = (
    ("miner_payload", "/var/stash/miner.bundle", "miner"),
    ("ddos_payload", "/var/stash/ddos.bundle", "DDoS flooder"),
    ("leak_payload", "/var/stash/leak.bundle", "leak worm"),
    ("virus_payload", "/var/stash/virus.bundle", "autonomous virus"),
    ("ransom_payload", "/var/stash/ransom.bundle", "ransom locker"),
    ("deface_payload", "/var/stash/deface.bundle", "defacer"),
    ("frame_payload", "/var/stash/frame.bundle", "frame kit"),
)

STASH_PATHS: frozenset[str] = frozenset(row[1] for row in DROP_ROTATION)
SHOP_KEY_BY_PATH: dict[str, str] = {row[1]: row[0] for row in DROP_ROTATION}

COOLDOWN = 22
INITIAL_DELAY = 8


class PayloadDropManager:
    @staticmethod
    def _career(game: Game) -> bool:
        return game.player.phase in ("career", "endless")

    @staticmethod
    def _ensure_route(game: Game) -> None:
        from main import Route

        p = game.player
        if not any(r.destination == "198.18.0.0/24" for r in p.routes):
            p.routes.append(Route("198.18.0.0/24", p.gateway))

    @staticmethod
    def _bundle_content(label: str) -> str:
        return (
            f"# payload bundle — {label}\n"
            "encrypted operator kit; download to exfil and unpack locally\n"
        )

    @staticmethod
    def _mail_body(ip: str, path: str, label: str, password: str, *, first: bool) -> str:
        last_octet = ip.rsplit(".", 1)[-1]
        fname = path.rsplit("/", 1)[-1]
        if first:
            return (
                "I mirror abandoned mesh nodes when operators go dark.\n"
                f"Tonight: something useful for a {label}.\n\n"
                f"  subnet: 198.18.0.0/24\n"
                f"  host ends in .{last_octet}\n"
                f"  path: {path}\n"
                f"  ssh pass hint: {password}\n\n"
                "scan, connect, crack, download the bundle. Then: infect on a cracked host.\n"
                "More drops when you're ready — watch Mail.\n\n"
                "— shard"
            )
        hints = random.choice([
            f"Node .{last_octet} still warm. {fname} is the package.",
            f"Dead relay 198.18.x.{last_octet} — look in /var/stash/.",
            f"Coords partial: *.*.*.{last_octet} — {label} kit inside {fname}.",
        ])
        return (
            f"{hints}\n"
            f"SSH: try '{password}' on the drop host.\n"
            f"Full path after crack: {path}\n\n"
            "— shard"
        )

    @staticmethod
    def active_drop(game: Game) -> dict[str, Any] | None:
        ip = getattr(game.meta, "payload_drop_ip", "")
        if not ip:
            return None
        path = getattr(game.meta, "payload_drop_path", "")
        key = getattr(game.meta, "payload_drop_key", "")
        if not path or not key:
            return None
        if getattr(game.meta, "payload_drop_claimed", False):
            return None
        return {"ip": ip, "path": path, "shop_key": key}

    @staticmethod
    def spawn(game: Game, *, force: bool = False) -> bool:
        from main import Server

        if not PayloadDropManager._career(game):
            return False
        if not force and PayloadDropManager.active_drop(game):
            return False

        idx = getattr(game.meta, "payload_drop_index", 0) % len(DROP_ROTATION)
        shop_key, path, label = DROP_ROTATION[idx]
        game.meta.payload_drop_index = idx + 1

        PayloadDropManager._ensure_route(game)
        octet = random.randint(60, 240)
        ip = f"198.18.{random.randint(1, 254)}.{octet}"
        password = random.choice(["nullshard", "deadrelay", "stash404", "meshdrop"])
        hostname = f"drop-{octet}"

        bundle = PayloadDropManager._bundle_content(label)
        if ip not in game.network.servers:
            game.network.servers[ip] = Server(
                ip,
                hostname,
                1,
                subnet="198.18.0.0/24",
                ssh_user="stash",
                ssh_password=password,
                extra_files={path: bundle},
            )
        else:
            from main import VirtualFile
            game.network.servers[ip].files[path] = VirtualFile(path, bundle, owner="stash")

        game.player.discovered_ips.add(ip)
        game.meta.payload_drop_ip = ip
        game.meta.payload_drop_path = path
        game.meta.payload_drop_key = shop_key
        game.meta.payload_drop_password = password
        game.meta.payload_drop_claimed = False
        game.meta.payload_drop_cd = COOLDOWN

        first = idx == 0 and game.meta.payload_drop_index <= 1
        subject = random.choice([
            f"dead drop — {label}",
            f"mesh stash / .{octet}",
            "anonymous payload coords",
        ])
        game.mail.send(
            SENDER,
            subject,
            PayloadDropManager._mail_body(ip, path, label, password, first=first),
        )
        return True

    @staticmethod
    def restore_from_save(game: Game) -> None:
        """Recreate dead-drop host after load (dynamic hosts are not fully serialized)."""
        if getattr(game.meta, "payload_drop_claimed", False):
            return
        ip = getattr(game.meta, "payload_drop_ip", "")
        path = getattr(game.meta, "payload_drop_path", "")
        password = getattr(game.meta, "payload_drop_password", "")
        if not ip or not path or not password:
            return
        if game.network.get_server(ip):
            return
        from main import Server, VirtualFile

        shop_key = getattr(game.meta, "payload_drop_key", "")
        label = shop_key.replace("_payload", "").replace("_", " ")
        bundle = PayloadDropManager._bundle_content(label)
        octet = ip.rsplit(".", 1)[-1]
        game.network.servers[ip] = Server(
            ip,
            f"drop-{octet}",
            1,
            subnet="198.18.0.0/24",
            ssh_user="stash",
            ssh_password=password,
            extra_files={path: bundle},
        )
        game.network.servers[ip].files[path] = VirtualFile(path, bundle, owner="stash")
        PayloadDropManager._ensure_route(game)
        game.player.discovered_ips.add(ip)

    @staticmethod
    def on_career_start(game: Game) -> None:
        if not PayloadDropManager._career(game):
            return
        if getattr(game.meta, "payload_drop_index", 0) > 0 or PayloadDropManager.active_drop(game):
            return
        game.meta.payload_drop_cd = INITIAL_DELAY
        game.meta.payload_drop_index = 0

    @staticmethod
    def on_chaos_start(game: Game) -> None:
        """Chaos skips the shop — first drop lands immediately."""
        game.meta.payload_drop_index = 0
        game.meta.payload_drop_cd = 0
        PayloadDropManager.spawn(game, force=True)

    @staticmethod
    def on_post_command(game: Game) -> None:
        if not PayloadDropManager._career(game):
            return
        cd = getattr(game.meta, "payload_drop_cd", 0)
        if cd > 0:
            game.meta.payload_drop_cd = cd - 1
            return
        if PayloadDropManager.active_drop(game):
            return
        PayloadDropManager.spawn(game)

    @staticmethod
    def try_claim_download(game: Game, remote_ip: str, path: str) -> bool:
        drop = PayloadDropManager.active_drop(game)
        if not drop:
            return False
        if drop["ip"] != remote_ip or drop["path"] != path:
            return False
        from faction_consumables import ConsumableManager
        from main import success, teach

        key = drop["shop_key"]
        spec = PAYLOAD_SPECS.get(
            next((k for k, v in PAYLOAD_SPECS.items() if v["shop_key"] == key), ""),
            {},
        )
        label = spec.get("label", key)
        ConsumableManager.add_to_inventory(game, key, 1)
        game.meta.payload_drop_claimed = True
        success(f"Unpacked {label} — added to inventory (infect when on a cracked host).")
        teach("Dead drops rotate. shard@null.dark will mail the next coords when you're ready.")
        game.mail.send(
            SENDER,
            f"received — {label}",
            "Bundle checksum OK. Burn the relay when you're done.\n\n— shard",
        )
        return True

    @staticmethod
    def hint_when_empty(game: Game, shop_key: str) -> str | None:
        from faction_consumables import ConsumableManager

        if ConsumableManager.inventory_count(game, shop_key) > 0:
            return None
        drop = PayloadDropManager.active_drop(game)
        if drop and drop["shop_key"] == shop_key:
            return (
                f"Check Mail from {SENDER} — dead drop on {drop['ip']}, "
                f"download {drop['path']}"
            )
        cd = getattr(game.meta, "payload_drop_cd", 0)
        if cd > 0:
            return f"No {shop_key} — next shard drop in ~{cd} commands. Watch Mail."
        return f"No {shop_key} — watch Mail from {SENDER} for dead-drop coords."
