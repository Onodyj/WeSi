#!/usr/bin/env python3
"""
CLI tool for managing WeSi API keys.
Usage: python scripts/add_api_key.py --key <api_key> --owner <owner_name>
"""

import sys
import os
import argparse

# Add parent directory to path to import data module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.db import init_db, add_api_key, list_api_keys


def main():
    """Main entry point for the API key management CLI."""
    parser = argparse.ArgumentParser(
        description="Manage WeSi API keys",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add a new API key
  python scripts/add_api_key.py --key my-secret-key-123 --owner "John Doe"
  
  # List all API keys
  python scripts/add_api_key.py --list
        """
    )
    
    parser.add_argument(
        "--key",
        type=str,
        help="API key to add"
    )
    
    parser.add_argument(
        "--owner",
        type=str,
        help="Owner/name of the API key holder"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all existing API keys"
    )
    
    args = parser.parse_args()
    
    # Initialize database
    init_db()
    
    # List keys if requested
    if args.list:
        keys = list_api_keys()
        if not keys:
            print("No API keys found.")
            return 0
        
        print(f"\n{'Key':<40} {'Owner':<20} {'Active':<10} {'Created At'}")
        print("-" * 90)
        for key_info in keys:
            active_status = "Yes" if key_info['active'] else "No"
            print(f"{key_info['key']:<40} {key_info['owner']:<20} {active_status:<10} {key_info['created_at']}")
        print()
        return 0
    
    # Validate arguments for adding a key
    if not args.key or not args.owner:
        parser.error("--key and --owner are required (or use --list to list keys)")
    
    # Add the API key
    success = add_api_key(args.key, args.owner)
    
    if success:
        print(f"✅ API key added successfully!")
        print(f"   Key: {args.key}")
        print(f"   Owner: {args.owner}")
        return 0
    else:
        print(f"❌ Failed to add API key. Key may already exist.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
