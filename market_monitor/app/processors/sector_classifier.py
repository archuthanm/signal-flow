from __future__ import annotations

from market_monitor.app.config import SECTOR_DISPLAY_NAMES


def display_sector_name(sector: str | None) -> str:
    if not sector:
        return "Unclassified"
    return SECTOR_DISPLAY_NAMES.get(sector, sector.replace("_", " ").title())
