#!/usr/bin/env python3
"""
Regime Alert Bot — Event-Driven Telegram Alerts
=================================================
Zero dependencies. Just Python 3.8+ stdlib.
Sends Telegram alerts only when market REGIME CHANGES.
Respects the attention economy — no noise, only signal.

Usage:
  python3 scripts/regime-alert-bot.py          # Check and alert on change
  python3 scripts/regime-alert-bot.py --force  # Force alert regardless of change
  python3 scripts/regime-alert-bot.py --status # Just print current regime, no alert

Cron: */15 * * * * python3 /workspace/scripts/regime-alert-bot.py
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────
STATE_FILE = Path("/workspace/data/regime-state.json")
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


# ── API Helpers ─────────────────────────────────────────────────────────

def api_get(url: str, timeout: int = 20) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[WARN] API error: {e}", file=sys.stderr)
        return None


def get_prices() -> dict:
    data = api_get(
        "https://api.coingecko.com/api/v3/simple/price"
        "?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true"
    )
    if not data:
        return {}
    result = {}
    for key, coin_id in [("BTC", "bitcoin"), ("ETH", "ethereum"), ("SOL", "solana")]:
        if coin_id in data:
            c = data[coin_id]
            result[key] = {"price": c.get("usd", 0), "change_24h": c.get("usd_24h_change", 0)}
    return result


def get_fng() -> dict:
    data = api_get("https://api.alternative.me/fng/?limit=1")
    if data and "data" in data and len(data["data"]) > 0:
        v = data["data"][0]
        return {"value": int(v["value"]), "classification": v["value_classification"]}
    return {"value": 50, "classification": "Neutral"}


# ── Regime Classification ───────────────────────────────────────────────

def classify_regime(prices: dict, fng: dict) -> dict:
    score = 0
    fng_val = fng.get("value", 50)
    if fng_val <= 25:
        score += 25
    elif fng_val <= 40:
        score += 15
    elif fng_val <= 60:
        score += 0
    elif fng_val <= 75:
        score -= 10
    else:
        score -= 20

    btc = prices.get("BTC", {})
    btc_chg = btc.get("change_24h", 0)
    btc_price = btc.get("price", 0)

    if abs(btc_chg) < 0.5:
        pass
    elif btc_chg > 5:
        score += 20
    elif btc_chg > 2:
        score += 10
    elif btc_chg > 0:
        score += 3
    elif btc_chg > -2:
        score -= 2
    elif btc_chg > -5:
        score -= 8
    else:
        score -= 15

    eth = prices.get("ETH", {})
    eth_chg = eth.get("change_24h", 0)
    if eth_chg and btc_chg and eth_chg > btc_chg + 3:
        score += 8

    sol = prices.get("SOL", {})
    sol_chg = sol.get("change_24h", 0)
    if sol_chg and btc_chg and sol_chg > btc_chg + 3:
        score += 5

    if score >= 50:
        regime, emoji, desc = "BULL", "🟢", "Strong bullish momentum"
    elif score >= 25:
        regime, emoji, desc = "ACCUMULATE", "🔵", "Favorable accumulation zone"
    elif score >= 5:
        regime, emoji, desc = "SIDEWAYS_BULL", "🟡", "Mildly positive, ranging"
    elif score >= -10:
        regime, emoji, desc = "SIDEWAYS_BEAR", "🟠", "Mildly negative, ranging"
    elif score >= -30:
        regime, emoji, desc = "DISTRIBUTE", "🔴", "Distribution / caution zone"
    else:
        regime, emoji, desc = "BEAR", "🟣", "Bearish momentum"

    return {
        "regime": regime, "emoji": emoji, "description": desc, "score": score,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prices": {"BTC": f"${btc_price:,.0f}", "ETH": f"${eth.get('price',0):,.0f}", "SOL": f"${sol.get('price',0):,.2f}"},
        "changes": {"BTC": f"{btc_chg:+.1f}%", "ETH": f"{eth_chg:+.1f}%"},
        "fng": f"{fng_val}/100 {fng.get('classification', '?')}",
    }


# ── State Management ────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ── Notification ────────────────────────────────────────────────────────

def send_notify(message: str):
    if len(message) > 3500:
        message = message[:3500] + "\n\n... (truncated)"
    try:
        result = subprocess.run(["notify", message], capture_output=True, text=True, timeout=20)
        if result.returncode == 0:
            print(f"[OK] Notify sent")
            return True
        else:
            print(f"[FAIL] {result.stderr.strip() or result.stdout.strip()}", file=sys.stderr)
            return False
    except FileNotFoundError:
        print("[FAIL] notify command not found", file=sys.stderr)
        return False
    except subprocess.TimeoutExpired:
        print("[FAIL] notify timed out", file=sys.stderr)
        return False


def format_change_alert(current: dict, previous: dict) -> str:
    prev_regime = previous.get("regime", "UNKNOWN")
    prev_emoji = previous.get("emoji", "⬜")
    return (
        f"🚨 [NOTIFY] Regime Shift: {prev_emoji} {prev_regime} → {current['emoji']} {current['regime']}\n"
        f"\n"
        f"📊 BTC: {current['prices']['BTC']} ({current['changes']['BTC']})\n"
        f"   ETH: {current['prices']['ETH']} ({current['changes']['ETH']})\n"
        f"   SOL: {current['prices']['SOL']}\n"
        f"\n"
        f"😨 F&G: {current['fng']}\n"
        f"📈 Score: {current['score']:+d} — {current['description']}\n"
        f"\n"
        f"🕐 {current['timestamp']}"
    )


# ── Main ────────────────────────────────────────────────────────────────

def main():
    force = "--force" in sys.argv
    status_only = "--status" in sys.argv

    print("=" * 50)
    print("Regime Alert Bot")

    prices = get_prices()
    if not prices:
        print("[FAIL] Could not fetch prices. Aborting.")
        return 1

    fng = get_fng()
    btc_price = prices.get("BTC", {}).get("price", 0)
    btc_chg = prices.get("BTC", {}).get("change_24h", 0)
    print(f"  BTC: ${btc_price:,.0f} ({btc_chg:+.2f}%)")
    print(f"  F&G: {fng.get('value', '?')}/100 ({fng.get('classification', '?')})")

    current = classify_regime(prices, fng)
    print(f"  Regime: {current['emoji']} {current['regime']} (score: {current['score']:+d})")

    state = load_state()
    previous = state if state else {}
    prev_regime = previous.get("regime")
    changed = current["regime"] != prev_regime
    is_first_run = prev_regime is None

    if status_only:
        print(f"\n  Current: {current['emoji']} {current['regime']} ({current['score']:+d})")
        print(f"  Previous: {prev_regime or '(none)'}  Changed: {'YES' if changed else 'NO'}")
        save_state(state | current)
        return 0

    if force and changed:
        print(f"\n  ⚠️ FORCED — {current['regime']}")
        message = format_change_alert(current, previous)
        send_notify(message)
    elif is_first_run:
        print(f"\n  📋 First run — baseline: {current['regime']}")
        message = (
            f"[NOTIFY] Regime Baseline Established\n\n"
            f"Regime: {current['emoji']} {current['regime']} (score: {current['score']:+d})\n"
            f"BTC: {current['prices']['BTC']} | ETH: {current['prices']['ETH']}\n"
            f"F&G: {current['fng']}\n"
            f"\nBot will now monitor for regime shifts."
        )
        send_notify(message)
    elif changed:
        print(f"\n  ⚠️ REGIME CHANGE: {prev_regime} → {current['regime']}")
        message = format_change_alert(current, previous)
        send_notify(message)
    else:
        print(f"\n  ✅ No change — still {current['regime']}")

    state.update(current)
    save_state(state)
    print(f"\n  State saved")

    print(f"\n  Output: {json.dumps({'regime': current['regime'], 'score': current['score'], 'changed': changed})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
