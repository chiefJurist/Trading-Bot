import json
from binance_liquidations import parse_force_order


def test_parse_force_order_valid_message():
    msg = json.dumps({
        "data": {"o": {"s": "ETHUSDT", "S": "SELL", "ap": "2700.50", "z": "0.5", "T": 1739630186394}}
    })
    result = parse_force_order(msg)

    assert result["symbol"] == "ETHUSDT"
    assert result["side"] == "SELL"
    assert result["avg_price"] == 2700.50
    assert result["filled_qty"] == 0.5
    assert result["usd_value"] == 1350.25
    assert result["trade_time"] == 1739630186394


def test_parse_force_order_malformed_message_returns_none():
    assert parse_force_order("not valid json") is None


def test_parse_force_order_missing_fields_defaults_to_zero():
    msg = json.dumps({"data": {"o": {"s": "BTCUSDT", "S": "BUY"}}})
    result = parse_force_order(msg)

    assert result["avg_price"] == 0.0
    assert result["filled_qty"] == 0.0
    assert result["usd_value"] == 0.0