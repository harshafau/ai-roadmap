"""Telegram push notifications.

Posts to api.telegram.org via plain HTTPS. No third-party SDK needed. If
either bot_token or chat_id is empty the notifier is a silent no-op so the
bot still runs end-to-end without Telegram configured.

To set up:
  1. On Telegram, message @BotFather and run /newbot. Save the bot token.
  2. Message your new bot at least once (anything works).
  3. Open https://api.telegram.org/bot<TOKEN>/getUpdates in a browser; copy
     the numeric `chat.id` that appears.
  4. Put both into .env as TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from ..strategy import Signal

log = logging.getLogger(__name__)


@dataclass
class TelegramNotifier:
    bot_token: str = ""
    chat_id: str = ""
    timeout_s: float = 5.0

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send(self, text: str) -> bool:
        """Returns True on success, False on any failure (logged, not raised)."""
        if not self.enabled:
            return False
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            resp = requests.post(
                url,
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"},
                timeout=self.timeout_s,
            )
            resp.raise_for_status()
            return True
        except Exception as exc:
            log.warning("telegram send failed: %s", exc)
            return False

    def trade(self, mode: str, signal: Signal, qty: int, fill_price: float) -> None:
        emoji = "🟢" if signal.type.value == "BUY" else "🔴"
        stop = f"₹{signal.stop_loss:.2f}" if signal.stop_loss else "-"
        target = f"₹{signal.take_profit:.2f}" if signal.take_profit else "-"
        msg = (
            f"{emoji} <b>{mode.upper()} {signal.type.value}</b> {signal.symbol}\n"
            f"Qty: {qty} @ ₹{fill_price:.2f}\n"
            f"Stop: {stop}  Target: {target}\n"
            f"<i>{signal.reason}</i>"
        )
        self.send(msg)

    def daily_summary(self, realized_pnl: float, n_trades: int, open_positions: int) -> None:
        sign = "+" if realized_pnl >= 0 else ""
        msg = (
            f"📊 <b>End of session</b>\n"
            f"Realized P&L: {sign}₹{realized_pnl:,.0f}\n"
            f"Trades today: {n_trades}\n"
            f"Open positions: {open_positions}"
        )
        self.send(msg)

    def alert(self, text: str) -> None:
        self.send(f"⚠️ {text}")
