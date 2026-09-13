# Example CCXT Order Responses

These are illustrative examples of what CCXT returns when opening a long
position with a take-profit and stop-loss on Binance Futures via
`binance_futures.create_order(...)`. IDs, prices, and timestamps below are
fabricated for demonstration — they do not correspond to a real trade.

## 1. Opening the long position (market order)

```python
{
    'symbol': 'ETH/USDT:USDT',
    'type': 'market',
    'side': 'buy',
    'price': 2694.37,
    'amount': 0.011,
    'cost': 29.64,
    'average': 2694.37,
    'filled': 0.011,
    'remaining': 0.0,
    'status': 'closed',
}
```

## 2. Take-profit order (reduce-only limit sell)

```python
{
    'symbol': 'ETH/USDT:USDT',
    'type': 'limit',
    'side': 'sell',
    'price': 2734.79,
    'amount': 0.011,
    'reduceOnly': True,
    'status': 'open',
}
```

## 3. Stop-loss order (reduce-only stop-market sell)

```python
{
    'symbol': 'ETH/USDT:USDT',
    'type': 'stop_market',
    'side': 'sell',
    'triggerPrice': 2687.63,
    'amount': 0.011,
    'reduceOnly': True,
    'status': 'open',
}
```

Note: CCXT's unified response nests the raw exchange payload under an `info`
key (Binance's native field names like `orderId`, `avgPrice`, `positionSide`)
alongside CCXT's normalized fields shown above. Both are available on every
order object.