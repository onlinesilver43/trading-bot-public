#!/usr/bin/env python3
"""
Test script for SMA crossover strategy
Tests the strategy with synthetic market data
"""

import numpy as np
from strategy.sma_crossover import decide, indicators

def test_sma_strategy():
    """Test the SMA crossover strategy with synthetic data"""
    
    print("🧪 Testing SMA Crossover Strategy...")
    
    # Generate synthetic price data (200 candles)
    np.random.seed(42)  # For reproducible results
    base_price = 100.0
    prices = [base_price]
    
    for i in range(199):
        # Random walk with slight upward bias
        change = np.random.normal(0.001, 0.02)
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 0.01))  # Ensure positive prices
    
    print(f"✅ Generated {len(prices)} synthetic price candles")
    print(f"   Price range: ${min(prices):.2f} - ${max(prices):.2f}")
    
    # Test indicators function
    print("\n📊 Testing indicators function...")
    fast_sma, slow_sma = indicators(prices, fast=10, slow=20, closed_only=True)
    
    print(f"   Fast SMA (10): {len(fast_sma)} values")
    print(f"   Slow SMA (20): {len(slow_sma)} values")
    print(f"   Last fast SMA: {fast_sma[-1]:.2f}")
    print(f"   Last slow SMA: {slow_sma[-1]:.2f}")
    
    # Test decide function
    print("\n🎯 Testing decide function...")
    
    # Mock configuration
    class MockConfig:
        confirm_bars = 3
        threshold_pct = 0.01
        min_hold_bars = 5
    
    config = MockConfig()
    
    # Test decision logic
    last_price = prices[-1]
    last_trade_ts = 0
    current_ts = len(prices) * 60000  # 1 minute bars
    tf_ms = 60000
    
    signal, reason, cooldown_ok, sep = decide(
        fast_sma, slow_sma, last_price, config, last_trade_ts, current_ts, tf_ms
    )
    
    print(f"   Signal: {signal}")
    print(f"   Reason: {reason}")
    print(f"   Cooldown OK: {cooldown_ok}")
    print(f"   Separation: {sep:.4f}")
    
    # Test with different scenarios
    print("\n🔄 Testing different market scenarios...")
    
    # Scenario 1: Strong uptrend
    uptrend_prices = [100 + i * 0.5 for i in range(50)]
    fast_uptrend, slow_uptrend = indicators(uptrend_prices, 5, 10, True)
    
    signal_up, reason_up, _, sep_up = decide(
        fast_uptrend, slow_uptrend, uptrend_prices[-1], config, 0, 50 * 60000, 60000
    )
    
    print(f"   Uptrend scenario: {signal_up} ({reason_up}) - sep: {sep_up:.4f}")
    
    # Scenario 2: Strong downtrend
    downtrend_prices = [100 - i * 0.5 for i in range(50)]
    fast_downtrend, slow_downtrend = indicators(downtrend_prices, 5, 10, True)
    
    signal_down, reason_down, _, sep_down = decide(
        fast_downtrend, slow_downtrend, downtrend_prices[-1], config, 0, 50 * 60000, 60000
    )
    
    print(f"   Downtrend scenario: {signal_down} ({reason_down}) - sep: {sep_down:.4f}")
    
    print("\n✅ Strategy testing completed successfully!")
    return True

if __name__ == "__main__":
    try:
        test_sma_strategy()
    except Exception as e:
        print(f"❌ Strategy test failed: {e}")
        import traceback
        traceback.print_exc()
