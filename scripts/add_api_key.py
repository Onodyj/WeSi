#!/usr/bin/env python3
"""
CLI tool for managing WeSi API keys.
Usage: python scripts/add_api_key.py --key <api_key> --owner <owner_name>
"""

import sys
import os
import argparse
import secrets

# Add parent directory to path to import data module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.db import add_api_key, list_api_keys, deactivate_api_key, get_api_key


def generate_api_key(length: int = 32) -> str:
    """
    Generate a secure random API key.

    Args:
        length: Number of random bytes to generate (default: 32 bytes)
                The resulting hex string will be 2*length characters long

    Returns:
        Hex-encoded random string (64 characters for default length of 32 bytes)
    """
    return secrets.token_hex(length)


def main():
    """Main entry point for the API key management CLI."""
    parser = argparse.ArgumentParser(
        description="Manage WeSi API keys",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add a new API key (auto-generated)
  python scripts/add_api_key.py --owner "John Doe"

  # Add a specific API key
  python scripts/add_api_key.py --key my-secret-key-123 --owner "John Doe"

  # List all API keys
  python scripts/add_api_key.py --list

  # Deactivate an API key
  python scripts/add_api_key.py --deactivate mykey123

  # Check if an API key exists
  python scripts/add_api_key.py --check mykey123

  # Generate a new key without adding it
  python scripts/add_api_key.py --generate
        """
    )

    parser.add_argument("--key", type=str, help="API key to add (auto-generated if not provided)")
    parser.add_argument("--owner", type=str, help="Owner/name of the API key holder")
    parser.add_argument("--list", action="store_true", help="List all existing API keys")
    parser.add_argument("--deactivate", type=str, metavar="KEY", help="Deactivate an API key")
    parser.add_argument("--check", type=str, metavar="KEY", help="Check if an API key is valid")
    parser.add_argument("--generate", action="store_true", help="Generate a new API key without adding it")

    args = parser.parse_args()

    # List keys if requested
    if args.list:
        keys = list_api_keys()
        if not keys:
            print("No API keys found.")
            return 0

        print(f"\n{'Key (masked)':<40} {'Owner':<20} {'Active':<10} {'Created At'}")
        print("-" * 90)
        for key_info in keys:
            active_status = "Yes" if key_info['active'] else "No"
            # Mask the API key, showing only the first 8 and last 4 characters
            key = key_info['key']
            masked_key = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else f"{key[:4]}...{key[-4:]}"
            # Note: only non-sensitive metadata (owner, created_at) is logged in plaintext;
            # the actual API key value is masked above.
            owner = key_info['owner']
            created_at = key_info['created_at']
            print(f"{masked_key:<40} {owner:<20} {active_status:<10} {created_at}")
        print()
        return 0

    # Deactivate API key
    if args.deactivate:
        if deactivate_api_key(args.deactivate):
            print(f"✅ API key deactivated successfully.")
        else:
            print(f"❌ API key not found.", file=sys.stderr)
            return 1
        return 0

    # Check API key
    if args.check:
        key_data = get_api_key(args.check)
        if key_data:
            print(f"✅ API key is valid")
            print(f"   Owner: {key_data['owner']}")
            print(f"   Created: {key_data['created_at']}")
        else:
            print(f"❌ API key is invalid or inactive")
            return 1
        return 0

    # Generate API key only
    if args.generate:
        new_key = generate_api_key()
        print(f"Generated API key: {new_key}")
        return 0

    # Add API key
    if args.owner:
        # Generate key if not provided
        key = args.key if args.key else generate_api_key()

        success = add_api_key(key, args.owner)
        if success:
            print(f"✅ API key added successfully!")
            print(f"   Key: {key}")
            print(f"   Owner: {args.owner}")
            return 0
        else:
            print(f"❌ Failed to add API key. Key may already exist.", file=sys.stderr)
            return 1

    # No valid action specified
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
