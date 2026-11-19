"""
Future monetization hooks (disabled by default).

When ready to connect businesses / ads for player rewards:
  ADS_ENABLED=1
  MONETIZATION_PROVIDER=...
  ADS_PUBLISHER_ID=...

Do not enable in academic mode without policy review.
"""
from __future__ import annotations
import os


def ads_enabled() -> bool:
    return (os.environ.get("ADS_ENABLED") or "0").strip() in ("1", "true", "yes", "on")


def monetization_mode() -> str:
    """off | preview | live"""
    if not ads_enabled():
        return "off"
    return (os.environ.get("MONETIZATION_MODE") or "preview").strip().lower()


def ad_slot_html(placement: str = "dashboard") -> str:
    """Return HTML for an ad slot, or empty string when disabled."""
    if not ads_enabled():
        return ""
    pub = os.environ.get("ADS_PUBLISHER_ID") or ""
    # Placeholder only — real network scripts added later by operator
    return (
        f'<aside class="ad-slot" data-placement="{placement}" data-publisher="{pub}">'
        f'<span class="ad-label">Sponsored (preview)</span>'
        f'<p>Business ad inventory will appear here when ADS_ENABLED is configured.</p>'
        f"</aside>"
    )


def player_reward_policy() -> dict:
    """Describe future earn-with-ads rules (not active until live)."""
    return {
        "enabled": ads_enabled() and monetization_mode() == "live",
        "mode": monetization_mode(),
        "note": "Future: verified views/actions may credit a player wallet; not implemented for production payouts yet.",
    }
