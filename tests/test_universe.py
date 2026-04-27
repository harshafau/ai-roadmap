from trading_bot.universe import load_universe, universe_path


def test_nifty50_loads_and_uses_stub_ids_when_empty():
    instruments = load_universe(universe_path("nifty50"))
    assert len(instruments) >= 49  # 50 names; allow tolerance for index changes
    syms = {i.symbol for i in instruments}
    assert "RELIANCE" in syms and "HDFCBANK" in syms and "INFY" in syms
    # security_ids may be empty in the committed CSV — loader fills with STUBs.
    for i in instruments:
        assert i.security_id, f"empty security_id for {i.symbol}"
