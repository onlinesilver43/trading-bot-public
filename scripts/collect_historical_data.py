#!/usr/bin/env python3
"""
Comprehensive Historical Data Collection Script
Collects all required historical data for BTCUSDT and ETHUSDT across multiple timeframes.
"""

import subprocess
import json
import time
import os
from datetime import datetime

def run_ssh_command(command):
    """Run SSH command and return output"""
    try:
        result = subprocess.run(
            f'sshpass -f ~/.ssh/tb_pw ssh tb "{command}"',
            shell=True, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"SSH command failed: {e}")
        return None

def check_current_data():
    """Check current data collection status"""
    print("🔍 Checking current data collection status...")
    
    manifest = run_ssh_command("cat /srv/trading-bots/history/manifest.json | jq '.'")
    if manifest:
        try:
            data = json.loads(manifest)
            print(f"📊 Current data: {data.get('statistics', {})}")
            return data
        except json.JSONDecodeError:
            print("❌ Failed to parse manifest")
    
    return None

def collect_data_for_symbol_interval(symbol, interval, start_date="2020-01", end_date="2025-08"):
    """Collect data for a specific symbol and interval"""
    print(f"📥 Collecting {symbol} {interval} data from {start_date} to {end_date}...")
    
    command = f"""cd /srv/trading-bots/history_fetcher && \
docker run --rm -v /srv/trading-bots/history:/app/history \
history-fetcher-fixed python fetch.py \
--symbol {symbol} --interval {interval} \
--from {start_date} --to {end_date}"""
    
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(
            f'sshpass -f ~/.ssh/tb_pw ssh tb "{command}"',
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✅ Successfully collected {symbol} {interval} data")
            return True
        else:
            print(f"❌ Failed to collect {symbol} {interval} data")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Exception during {symbol} {interval} collection: {e}")
        return False

def update_manifest():
    """Update the manifest file"""
    print("🔄 Updating manifest...")
    
    # Run the manifest update command
    command = """cd /srv/trading-bots/history_fetcher && \
docker run --rm -v /srv/trading-bots/history:/app/history \
history-fetcher-fixed python -c "
import json
import os
from datetime import datetime

def update_manifest():
    manifest_path = '/app/history/manifest.json'
    
    # Scan for all files
    data = {'created': datetime.now().isoformat(), 'last_updated': datetime.now().isoformat(), 'data': {}}
    statistics = {'total_files': 0, 'total_size_bytes': 0, 'symbols': {}, 'intervals': {}}
    
    # Scan parquet directory
    parquet_dir = '/app/history/parquet'
    if os.path.exists(parquet_dir):
        for symbol_dir in os.listdir(parquet_dir):
            symbol_path = os.path.join(parquet_dir, symbol_dir)
            if os.path.isdir(symbol_path):
                data['data'][symbol_dir] = {}
                statistics['symbols'][symbol_dir] = 0
                
                for interval_dir in os.listdir(symbol_path):
                    interval_path = os.path.join(symbol_path, interval_dir)
                    if os.path.isdir(interval_path):
                        data['data'][symbol_dir][interval_dir] = []
                        if interval_dir not in statistics['intervals']:
                            statistics['intervals'][interval_dir] = 0
                        
                        # Scan year-month directories
                        for year_dir in os.listdir(interval_path):
                            year_path = os.path.join(interval_path, year_dir)
                            if os.path.isdir(year_path):
                                for filename in os.listdir(year_path):
                                    if filename.endswith('.parquet'):
                                        file_path = os.path.join(year_path, filename)
                                        file_size = os.path.getsize(file_path)
                                        
                                        file_info = {
                                            'filename': filename,
                                            'file_type': 'parquet',
                                            'date': year_dir,
                                            'size_bytes': file_size,
                                            'parquet_path': file_path,
                                            'downloaded_at': datetime.now().isoformat()
                                        }
                                        
                                        data['data'][symbol_dir][interval_dir].append(file_info)
                                        statistics['total_files'] += 1
                                        statistics['total_size_bytes'] += file_size
                                        statistics['symbols'][symbol_dir] += 1
                                        statistics['intervals'][interval_dir] += 1
    
    # Write manifest
    manifest_data = {
        'created': data['created'],
        'last_updated': data['last_updated'],
        'data': data['data'],
        'statistics': statistics
    }
    
    with open(manifest_path, 'w') as f:
        json.dump(manifest_data, f, indent=2)
    
    print(f'Manifest updated: {statistics}')

update_manifest()
" """
    
    try:
        result = subprocess.run(
            f'sshpass -f ~/.ssh/tb_pw ssh tb "{command}"',
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0:
            print("✅ Manifest updated successfully")
            return True
        else:
            print(f"❌ Failed to update manifest: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Exception updating manifest: {e}")
        return False

def main():
    """Main data collection process"""
    print("🚀 Starting comprehensive historical data collection...")
    print("=" * 60)
    
    # Data collection plan
    collection_plan = [
        ("BTCUSDT", "1h"),
        ("BTCUSDT", "5m"), 
        ("ETHUSDT", "1h"),
        ("ETHUSDT", "5m")
    ]
    
    # Check current status
    current_data = check_current_data()
    
    # Collect data for each symbol/interval combination
    successful_collections = 0
    total_collections = len(collection_plan)
    
    for symbol, interval in collection_plan:
        print(f"\n{'='*40}")
        print(f"📊 Collection {successful_collections + 1}/{total_collections}: {symbol} {interval}")
        print(f"{'='*40}")
        
        if collect_data_for_symbol_interval(symbol, interval):
            successful_collections += 1
            print(f"✅ {symbol} {interval} collection completed")
        else:
            print(f"❌ {symbol} {interval} collection failed")
        
        # Update manifest after each collection
        update_manifest()
        
        # Brief pause between collections
        time.sleep(2)
    
    # Final status check
    print(f"\n{'='*60}")
    print("🎯 FINAL DATA COLLECTION SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successful collections: {successful_collections}/{total_collections}")
    
    final_data = check_current_data()
    if final_data:
        stats = final_data.get('statistics', {})
        print(f"📊 Total files collected: {stats.get('total_files', 0)}")
        print(f"📊 Total size: {stats.get('total_size_bytes', 0)} bytes")
        print(f"📊 Symbols: {stats.get('symbols', {})}")
        print(f"📊 Intervals: {stats.get('intervals', {})}")
    
    print(f"\n🎉 Data collection process completed at {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()
