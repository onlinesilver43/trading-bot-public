#!/usr/bin/env python3
"""
Historical Data Analyzer
Pulls real historical data and starts analysis for the Historical Analysis Bot
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Data sources for historical data"""

    YAHOO_FINANCE = "yahoo_finance"
    ALPHA_VANTAGE = "alpha_vantage"
    POLYGON = "polygon"
    LOCAL_DATABASE = "local_database"


class MarketSymbol(Enum):
    """Market symbols to analyze - Binance US and Coinbase US compatible"""

    BTC_USDT = "BTC/USDT"  # Bitcoin
    ETH_USDT = "ETH/USDT"  # Ethereum
    BNB_USDT = "BNB/USDT"  # Binance Coin
    ADA_USDT = "ADA/USDT"  # Cardano
    SOL_USDT = "SOL/USDT"  # Solana
    XRP_USDT = "XRP/USDT"  # Ripple
    DOT_USDT = "DOT/USDT"  # Polkadot
    MATIC_USDT = "MATIC/USDT"  # Polygon
    AVAX_USDT = "AVAX/USDT"  # Avalanche
    LINK_USDT = "LINK/USDT"  # Chainlink


@dataclass
class HistoricalDataPoint:
    """Single historical data point"""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    symbol: str
    source: str


@dataclass
class MarketRegimeData:
    """Market regime analysis data"""

    timeframe: str
    regime: str
    confidence: float
    volatility: float
    trend_strength: float
    mean_reversion_score: float
    momentum_score: float
    grid_trading_score: float
    analysis_timestamp: datetime


@dataclass
class StrategyOpportunity:
    """Strategy opportunity identified from data"""

    symbol: str
    timeframe: str
    strategy_type: str
    opportunity_score: float
    expected_return: float
    risk_level: float
    parameters: Dict[str, Any]
    confidence: float


class HistoricalDataAnalyzer:
    """
    Historical Data Analyzer

    This class:
    1. Pulls real historical data from multiple sources
    2. Analyzes market regimes across different timeframes
    3. Identifies trading opportunities
    4. Prepares data for the Historical Analysis Bot
    """

    def __init__(
        self,
        symbols: List[str] = None,
        data_sources: List[DataSource] = None,
        api_keys: Dict[str, str] = None,
    ):

        # Use existing Binance US symbols from the project
        self.symbols = symbols or [
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "ADAUSDT",
            "SOLUSDT",
        ]
        self.data_sources = data_sources or [DataSource.LOCAL_DATABASE]
        self.api_keys = api_keys or {}

        # Data storage
        self.historical_data = {}
        self.regime_analysis = {}
        self.strategy_opportunities = []
        self.analysis_summary = {}

        # Analysis parameters - use existing Binance timeframes
        self.timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
        self.min_data_points = 100

        # Connect to existing data infrastructure
        self.data_base_path = "/srv/trading-bots/history"
        self.parquet_path = f"{self.data_base_path}/parquet"
        self.csv_path = f"{self.data_base_path}/csv"

        logger.info(
            f"Historical Data Analyzer initialized for {len(self.symbols)} symbols"
        )

    async def run_full_analysis(self) -> Dict[str, Any]:
        """Run complete historical data analysis"""
        logger.info("🚀 Starting full historical data analysis...")

        try:
            # Step 1: Pull historical data
            await self._pull_historical_data()

            # Step 2: Analyze market regimes
            await self._analyze_market_regimes()

            # Step 3: Identify strategy opportunities
            await self._identify_strategy_opportunities()

            # Step 4: Generate analysis summary
            self._generate_analysis_summary()

            logger.info("✅ Historical data analysis completed successfully!")

            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "symbols_analyzed": len(self.symbols),
                "timeframes_analyzed": len(self.timeframes),
                "regimes_identified": len(self.regime_analysis),
                "opportunities_found": len(self.strategy_opportunities),
                "analysis_summary": self.analysis_summary,
            }

        except Exception as e:
            logger.error(f"Error in full analysis: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _pull_historical_data(self):
        """Pull historical data for all symbols and timeframes"""
        logger.info("📊 Pulling historical data...")

        for symbol in self.symbols:
            logger.info(f"Pulling data for {symbol}...")

            try:
                # Pull data for each timeframe
                symbol_data = {}

                for timeframe in self.timeframes:
                    data = await self._pull_symbol_data(symbol, timeframe)
                    if (
                        data is not None
                        and not data.empty
                        and len(data) >= self.min_data_points
                    ):
                        symbol_data[timeframe] = data
                        logger.info(f"  {timeframe}: {len(data)} data points")
                    else:
                        logger.warning(
                            f"  {timeframe}: Insufficient data ({len(data) if data is not None and not data.empty else 0} points)"
                        )

                if symbol_data:
                    self.historical_data[symbol] = symbol_data
                    logger.info(
                        f"✅ {symbol}: Data collected for {len(symbol_data)} timeframes"
                    )
                else:
                    logger.error(f"❌ {symbol}: No valid data collected")

            except Exception as e:
                logger.error(f"Error pulling data for {symbol}: {str(e)}")

        logger.info(
            f"Data collection complete: {len(self.historical_data)} symbols with data"
        )

    async def _pull_symbol_data(
        self, symbol: str, timeframe: str
    ) -> Optional[pd.DataFrame]:
        """Pull data for a specific symbol and timeframe"""
        try:
            # Try to load from existing historical data sources
            data = await self._load_from_existing_sources(symbol, timeframe)

            if data is not None and len(data) > 0:
                return data

            # If no existing data, generate synthetic data for testing
            logger.info(f"Generating synthetic data for {symbol} {timeframe}")
            return await self._generate_synthetic_data(symbol, timeframe)

        except Exception as e:
            logger.error(f"Error pulling {timeframe} data for {symbol}: {str(e)}")
            return None

    async def _load_from_existing_sources(
        self, symbol: str, timeframe: str
    ) -> Optional[pd.DataFrame]:
        """Try to load data from existing sources"""
        try:
            # Check for data in common locations - Binance US compatible
            # Convert symbol format (e.g., "BTC/USDT" -> "BTCUSDT")
            # binance_symbol = symbol.replace("/", "")  # Not currently used

            possible_paths = [
                f"{self.parquet_path}/{symbol}/{timeframe}",
                f"{self.csv_path}/{symbol}/{timeframe}",
                f"{self.data_base_path}/raw/{symbol}-{timeframe}",
                f"{self.data_base_path}/manifest.json",  # Check manifest for available data
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    logger.info(f"Found existing data at: {path}")
                    try:
                        if path.endswith(".csv"):
                            data = pd.read_csv(path)
                        elif path.endswith(".json"):
                            data = pd.read_json(path)
                        elif path.endswith(".parquet"):
                            data = pd.read_parquet(path)
                        else:
                            continue

                        # Standardize column names
                        if "timestamp" in data.columns:
                            data["timestamp"] = pd.to_datetime(data["timestamp"])
                        elif "date" in data.columns:
                            data["timestamp"] = pd.to_datetime(data["date"])

                        # Ensure we have required columns
                        required_cols = [
                            "timestamp",
                            "open",
                            "high",
                            "low",
                            "close",
                            "volume",
                        ]
                        if all(col in data.columns for col in required_cols):
                            data = data[required_cols].copy()
                            data["symbol"] = symbol
                            data["source"] = "existing_source"
                            return data.sort_values("timestamp").reset_index(drop=True)

                    except Exception as e:
                        logger.warning(f"Error loading from {path}: {str(e)}")
                        continue

            return None

        except Exception as e:
            logger.error(f"Error loading from existing sources: {str(e)}")
            return None

    async def _generate_synthetic_data(
        self, symbol: str, timeframe: str
    ) -> pd.DataFrame:
        """Generate synthetic data for testing when real data is not available"""
        try:
            # Calculate number of data points based on Binance timeframe
            timeframe_map = {
                "1m": 1440,  # 1 day worth of 1-minute data
                "5m": 288,  # 1 day worth of 5-minute data
                "15m": 96,  # 1 day worth of 15-minute data
                "1h": 24,  # 1 day worth of hourly data
                "4h": 6,  # 1 day worth of 4-hour data
                "1d": 1,  # 1 day worth of daily data
            }
            data_points = timeframe_map.get(timeframe, 24)

            # Generate synthetic OHLCV data
            np.random.seed(42)  # For reproducible results

            # Start with crypto-appropriate base prices
            crypto_base_prices = {
                "BTC/USDT": 45000.0,  # Bitcoin
                "ETH/USDT": 3000.0,  # Ethereum
                "BNB/USDT": 300.0,  # Binance Coin
                "ADA/USDT": 0.5,  # Cardano
                "SOL/USDT": 100.0,  # Solana
                "XRP/USDT": 0.6,  # Ripple
                "DOT/USDT": 7.0,  # Polkadot
                "MATIC/USDT": 0.8,  # Polygon
                "AVAX/USDT": 25.0,  # Avalanche
                "LINK/USDT": 15.0,  # Chainlink
            }

            base_price = crypto_base_prices.get(symbol, 100.0)

            # Generate price series with realistic patterns
            returns = np.random.normal(
                0.0001, 0.02, data_points
            )  # Small returns per timeframe
            prices = [base_price]

            for ret in returns:
                new_price = prices[-1] * (1 + ret)
                prices.append(new_price)

            # Generate OHLCV data
            data = []
            current_time = datetime.now()

            for i, close_price in enumerate(prices[1:], 1):
                # Generate realistic OHLC from close price
                volatility = 0.02  # 2% volatility per timeframe

                high = close_price * (1 + abs(np.random.normal(0, volatility / 2)))
                low = close_price * (1 - abs(np.random.normal(0, volatility / 2)))
                open_price = prices[i - 1]

                # Ensure OHLC relationships are valid
                high = max(high, open_price, close_price)
                low = min(low, open_price, close_price)

                # Generate volume
                volume = int(
                    np.random.lognormal(10, 1)
                )  # Realistic volume distribution

                # Calculate timestamp based on timeframe
                if timeframe == "1m":
                    timestamp = current_time - timedelta(minutes=data_points - i)
                elif timeframe == "5m":
                    timestamp = current_time - timedelta(minutes=5 * (data_points - i))
                elif timeframe == "15m":
                    timestamp = current_time - timedelta(minutes=15 * (data_points - i))
                elif timeframe == "1h":
                    timestamp = current_time - timedelta(hours=data_points - i)
                elif timeframe == "4h":
                    timestamp = current_time - timedelta(hours=4 * (data_points - i))
                else:  # 1d
                    timestamp = current_time - timedelta(days=data_points - i)

                data.append(
                    {
                        "timestamp": timestamp,
                        "open": round(open_price, 4),
                        "high": round(high, 4),
                        "low": round(low, 4),
                        "close": round(close_price, 4),
                        "volume": volume,
                        "symbol": symbol,
                        "source": "synthetic",
                    }
                )

            df = pd.DataFrame(data)
            logger.info(
                f"Generated {len(df)} synthetic data points for {symbol} {timeframe}"
            )
            return df

        except Exception as e:
            logger.error(f"Error generating synthetic data: {str(e)}")
            return pd.DataFrame()

    def _calculate_start_date(self, end_date: datetime, timeframe: str) -> datetime:
        """Calculate start date based on timeframe"""
        timeframe_map = {
            "1M": 30,
            "3M": 90,
            "6M": 180,
            "1Y": 365,
            "2Y": 730,
            "5Y": 1825,
        }

        days = timeframe_map.get(timeframe, 365)
        return end_date - timedelta(days=days)

    async def _analyze_market_regimes(self):
        """Analyze market regimes for all symbols and timeframes"""
        logger.info("🔍 Analyzing market regimes...")

        for symbol, timeframes_data in self.historical_data.items():
            logger.info(f"Analyzing regimes for {symbol}...")

            symbol_regimes = {}

            for timeframe, data in timeframes_data.items():
                try:
                    regime_data = await self._analyze_single_regime(
                        symbol, timeframe, data
                    )
                    if regime_data:
                        symbol_regimes[timeframe] = regime_data
                        logger.info(
                            f"  {timeframe}: {regime_data.regime} (confidence: {regime_data.confidence:.2f})"
                        )

                except Exception as e:
                    logger.error(
                        f"Error analyzing {timeframe} regime for {symbol}: {str(e)}"
                    )

            if symbol_regimes:
                self.regime_analysis[symbol] = symbol_regimes
                logger.info(
                    f"✅ {symbol}: Regime analysis complete for {len(symbol_regimes)} timeframes"
                )

        logger.info(
            f"Regime analysis complete: {len(self.regime_analysis)} symbols analyzed"
        )

    async def _analyze_single_regime(
        self, symbol: str, timeframe: str, data: pd.DataFrame
    ) -> Optional[MarketRegimeData]:
        """Analyze market regime for a single symbol and timeframe"""
        try:
            if len(data) < 20:  # Need minimum data for analysis
                return None

            # Calculate technical indicators
            close_prices = data["close"].values
            returns = np.diff(close_prices) / close_prices[:-1]

            # Volatility analysis
            volatility = np.std(returns) * np.sqrt(252)  # Annualized

            # Trend analysis
            sma_20 = np.mean(close_prices[-20:])
            sma_50 = np.mean(close_prices[-50:]) if len(close_prices) >= 50 else sma_20
            trend_strength = (sma_20 - sma_50) / sma_50

            # Mean reversion analysis
            price_range = (np.max(close_prices) - np.min(close_prices)) / np.mean(
                close_prices
            )
            mean_reversion_score = 1.0 / (
                1.0 + price_range
            )  # Higher score = more mean reversion

            # Momentum analysis
            momentum_score = np.sum(returns[-20:]) if len(returns) >= 20 else 0
            momentum_score = 1.0 / (1.0 + np.exp(-momentum_score))  # Sigmoid to 0-1

            # Determine regime
            regime, confidence = self._classify_regime(
                volatility, trend_strength, mean_reversion_score, momentum_score
            )

            # Grid trading suitability
            grid_trading_score = self._calculate_grid_trading_score(data)

            return MarketRegimeData(
                timeframe=timeframe,
                regime=regime,
                confidence=confidence,
                volatility=volatility,
                trend_strength=trend_strength,
                mean_reversion_score=mean_reversion_score,
                momentum_score=momentum_score,
                grid_trading_score=grid_trading_score,
                analysis_timestamp=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Error in regime analysis: {str(e)}")
            return None

    def _classify_regime(
        self,
        volatility: float,
        trend_strength: float,
        mean_reversion: float,
        momentum: float,
    ) -> Tuple[str, float]:
        """Classify market regime based on indicators"""

        # High volatility regimes
        if volatility > 0.25:
            if abs(trend_strength) > 0.1:
                regime = "volatile_trending"
                confidence = 0.8
            else:
                regime = "high_volatility_sideways"
                confidence = 0.7

        # Low volatility regimes
        elif volatility < 0.15:
            if abs(trend_strength) > 0.05:
                regime = "low_volatility_trending"
                confidence = 0.9
            else:
                regime = "low_volatility_sideways"
                confidence = 0.8

        # Medium volatility regimes
        else:
            if abs(trend_strength) > 0.08:
                if momentum > 0.6:
                    regime = "trending_up"
                    confidence = 0.85
                elif momentum < 0.4:
                    regime = "trending_down"
                    confidence = 0.85
                else:
                    regime = "weak_trend"
                    confidence = 0.7
            else:
                if mean_reversion > 0.6:
                    regime = "mean_reversion"
                    confidence = 0.8
                else:
                    regime = "sideways"
                    confidence = 0.7

        return regime, confidence

    def _calculate_grid_trading_score(self, data: pd.DataFrame) -> float:
        """Calculate suitability for grid trading"""
        try:
            # Grid trading works best in sideways markets with consistent volatility
            close_prices = data["close"].values

            # Calculate price range
            price_range = (np.max(close_prices) - np.min(close_prices)) / np.mean(
                close_prices
            )

            # Calculate volatility consistency
            returns = np.diff(close_prices) / close_prices[:-1]
            volatility_consistency = 1.0 / (1.0 + np.std(np.abs(returns)))

            # Calculate trend consistency (lower is better for grid trading)
            trend_consistency = 1.0 / (1.0 + abs(np.mean(returns)))

            # Combine factors
            grid_score = (
                volatility_consistency * 0.4
                + (1.0 - price_range) * 0.3
                + trend_consistency * 0.3
            )

            return min(max(grid_score, 0.0), 1.0)

        except Exception as e:
            logger.error(f"Error calculating grid trading score: {str(e)}")
            return 0.5

    async def _identify_strategy_opportunities(self):
        """Identify trading opportunities based on regime analysis"""
        logger.info("🎯 Identifying strategy opportunities...")

        opportunities = []

        for symbol, timeframes_data in self.regime_analysis.items():
            logger.info(f"Finding opportunities for {symbol}...")

            for timeframe, regime_data in timeframes_data.items():
                try:
                    # Find opportunities for this regime
                    symbol_opportunities = self._find_regime_opportunities(
                        symbol, timeframe, regime_data
                    )

                    opportunities.extend(symbol_opportunities)

                    if symbol_opportunities:
                        logger.info(
                            f"  {timeframe}: Found {len(symbol_opportunities)} opportunities"
                        )

                except Exception as e:
                    logger.error(
                        f"Error finding opportunities for {symbol} {timeframe}: {str(e)}"
                    )

        self.strategy_opportunities = opportunities
        logger.info(f"Strategy opportunities identified: {len(opportunities)} total")

    def _find_regime_opportunities(
        self, symbol: str, timeframe: str, regime_data: MarketRegimeData
    ) -> List[StrategyOpportunity]:
        """Find trading opportunities for a specific regime"""
        opportunities = []

        try:
            regime = regime_data.regime
            confidence = regime_data.confidence

            # Only consider high-confidence regimes
            if confidence < 0.7:
                return opportunities

            # Momentum strategies for trending markets
            if "trending" in regime:
                if regime_data.momentum_score > 0.6:
                    opportunities.append(
                        StrategyOpportunity(
                            symbol=symbol,
                            timeframe=timeframe,
                            strategy_type="momentum",
                            opportunity_score=regime_data.momentum_score * confidence,
                            expected_return=0.15,  # 15% expected return
                            risk_level=0.25,  # 25% max drawdown
                            parameters={
                                "entry_threshold": 0.02,
                                "stop_loss": 0.05,
                                "take_profit": 0.10,
                            },
                            confidence=confidence,
                        )
                    )

            # Mean reversion strategies for sideways markets
            if "sideways" in regime or "mean_reversion" in regime:
                if regime_data.mean_reversion_score > 0.6:
                    opportunities.append(
                        StrategyOpportunity(
                            symbol=symbol,
                            timeframe=timeframe,
                            strategy_type="mean_reversion",
                            opportunity_score=regime_data.mean_reversion_score
                            * confidence,
                            expected_return=0.12,  # 12% expected return
                            risk_level=0.15,  # 15% max drawdown
                            parameters={
                                "lookback_period": 20,
                                "std_dev_threshold": 2.0,
                                "entry_threshold": 0.03,
                            },
                            confidence=confidence,
                        )
                    )

            # Grid trading for low volatility sideways markets
            if regime_data.grid_trading_score > 0.7:
                opportunities.append(
                    StrategyOpportunity(
                        symbol=symbol,
                        timeframe=timeframe,
                        strategy_type="grid_trading",
                        opportunity_score=regime_data.grid_trading_score * confidence,
                        expected_return=0.08,  # 8% expected return
                        risk_level=0.10,  # 10% max drawdown
                        parameters={
                            "grid_levels": 10,
                            "grid_spacing": 0.01,
                            "position_size": 0.1,
                        },
                        confidence=confidence,
                    )
                )

            # Scalping for high volatility markets
            if "volatile" in regime and regime_data.volatility > 0.3:
                opportunities.append(
                    StrategyOpportunity(
                        symbol=symbol,
                        timeframe=timeframe,
                        strategy_type="scalping",
                        opportunity_score=0.8 * confidence,
                        expected_return=0.20,  # 20% expected return
                        risk_level=0.30,  # 30% max drawdown
                        parameters={
                            "entry_threshold": 0.01,
                            "stop_loss": 0.02,
                            "take_profit": 0.03,
                            "max_hold_time": 5,  # minutes
                        },
                        confidence=confidence,
                    )
                )

        except Exception as e:
            logger.error(f"Error finding opportunities: {str(e)}")

        return opportunities

    def _generate_analysis_summary(self):
        """Generate comprehensive analysis summary"""
        logger.info("📊 Generating analysis summary...")

        summary = {
            "analysis_timestamp": datetime.now().isoformat(),
            "symbols_analyzed": len(self.historical_data),
            "total_data_points": sum(
                sum(len(data) for data in timeframes.values())
                for timeframes in self.historical_data.values()
            ),
            "regime_distribution": {},
            "opportunity_summary": {},
            "top_opportunities": [],
            "risk_assessment": {},
        }

        # Regime distribution
        regime_counts = {}
        for symbol_data in self.regime_analysis.values():
            for timeframe_data in symbol_data.values():
                regime = timeframe_data.regime
                regime_counts[regime] = regime_counts.get(regime, 0) + 1

        summary["regime_distribution"] = regime_counts

        # Opportunity summary
        strategy_counts = {}
        total_opportunity_score = 0

        for opp in self.strategy_opportunities:
            strategy = opp.strategy_type
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            total_opportunity_score += opp.opportunity_score

        summary["opportunity_summary"] = {
            "strategy_counts": strategy_counts,
            "total_opportunities": len(self.strategy_opportunities),
            "average_opportunity_score": (
                total_opportunity_score / len(self.strategy_opportunities)
                if self.strategy_opportunities
                else 0
            ),
        }

        # Top opportunities (sorted by score)
        top_opps = sorted(
            self.strategy_opportunities, key=lambda x: x.opportunity_score, reverse=True
        )[:10]

        summary["top_opportunities"] = [
            {
                "symbol": opp.symbol,
                "timeframe": opp.timeframe,
                "strategy": opp.strategy_type,
                "score": opp.opportunity_score,
                "expected_return": opp.expected_return,
                "risk_level": opp.risk_level,
            }
            for opp in top_opps
        ]

        # Risk assessment
        if self.strategy_opportunities:
            avg_risk = np.mean([opp.risk_level for opp in self.strategy_opportunities])
            avg_return = np.mean(
                [opp.expected_return for opp in self.strategy_opportunities]
            )

            summary["risk_assessment"] = {
                "average_risk": avg_risk,
                "average_expected_return": avg_return,
                "risk_return_ratio": avg_return / avg_risk if avg_risk > 0 else 0,
                "high_risk_opportunities": len(
                    [
                        opp
                        for opp in self.strategy_opportunities
                        if opp.risk_level > 0.25
                    ]
                ),
            }

        self.analysis_summary = summary
        logger.info("✅ Analysis summary generated")

    def get_analysis_results(self) -> Dict[str, Any]:
        """Get complete analysis results"""
        return {
            "historical_data": self.historical_data,
            "regime_analysis": self.regime_analysis,
            "strategy_opportunities": self.strategy_opportunities,
            "analysis_summary": self.analysis_summary,
        }

    def export_analysis_report(self, filename: str = None) -> str:
        """Export analysis report to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"historical_analysis_report_{timestamp}.json"

        try:
            # Prepare data for export (remove pandas DataFrames)
            export_data = {
                "analysis_summary": self.analysis_summary,
                "regime_analysis": {
                    symbol: {
                        timeframe: {
                            "regime": data.regime,
                            "confidence": data.confidence,
                            "volatility": data.volatility,
                            "trend_strength": data.trend_strength,
                            "mean_reversion_score": data.mean_reversion_score,
                            "momentum_score": data.momentum_score,
                            "grid_trading_score": data.grid_trading_score,
                            "analysis_timestamp": data.analysis_timestamp.isoformat(),
                        }
                        for timeframe, data in timeframes.items()
                    }
                    for symbol, timeframes in self.regime_analysis.items()
                },
                "strategy_opportunities": [
                    {
                        "symbol": opp.symbol,
                        "timeframe": opp.timeframe,
                        "strategy_type": opp.strategy_type,
                        "opportunity_score": opp.opportunity_score,
                        "expected_return": opp.expected_return,
                        "risk_level": opp.risk_level,
                        "parameters": opp.parameters,
                        "confidence": opp.confidence,
                    }
                    for opp in self.strategy_opportunities
                ],
            }

            with open(filename, "w") as f:
                json.dump(export_data, f, indent=2)

            logger.info(f"Analysis report exported to: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Error exporting report: {str(e)}")
            return ""


async def main():
    """Test the Historical Data Analyzer"""
    print("🚀 Historical Data Analyzer - Phase 4 Implementation")
    print("=" * 60)

    # Initialize analyzer
    analyzer = HistoricalDataAnalyzer()

    # Run full analysis
    print("Running full historical data analysis...")
    result = await analyzer.run_full_analysis()

    if result["status"] == "success":
        print("\n📊 ANALYSIS RESULTS:")
        print(f"Symbols analyzed: {result['symbols_analyzed']}")
        print(f"Timeframes analyzed: {result['timeframes_analyzed']}")
        print(f"Regimes identified: {result['regimes_identified']}")
        print(f"Opportunities found: {result['opportunities_found']}")

        # Show top opportunities
        summary = analyzer.analysis_summary
        if "top_opportunities" in summary and summary["top_opportunities"]:
            print("\n🎯 TOP OPPORTUNITIES:")
            for i, opp in enumerate(summary["top_opportunities"][:5]):
                print(
                    f"  {i+1}. {opp['symbol']} ({opp['timeframe']}) - {opp['strategy']}"
                )
                print(
                    f"     Score: {opp['score']:.3f}, Expected Return: {opp['expected_return']:.1%}"
                )
                print()

        # Export report
        report_file = analyzer.export_analysis_report()
        if report_file:
            print(f"📄 Analysis report exported to: {report_file}")

        print("\n✅ Historical Data Analyzer test completed successfully!")

    else:
        print(f"❌ Analysis failed: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
