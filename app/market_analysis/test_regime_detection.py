#!/usr/bin/env python3
"""
Safe test script for market regime detection system
This script tests the regime detection without affecting the main trading bot
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def create_test_market_data():
    """Create synthetic market data for testing regime detection"""
    
    # Generate 200 candles of test data (simulating different market conditions)
    test_data = []
    base_price = 50000.0  # BTC starting price
    current_price = base_price
    
    # Simulate different market conditions
    for i in range(200):
        timestamp = int((datetime.now() - timedelta(minutes=200-i)).timestamp() * 1000)
        
        # Simulate price movements
        if i < 50:  # Bull market
            price_change = current_price * 0.002  # 0.2% increase
            volatility = 0.01  # Low volatility
        elif i < 100:  # Bear market
            price_change = -current_price * 0.0015  # 0.15% decrease
            volatility = 0.008  # Low volatility
        elif i < 150:  # Sideways market
            price_change = current_price * (0.0005 if i % 2 == 0 else -0.0005)  # Oscillating
            volatility = 0.005  # Very low volatility
        else:  # Volatile market
            price_change = current_price * (0.005 if i % 3 == 0 else -0.004)  # Large swings
            volatility = 0.025  # High volatility
        
        # Calculate OHLCV
        open_price = current_price
        high_price = current_price + abs(price_change) + (current_price * volatility)
        low_price = current_price - abs(price_change) - (current_price * volatility)
        close_price = current_price + price_change
        volume = 1000 + (i * 10)  # Increasing volume trend
        
        # Ensure prices are realistic
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        
        candle = {
            "timestamp": timestamp,
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": round(volume, 2)
        }
        
        test_data.append(candle)
        current_price = close_price
    
    return test_data

def test_regime_detection():
    """Test the market regime detection system"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    logger.info("Starting safe test of market regime detection system...")
    
    try:
        # Import the regime detector
        from market_analysis import MarketRegimeDetector
        
        # Create test data
        logger.info("Creating synthetic test market data...")
        test_data = create_test_market_data()
        logger.info(f"Created {len(test_data)} test candles")
        
        # Initialize regime detector
        logger.info("Initializing market regime detector...")
        detector = MarketRegimeDetector(lookback_periods=100)
        
        # Test regime detection on test data
        logger.info("Testing regime detection on synthetic data...")
        
        # Test with different segments of data
        test_segments = [
            ("Bull Market Segment", test_data[:50]),
            ("Bear Market Segment", test_data[50:100]),
            ("Sideways Market Segment", test_data[100:150]),
            ("Volatile Market Segment", test_data[150:])
        ]
        
        results = {}
        
        for segment_name, segment_data in test_segments:
            logger.info(f"Testing {segment_name}...")
            
            # Detect regime for this segment
            regime_metrics = detector.detect_regime(segment_data)
            
            results[segment_name] = {
                "regime": regime_metrics.regime.value,
                "confidence": regime_metrics.confidence,
                "trend_strength": regime_metrics.trend_strength,
                "volatility": regime_metrics.volatility,
                "volume_trend": regime_metrics.volume_trend,
                "momentum": regime_metrics.momentum
            }
            
            logger.info(f"  Detected regime: {regime_metrics.regime.value}")
            logger.info(f"  Confidence: {regime_metrics.confidence:.3f}")
            logger.info(f"  Trend strength: {regime_metrics.trend_strength:.3f}")
            logger.info(f"  Volatility: {regime_metrics.volatility:.3f}")
        
        # Test regime summary
        logger.info("Testing regime summary...")
        summary = detector.get_regime_summary()
        
        # Print test results
        print("\n" + "="*60)
        print("MARKET REGIME DETECTION TEST RESULTS")
        print("="*60)
        
        for segment_name, result in results.items():
            print(f"\n{segment_name}:")
            print(f"  Regime: {result['regime']}")
            print(f"  Confidence: {result['confidence']:.3f}")
            print(f"  Trend Strength: {result['trend_strength']:.3f}")
            print(f"  Volatility: {result['volatility']:.3f}")
            print(f"  Volume Trend: {result['volume_trend']:.3f}")
            print(f"  Momentum: {result['momentum']:.3f}")
        
        print(f"\nPerformance Summary:")
        print(f"  Total Detections: {summary.get('performance', {}).get('total_detections', 0)}")
        print(f"  Regime Changes: {summary.get('performance', {}).get('regime_changes', 0)}")
        print(f"  Average Confidence: {summary.get('performance', {}).get('avg_confidence', 0):.3f}")
        
        print("="*60)
        
        # Validate results
        validation_passed = True
        
        # Check if bull market was detected in first segment
        if results["Bull Market Segment"]["regime"] != "bull":
            logger.warning("Bull market segment not correctly identified as bull")
            validation_passed = False
        
        # Check if bear market was detected in second segment
        if results["Bear Market Segment"]["regime"] != "bear":
            logger.warning("Bear market segment not correctly identified as bear")
            validation_passed = False
        
        # Check if sideways market was detected in third segment
        if results["Sideways Market Segment"]["regime"] != "sideways":
            logger.warning("Sideways market segment not correctly identified as sideways")
            validation_passed = False
        
        # Check if volatile market was detected in fourth segment
        if results["Volatile Market Segment"]["regime"] != "volatile":
            logger.warning("Volatile market segment not correctly identified as volatile")
            validation_passed = False
        
        if validation_passed:
            logger.info("All regime detection tests passed!")
            return {"status": "success", "message": "All tests passed", "results": results}
        else:
            logger.warning("Some regime detection tests failed")
            return {"status": "warning", "message": "Some tests failed", "results": results}
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Run the test
    result = test_regime_detection()
    
    # Exit with appropriate code
    if result.get('status') == 'success':
        sys.exit(0)
    elif result.get('status') == 'warning':
        sys.exit(1)
    else:
        sys.exit(2)
