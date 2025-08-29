#!/usr/bin/env python3
"""
Main entry point for the Trading Bot System
This file serves as the primary entry point for running the trading bot
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

def main():
    """Main entry point for the trading bot system"""
    try:
        # Import and run the bot
        from bot.bot_main import main as bot_main
        print("🚀 Starting Trading Bot System...")
        bot_main()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all dependencies are installed and the virtual environment is activated.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting trading bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
