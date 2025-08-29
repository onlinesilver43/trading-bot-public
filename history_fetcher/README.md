# History Fetcher System

## Overview

The History Fetcher is a comprehensive system for downloading, processing, and managing historical cryptocurrency trading data from Binance Vision. It's designed to support the unlimited scaling trading system by providing high-quality historical data for strategy backtesting and market condition analysis.

## Features

- **Multi-Symbol Support**: BTCUSDT, ETHUSDT, BNBUSDT, ADAUSDT, SOLUSDT
- **Multiple Timeframes**: 1m, 5m, 15m, 1h, 4h, 1d
- **Data Types**: Klines (OHLCV), Trades, Aggregated Trades
- **Format Conversion**: Automatic CSV to Parquet conversion for optimal storage
- **Manifest Management**: Comprehensive tracking of downloaded data
- **UI Integration**: Web dashboard for monitoring and management
- **GitHub Actions**: Automated deployment and execution

## Architecture

```
history_fetcher/
├── fetch.py              # Main data fetching script
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container configuration
└── README.md            # This file

/srv/trading-bots/history/  # Data storage (on server)
├── raw/                    # Raw ZIP files
├── csv/                    # Extracted CSV files
├── parquet/                # Processed Parquet files
└── manifest.json           # Data inventory
```

## Data Structure

### Raw Data (ZIP)
- Monthly ZIP files from Binance Vision
- Organized by symbol, interval, and date
- Example: `BTCUSDT-5m-2024-01.zip`

### CSV Files
- Extracted from ZIP files
- Standard OHLCV format
- Columns: timestamp, open, high, low, close, volume, close_time, quote_volume, trades, taker_buy_base, taker_buy_quote, ignore

### Parquet Files
- Optimized columnar format
- Partitioned by symbol/interval/date
- Compressed with Snappy for fast access
- Ideal for pandas analysis

## Usage

### Command Line

```bash
# Basic usage
python fetch.py --symbol BTCUSDT --interval 5m --from 2019-01 --to 2025-08

# Force re-download
python fetch.py --symbol ETHUSDT --interval 1h --from 2020-01 --to 2025-08 --force

# Fill gaps with daily data
python fetch.py --symbol BNBUSDT --interval 4h --from 2021-01 --to 2025-08 --fill-daily
```

### GitHub Actions

1. Go to GitHub Actions → "History Fetch (On-Demand)"
2. Click "Run workflow"
3. Configure parameters:
   - **Symbol**: Trading pair (e.g., BTCUSDT)
   - **Interval**: Timeframe (e.g., 5m)
   - **From Date**: Start date (YYYY-MM)
   - **To Date**: End date (YYYY-MM)
   - **Fill Daily**: Add daily data for gaps
   - **Force**: Re-download existing files

### Docker

```bash
# Build image
docker build -t history-fetcher .

# Run with volume mount
docker run --rm -v /srv/trading-bots/history:/srv/trading-bots/history \
  history-fetcher:latest \
  --symbol BTCUSDT --interval 5m --from 2019-01 --to 2025-08
```

## API Endpoints

### History Management
- `GET /api/history/manifest` - Get data inventory
- `GET /api/history/status` - Get system status
- `GET /api/history/symbols/{symbol}` - Get symbol details

### Web Interface
- `GET /history` - History management dashboard

## Configuration

### Environment Variables
- `HISTORY_BASE_DIR`: Base directory for data storage (default: `/srv/trading-bots/history`)

### Supported Symbols
- BTCUSDT (Bitcoin)
- ETHUSDT (Ethereum)
- BNBUSDT (Binance Coin)
- ADAUSDT (Cardano)
- SOLUSDT (Solana)

### Supported Intervals
- 1m (1 minute)
- 5m (5 minutes)
- 15m (15 minutes)
- 1h (1 hour)
- 4h (4 hours)
- 1d (1 day)

## Data Sources

### Binance Vision
- **Base URL**: https://data.binance.vision/api/data
- **Data Types**:
  - Klines: `https://data.binance.vision/api/data/klines/{symbol}/{interval}/{filename}`
  - Trades: `https://data.binance.vision/api/data/trades/{symbol}/{filename}`
  - AggTrades: `https://data.binance.vision/api/data/aggTrades/{symbol}/{filename}`

### File Naming Convention
- Format: `{symbol}-{interval}-{YYYY-MM}.zip`
- Example: `BTCUSDT-5m-2024-01.zip`

## Performance

### Storage Optimization
- Raw ZIP files cleaned up after 30 days
- Parquet compression reduces storage by ~70%
- Partitioned structure enables fast queries

### Processing Speed
- Parallel download and processing
- Progress bars for monitoring
- Automatic error handling and retry

## Monitoring

### Logs
- File: `history_fetcher.log`
- Console output with progress bars
- Error logging with stack traces

### Metrics
- Total files downloaded
- Total storage used
- Per-symbol statistics
- Processing timestamps

## Integration

### Trading Bot
- Historical data available for strategy backtesting
- Market condition analysis
- Performance optimization

### UI Dashboard
- Real-time status monitoring
- Data inventory management
- Download progress tracking

## Maintenance

### Cleanup
- Automatic cleanup of old raw files
- Manifest validation
- Storage space monitoring

### Updates
- New symbols can be added to `symbols` list
- New intervals supported by Binance Vision
- Regular dependency updates

## Troubleshooting

### Common Issues

1. **Download Failures**
   - Check internet connectivity
   - Verify Binance Vision API status
   - Check available disk space

2. **Processing Errors**
   - Verify Python dependencies
   - Check file permissions
   - Review error logs

3. **Storage Issues**
   - Monitor disk usage
   - Clean up old files
   - Verify directory permissions

### Debug Mode
```bash
# Enable verbose logging
export PYTHONPATH=/app
python fetch.py --help
```

## Future Enhancements

- **Additional Exchanges**: Coinbase, Kraken, etc.
- **Real-time Updates**: WebSocket integration
- **Advanced Analytics**: Built-in technical indicators
- **Machine Learning**: Automated pattern recognition
- **Cloud Storage**: S3, GCS integration

## Support

For issues or questions:
1. Check the logs: `history_fetcher.log`
2. Review GitHub Actions workflow runs
3. Check system resources and disk space
4. Verify network connectivity to Binance Vision

## License

This system is part of the unlimited scaling trading bot project.
