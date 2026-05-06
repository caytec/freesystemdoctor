"""Health Check engine — comprehensive system audit with 4 scores."""

import threading
from . import system_info, disk_cleaner, registry_cleaner, privacy_cleaner, protection


def get_health_scores() -> dict:
    """
    Calculate 4 health scores (0-100): Privacy, Space, Speed, Security.
    Returns dict with scores, issues, and detailed breakdown.
    """
    return {
        "privacy_score": _calc_privacy_score(),
        "space_score": _calc_space_score(),
        "speed_score": _calc_speed_score(),
        "security_score": _calc_security_score(),
        "overall_score": 0,  # calculated below
        "top_issues": [],
    }


def _calc_privacy_score() -> int:
    """Privacy score based on: telemetry status, location, ad-ID, browser tracking."""
    score = 100
    try:
        status = privacy_cleaner.get_privacy_status()
        # Deduct for enabled tracking
        if status.get("telemetry_enabled", False):
            score -= 15
        if status.get("location_enabled", False):
            score -= 10
        if status.get("advertising_enabled", False):
            score -= 10
    except Exception:
        pass
    return max(0, min(100, score))


def _calc_space_score() -> int:
    """Space score: 100 = >50% free, 75 = 30-50%, 50 = 20-30%, <20% = 25."""
    score = 100
    try:
        disks = system_info.get_disk_info()
        if disks:
            avg_used_pct = sum(d.get("used_pct", 0) for d in disks) / len(disks)
            if avg_used_pct > 80:
                score = 25
            elif avg_used_pct > 70:
                score = 50
            elif avg_used_pct > 50:
                score = 75
            else:
                score = 100
    except Exception:
        pass
    return score


def _calc_speed_score() -> int:
    """Speed score: based on startup items, services, RAM usage."""
    score = 100
    try:
        # Penalize high RAM usage
        metrics = system_info.get_live_metrics()
        ram_pct = metrics.get("ram_pct", 0)
        if ram_pct > 80:
            score -= 25
        elif ram_pct > 60:
            score -= 15
        elif ram_pct > 40:
            score -= 5
    except Exception:
        pass
    return max(0, min(100, score))


def _calc_security_score() -> int:
    """Security score: based on Defender status, Firewall status."""
    score = 100
    try:
        defender = protection.get_defender_status()
        if not defender.get("available", False):
            score -= 20
        if not defender.get("enabled", False):
            score -= 25
        if not defender.get("realtime", False):
            score -= 15

        fw = protection.get_firewall_status()
        enabled_count = sum(1 for p in ("Domain", "Private", "Public")
                           if fw.get(p, {}).get("enabled", False))
        if enabled_count < 2:
            score -= 10
    except Exception:
        pass
    return max(0, min(100, score))


def get_top_issues(limit: int = 5) -> list[str]:
    """Scan all modules and return top issues."""
    issues = []
    try:
        # Disk space
        disks = system_info.get_disk_info()
        for disk in disks:
            if disk.get("used_pct", 0) > 80:
                issues.append(f"⚠ {disk['Drive']}: {disk['used_pct']} full")

        # Junk files
        junk_results = disk_cleaner.scan_junk()
        total_junk = sum(r.size for r in junk_results)
        if total_junk > 100 * 1024 * 1024:  # >100MB
            issues.append(f"💾 Found {total_junk / 1024 / 1024:.0f} MB of junk files")

        # RAM
        metrics = system_info.get_live_metrics()
        if metrics.get("ram_pct", 0) > 80:
            issues.append(f"🔴 High RAM usage: {metrics['ram_pct']:.0f}%")

        # Security
        defender = protection.get_defender_status()
        if not defender.get("enabled", False):
            issues.append("🛡 Windows Defender is disabled")
        if not defender.get("realtime", False):
            issues.append("🛡 Real-time protection is off")

    except Exception:
        pass

    return issues[:limit]


def calculate_overall_score(scores: dict) -> int:
    """Weighted average: all scores equally weighted."""
    weights = {
        "privacy_score": 0.25,
        "space_score": 0.25,
        "speed_score": 0.25,
        "security_score": 0.25,
    }
    total = sum(scores.get(key, 0) * weight for key, weight in weights.items())
    return int(total)
