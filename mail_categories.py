"""Mail inbox categories for GUI tabs and filtering."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Game, MailMessage

MAIL_TABS = ("contracts", "rivals", "completed", "trash")

TAB_LABELS = {
    "contracts": "Contracts & Intel",
    "rivals": "Rivals",
    "completed": "Completed",
    "trash": "Trash",
}

CONTRACT_ID_RE = re.compile(
    r"(?:contract offer:|new contract:|contract)\s+([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)


def mission_id_from_mail(msg: MailMessage) -> str | None:
    match = CONTRACT_ID_RE.search(msg.subject)
    return match.group(1) if match else None


def is_rival_mail(msg: MailMessage) -> bool:
    return "@rival.net" in msg.sender.lower()


def is_completed_mail(msg: MailMessage, game: Game) -> bool:
    subject = msg.subject.lower()
    body = msg.body.lower()

    if subject.startswith("payment confirmed"):
        return True
    if "contract fulfilled" in body:
        return True

    mission_id = mission_id_from_mail(msg)
    if mission_id:
        for mission in game.missions.missions:
            if mission.mission_id == mission_id and mission.completed:
                return True

    return False


def mail_category(msg: MailMessage, game: Game) -> str:
    """Classify inbox mail into rivals, contracts, or completed."""
    if is_rival_mail(msg):
        return "rivals"
    if is_completed_mail(msg, game):
        return "completed"
    return "contracts"


def filter_messages(
    messages: list[MailMessage],
    category: str,
    game: Game,
) -> list[MailMessage]:
    if category == "trash":
        return list(messages)
    return [m for m in messages if mail_category(m, game) == category]


def unread_count(messages: list[MailMessage], category: str, game: Game) -> int:
    if category == "trash":
        return 0
    return sum(
        1 for m in messages
        if not m.read and mail_category(m, game) == category
    )
