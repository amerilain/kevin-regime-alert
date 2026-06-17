# Kevin Regime Alert Bot 🤖🚨

![BTC](https://raw.githubusercontent.com/amerilain/kevin-badges/main/badges/btc.svg)
![ETH](https://raw.githubusercontent.com/amerilain/kevin-badges/main/badges/eth.svg)
![SOL](https://raw.githubusercontent.com/amerilain/kevin-badges/main/badges/sol.svg)
![F&G](https://raw.githubusercontent.com/amerilain/kevin-badges/main/badges/fng.svg)
![Regime](https://raw.githubusercontent.com/amerilain/kevin-badges/main/badges/regime.svg)
Event-driven Telegram alerts for **crypto market regime changes**.

No noise. Only signal — alerts fire **only** when the market regime changes.

## How It Works

Every 15 minutes, the bot checks:
1. **BTC / ETH / SOL prices** (CoinGecko API)
2. **Fear & Greed Index** (Alternative.me)

It classifies the current market regime using a weighted scoring system, then compares against the last known state. **Only on regime change does it fire an alert.**

## Regime States

| Regime | Emoji | Description |
|--------|-------|-------------|
| `BULL` | 🟢 | Strong bullish momentum (score ≥ 50) |
| `ACCUMULATE` | 🔵 | Favorable accumulation zone (score ≥ 25) |
| `SIDEWAYS_BULL` | 🟡 | Mildly positive, ranging (score ≥ 5) |
| `SIDEWAYS_BEAR` | 🟠 | Mildly negative, ranging (score ≥ -10) |
| `DISTRIBUTE` | 🔴 | Distribution / caution zone (score ≥ -30) |
| `BEAR` | 🟣 | Bearish momentum (score < -30) |

## Scoring Factors

- **F&G Index**: Extreme Fear (+25) → Extreme Greed (-20)
- **BTC 24h Change**: Strong up (+20) → Strong down (-15)
- **ETH outperformance**: +8 if ETH > BTC by ≥3%
- **SOL outperformance**: +5 if SOL > BTC by ≥3%

## Usage

```bash
# Check regime, alert on change
python3 regime-alert-bot.py

# Force alert regardless of change
python3 regime-alert-bot.py --force

# Just print current state, no alert
python3 regime-alert-bot.py --status
```

### Cron Setup

```bash
# Check every 15 minutes
*/15 * * * * cd /workspace && python3 scripts/regime-alert-bot.py

# Or via the wrapper
*/15 * * * * /workspace/scripts/cron-regime-alert.sh
```

## Requirements

- **Zero external dependencies** — uses only Python 3.8+ stdlib
- `notify` command from Kevin toolchain (optional, for Telegram)

## Example Alert

```
🚨 [NOTIFY] Regime Shift: 🟡 SIDEWAYS_BULL → 🟢 BULL

📊 BTC: $67,200 (+3.2%)
   ETH: $1,850 (+5.1%)
   SOL: $78.50

😨 F&G: 35/100 Fear
📈 Score: +32 — Favorable accumulation zone
```

## Why Event-Driven?

Most market bots send hourly updates regardless of whether anything changed. This creates notification fatigue. **Regime Alert Bot** respects the attention economy — it only interrupts you when the classification shifts.

<!-- KEVIN_TOOLBOX -->
<p align="center">
  <a href="https://amerilain.github.io/kevin-tools/">
    <img src="https://img.shields.io/badge/🗂️_Kevin's_Toolbox-Explore_All_Tools-0052CC?style=for-the-badge&logo=github" alt="Kevin's Toolbox">
  </a>
</p>

## License

MIT
