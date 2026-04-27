from unittest.mock import MagicMock, patch

from trading_bot.notifications import TelegramNotifier
from trading_bot.strategy import Signal, SignalType


def test_disabled_when_token_or_chat_id_missing():
    assert TelegramNotifier("", "").enabled is False
    assert TelegramNotifier("abc", "").enabled is False
    assert TelegramNotifier("", "123").enabled is False
    assert TelegramNotifier("abc", "123").enabled is True


def test_send_is_silent_noop_when_disabled():
    n = TelegramNotifier("", "")
    # Must not raise even though we never configured anything.
    assert n.send("hello") is False


def test_send_swallows_network_errors():
    n = TelegramNotifier("token", "chat")
    with patch("trading_bot.notifications.telegram.requests.post", side_effect=RuntimeError("boom")):
        assert n.send("hello") is False  # logged + swallowed, not raised


def test_send_posts_to_telegram_api_when_enabled():
    n = TelegramNotifier("TOKEN", "12345")
    fake_resp = MagicMock()
    fake_resp.raise_for_status.return_value = None
    with patch("trading_bot.notifications.telegram.requests.post", return_value=fake_resp) as p:
        ok = n.send("hi")
    assert ok is True
    args, kwargs = p.call_args
    assert "https://api.telegram.org/botTOKEN/sendMessage" in args[0]
    assert kwargs["json"]["chat_id"] == "12345"
    assert kwargs["json"]["text"] == "hi"


def test_trade_message_contains_symbol_and_qty():
    n = TelegramNotifier("TOKEN", "12345")
    sig = Signal("RELIANCE", SignalType.BUY, 2950.0, "test reason", stop_loss=2920.0, take_profit=3010.0)
    captured = {}
    def fake_post(url, json, timeout):
        captured["text"] = json["text"]
        r = MagicMock(); r.raise_for_status.return_value = None
        return r
    with patch("trading_bot.notifications.telegram.requests.post", side_effect=fake_post):
        n.trade("paper", sig, qty=50, fill_price=2950.0)
    assert "RELIANCE" in captured["text"]
    assert "BUY" in captured["text"]
    assert "50" in captured["text"]
    assert "test reason" in captured["text"]
