from trading_bot.portfolio import Portfolio


def test_buy_then_sell_zeros_position(tmp_path):
    db = f"sqlite:///{tmp_path/'t.db'}"
    p = Portfolio(db, starting_cash=100_000)

    p.apply_fill("X", "BUY", 10, 100.0, "paper")
    positions = {pos.symbol: pos for pos in p.positions()}
    assert positions["X"].qty == 10
    assert positions["X"].avg_price == 100.0

    p.apply_fill("X", "SELL", 10, 120.0, "paper")
    assert p.positions() == []


def test_avg_price_weighted_across_buys(tmp_path):
    db = f"sqlite:///{tmp_path/'t.db'}"
    p = Portfolio(db, starting_cash=100_000)
    p.apply_fill("X", "BUY", 10, 100.0, "paper")
    p.apply_fill("X", "BUY", 10, 120.0, "paper")
    positions = {pos.symbol: pos for pos in p.positions()}
    assert positions["X"].qty == 20
    assert positions["X"].avg_price == 110.0
