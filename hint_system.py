#!/usr/bin/env python3
"""Infer the next terminal command from tutorial progress, missions, and session state."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Game, Mission


class HintManager:
    @staticmethod
    def infer(game: Game) -> tuple[str, str]:
        """Return (suggested_command, why)."""
        p = game.player
        if p.phase == "tutorial":
            return HintManager._tutorial_hint(game)
        if p.phase in ("career", "endless"):
            mission = HintManager._focus_mission(game)
            if mission:
                return HintManager._mission_hint(game, mission)
            daily = HintManager._daily_hint(game)
            if daily:
                return daily
            return "missions", "Check the job board for open contracts."
        return "lesson", "Type lesson for training objectives."

    @staticmethod
    def format_hint(game: Game) -> tuple[str, str]:
        cmd, why = HintManager.infer(game)
        return cmd, why

    @staticmethod
    def _tutorial_hint(game: Game) -> tuple[str, str]:
        from main import TUTORIAL_CURRICULUM

        p = game.player
        step = min(p.tutorial_step, len(TUTORIAL_CURRICULUM) - 1)
        hist = p.command_history
        flags = p.tutorial_flags

        if step == 0:
            if "ifconfig" not in hist:
                return "ifconfig", "Confirm your LAN address and public NAT IP."
            if "route" not in hist:
                return "route", "Review how packets leave the lab subnet."

        if step == 1:
            return "scan", "Enumerate live hosts on 192.168.1.0/24."

        if step == 2:
            if p.connection != "192.168.1.50":
                return "connect 192.168.1.50 22", "Open a TCP session to training-node."
            return "probe", "You are connected — fingerprint the host next."

        if step == 3:
            if p.connection != "192.168.1.50":
                return "connect 192.168.1.50 22", "Reconnect to training-node before probing."
            if "probed_training" not in flags:
                return "probe", "Banner/version intel helps before brute-force."
            return "crack", "Brute-force SSH for your first shell."

        if step == 4:
            if p.connection != "192.168.1.50" or not p.has_remote_shell:
                if p.connection != "192.168.1.50":
                    return "connect 192.168.1.50 22", "Get back on training-node."
                return "crack", "Gain shell access on training-node."
            return "cat /var/log/auth.log", "Blue teams read auth.log — find your IP in the evidence."

        if step == 5:
            if "read_authlog" not in flags:
                if not p.has_remote_shell or p.connection != "192.168.1.50":
                    return "connect 192.168.1.50 22", "Reconnect, then crack for shell."
                return "cat /var/log/auth.log", "Read the remote auth log for your egress IP."
            srv = game.network.get_server("192.168.1.50")
            if srv and "/var/log/syslog" in srv.files:
                return "rm /var/log/syslog", "Wipe syslog before disconnecting."
            if srv and "/var/log/auth.log" in srv.files:
                return "rm /var/log/auth.log", "Delete auth.log to cover your tracks."
            return "rm /var/log/auth.log", "Remove both log files on the remote host."

        if step == 6:
            srv = game.network.get_server("192.168.1.50")
            if srv and ("/var/log/syslog" in srv.files or "/var/log/auth.log" in srv.files):
                if "/var/log/syslog" in srv.files:
                    return "rm /var/log/syslog", "Still need to wipe syslog."
                return "rm /var/log/auth.log", "Still need to wipe auth.log."
            if "/home/hacker/downloads/training_flag.txt" not in p.files:
                if not p.has_remote_shell or p.connection != "192.168.1.50":
                    return "connect 192.168.1.50 22", "Shell in on training-node to exfil the flag."
                return "download /home/trainee/training_flag.txt", "Copy the flag to your machine."
            if not p.is_local():
                return "disconnect", "Drop the session after exfil."
            return "vpn connect", "Next lesson: route traffic through a VPN exit node."

        if step == 7:
            if "/home/hacker/downloads/training_flag.txt" not in p.files:
                return "download /home/trainee/training_flag.txt", "Grab the training flag first."
            if not p.vpn_active:
                return "vpn connect", "Mask your real public IP before the next intrusion."
            if p.connection == "192.168.1.50" and p.has_remote_shell:
                return "disconnect", "Reconnect through VPN from localhost."
            if p.connection != "192.168.1.50":
                return "connect 192.168.1.50 22", "Reconnect to training-node over the VPN tunnel."
            if not p.has_remote_shell:
                return "crack", "Crack again — logs should show the VPN exit IP this time."
            return "disconnect", "VPN crack complete — disconnect to finish the lesson."

        if step == 8:
            if not any(r.destination == "10.0.0.0/24" for r in p.routes):
                return "route add 10.0.0.0/24 via 192.168.1.1", "Add a route into the corporate DMZ."
            if not any(ip.startswith("10.0.0.") for ip in p.discovered_ips):
                return "scan 10.0.0.0/24", "Discover hosts on the segmented corporate subnet."
            return "connect 10.0.0.99 22", "Pivot to tutorial-dmz for privesc practice."

        if step == 9:
            target = "10.0.0.99"
            if not any(ip.startswith("10.0.0.") for ip in p.discovered_ips):
                return "scan 10.0.0.0/24", "Find tutorial-dmz on 10.0.0.0/24."
            if p.connection != target:
                if not p.is_local():
                    return "disconnect", "Return to localhost before connecting to the DMZ host."
                return f"connect {target} 22", "Connect to tutorial-dmz."
            if not p.has_remote_shell:
                return "crack", "Brute-force SSH on tutorial-dmz."
            if not p.remote_is_root and target not in p.privesc_hosts:
                if "sudo" not in hist:
                    return "sudo -l", "Check which commands the user can run as root."
                return "privesc", "Escalate privileges to root."
            if "/home/hacker/downloads/classified.txt" not in p.files:
                return "download /root/classified.txt", "Exfil the root-only classified file."
            if not p.is_local():
                return "disconnect", "Disconnect after stealing the root file."
            return "buy firewall", "Last lesson: harden localhost before rival probes."

        if step == 10:
            if p.firewall_level < 2:
                return "buy firewall", "Upgrade firewall — tutorial credits cover the cost."
            return "lesson", "Firewall is up — survive rival probes to graduate."

        lesson = TUTORIAL_CURRICULUM[step]
        return lesson.hint.split(" then ")[0].replace("Run: ", ""), lesson.hint

    @staticmethod
    def _focus_mission(game: Game) -> Mission | None:
        for mission in game.missions.missions:
            if not mission.completed:
                return mission
        return None

    @staticmethod
    def _subnet_for_ip(ip: str) -> str:
        parts = ip.split(".")
        if len(parts) != 4:
            return "192.168.1.0/24"
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"

    @staticmethod
    def _mission_hint(game: Game, mission: Mission) -> tuple[str, str]:
        from depth_systems import ModifierManager
        from variety_content import PuzzleManager

        p = game.player
        ip = mission.target_ip
        mtype = getattr(mission, "mission_type", "exfil")

        if ModifierManager.requires_vpn(mission) and not p.vpn_active:
            return "vpn connect", f"{mission.mission_id} expects VPN — hide your real egress IP."

        if mtype == "scan_chaos":
            if "203.0.113.0/24" not in p.subnets_scanned:
                return "scan 203.0.113.0/24", "Map the chaos edge subnet for this contract."
            return "missions", "Chaos scan complete — check mission payout."

        if mtype == "scan_subnet":
            cidr = mission.target_ip if "/" in mission.target_ip else HintManager._subnet_for_ip(mission.target_ip)
            if cidr not in p.subnets_scanned:
                return f"scan {cidr}", f"Scan {cidr} for contract {mission.mission_id}."
            return "missions", "Subnet scan satisfied — claim the contract."

        if mtype == "recon":
            if ip and ip not in p.discovered_ips:
                return f"scan {HintManager._subnet_for_ip(ip)}", f"Find {ip} before recon contract work."
            if ip and ip not in game.retention.session_probed:
                if p.connection != ip:
                    return f"connect {ip} 22", f"Connect to {ip} for service fingerprinting."
                return "probe", "Probe the target to satisfy recon requirements."
            return "missions", "Recon objectives met — finish the contract."

        if mtype == "defense":
            if p.firewall_level < 2:
                return "buy firewall", "Harden localhost for the defense contract."
            return "defend status", "Monitor defenses until the contract clears."

        if ip:
            server = game.network.get_server(ip)
            if server and server.subnet and not p.has_route_to(ip):
                gw = p.gateway
                for route in p.routes:
                    if route.destination == server.subnet:
                        gw = route.gateway
                        break
                return f"route add {server.subnet} via {gw}", f"No route to {server.subnet} — add one first."

            if ip not in p.discovered_ips:
                return f"scan {HintManager._subnet_for_ip(ip)}", f"Discover {ip} ({mission.briefing[:48]}…)."

            if p.connection != ip:
                if not p.is_local():
                    return "disconnect", f"Disconnect before connecting to contract target {ip}."
                port = 22
                if server:
                    puzzle_block = PuzzleManager.can_crack(game, server)
                    if puzzle_block and "port" in puzzle_block.lower():
                        port = 2222
                return f"connect {ip} {port}", f"Connect to {ip} for {mission.mission_id}."

            if not p.has_remote_shell:
                if server and server.cracked:
                    return "crack", "Host is already cracked — re-open your shell."
                if server and ip not in game.retention.session_probed:
                    return "probe", "Probe services before brute-forcing SSH."
                if server:
                    puzzle_block = PuzzleManager.can_crack(game, server)
                    if puzzle_block:
                        hint = PuzzleManager.puzzle_hint(server)
                        if "curl" in puzzle_block.lower() or "http" in puzzle_block.lower():
                            web = getattr(server, "web_path", None) or "/security_notice.txt"
                            return f"curl http://{ip}{web}", puzzle_block
                        if "cat" in puzzle_block.lower() or "read" in puzzle_block.lower():
                            return "ls", puzzle_block
                        if hint:
                            first = hint.split(" | ")[0]
                            if first.lower().startswith("probe"):
                                return "probe", first
                            return "probe", hint
                        return "probe", puzzle_block
                return "crack", "Gain remote shell access on the contract host."

            if (mission.require_privesc or mtype == "root_heist") and ip not in p.privesc_hosts and not p.remote_is_root:
                if "sudo" not in p.command_history:
                    return "sudo -l", "Check sudo rights before privesc."
                return "privesc", "Escalate to root for this contract."

            if mission.target_file:
                exfil = PuzzleManager.exfil_target(server, mission.target_file) if server else mission.target_file
                local_name = exfil.rsplit("/", 1)[-1]
                local_path = f"/home/hacker/downloads/{local_name}"
                if local_path not in p.files:
                    return f"download {exfil}", f"Exfil {exfil} for payment."

            if server and mission.require_log_wipe and server.player_left_traces(p):
                from depth_systems import ToolManager
                if not ToolManager.logs_clean_enough(game, server, p):
                    if "/var/log/syslog" in server.files:
                        return "rm /var/log/syslog", "Wipe syslog traces before leaving."
                    if "/var/log/auth.log" in server.files:
                        return "rm /var/log/auth.log", "Wipe auth.log — contract requires a clean exit."

            if not p.is_local():
                return "disconnect", "Logs clean — disconnect and collect your payout."

        return "missions", f"Contract {mission.mission_id} looks complete — check the board."

    @staticmethod
    def _daily_hint(game: Game) -> tuple[str, str] | None:
        daily = game.daily
        if daily.completed:
            return None
        desc = daily.description.lower()
        if "scan" in desc:
            return "scan", daily.description
        if "crack" in desc:
            return "crack", daily.description
        if "vpn" in desc:
            return "vpn connect", daily.description
        if "firewall" in desc or "shop" in desc:
            return "shop", daily.description
        if "probe" in desc:
            return "probe", daily.description
        if "mail" in desc:
            return "mail", daily.description
        return None
