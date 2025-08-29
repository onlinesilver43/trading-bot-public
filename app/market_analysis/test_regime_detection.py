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
        
        # Test with the full dataset first to ensure we have enough data
        logger.info("Testing regime detection on full dataset...")
        full_regime_metrics = detector.detect_regime(test_data)
        
        logger.info(f"Full dataset regime: {full_regime_metrics.regime.value}")
        logger.info(f"Full dataset confidence: {full_regime_metrics.confidence:.3f}")
        
        # Test with different segments of data (using overlapping windows to ensure enough data)
        test_segments = [
            ("Early Segment (0-100)", test_data[:100]),
            ("Middle Segment (50-150)", test_data[50:150]),
            ("Late Segment (100-200)", test_data[100:])
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
        
        print(f"\nFull Dataset:")
        print(f"  Regime: {full_regime_metrics.regime.value}")
        print(f"  Confidence: {full_regime_metrics.confidence:.3f}")
        print(f"  Trend Strength: {full_regime_metrics.trend_strength:.3f}")
        print(f"  Volatility: {full_regime_metrics.volatility:.3f}")
        print(f"  Volume Trend: {full_regime_metrics.volume_trend:.3f}")
        print(f"  Momentum: {full_regime_metrics.momentum:.3f}")
        
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
        
        # Check if full dataset was processed successfully
        if full_regime_metrics.regime.value == 'unknown':
            logger.warning("Full dataset regime detection failed")
            validation_passed = False
        
        # Check if we have at least some successful detections
        successful_detections = sum(1 for result in results.values() if result['regime'] != 'unknown')
        if successful_detections == 0:
            logger.warning("No successful regime detections in any segment")
            validation_passed = False
        
        if validation_passed:
            logger.info("Regime detection system working correctly!")
            return {"status": "success", "message": "System working correctly", "results": results}
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
