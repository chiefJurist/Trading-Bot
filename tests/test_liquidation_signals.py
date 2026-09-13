from datetime import datetime, timedelta
from liquidation_signals import detect_signals

OFFSET = timedelta(hours=1)


def test_detects_one_sided_cascade_in_single_minute():
    minute = datetime(2025, 1, 1, 12, 0)
    minutes = {minute: [{"symbol": "ETHUSDT", "side": "SELL"}] * 7}

    signals = detect_signals(minutes, window_minutes=1, threshold=7, time_offset=OFFSET)

    assert len(signals) == 1
    assert signals[0]["pair"] == "ETHUSDT"
    assert signals[0]["side"] == "SELL"
    assert signals[0]["occurrences"] == 7


def test_no_signal_when_opposite_side_present():
    minute = datetime(2025, 1, 1, 12, 0)
    minutes = {
        minute: [{"symbol": "ETHUSDT", "side": "SELL"}] * 7 + [{"symbol": "ETHUSDT", "side": "BUY"}]
    }

    assert detect_signals(minutes, window_minutes=1, threshold=7, time_offset=OFFSET) == []


def test_no_signal_below_threshold():
    minute = datetime(2025, 1, 1, 12, 0)
    minutes = {minute: [{"symbol": "ETHUSDT", "side": "SELL"}] * 6}

    assert detect_signals(minutes, window_minutes=1, threshold=7, time_offset=OFFSET) == []


def test_two_minute_window_catches_split_cascade():
    minute1 = datetime(2025, 1, 1, 12, 0)
    minute2 = datetime(2025, 1, 1, 12, 1)
    minutes = {
        minute1: [{"symbol": "BTCUSDT", "side": "BUY"}] * 4,
        minute2: [{"symbol": "BTCUSDT", "side": "BUY"}] * 4,
    }

    assert detect_signals(minutes, window_minutes=1, threshold=7, time_offset=OFFSET) == []

    signals = detect_signals(minutes, window_minutes=2, threshold=7, time_offset=OFFSET)
    assert len(signals) == 1
    assert signals[0]["occurrences"] == 8