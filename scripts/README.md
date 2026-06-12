# WeSi Scripts

This directory contains command-line tools for managing WeSi.

## API Key Management (`add_api_key.py`)

CLI tool for managing API keys in the WeSi database.

### Usage

```bash
# Add a new API key (auto-generated)
python scripts/add_api_key.py --owner "John Doe"

# Add a specific API key
python scripts/add_api_key.py --key mykey123 --owner "John Doe"

# List all active API keys
python scripts/add_api_key.py --list

# Deactivate an API key
python scripts/add_api_key.py --deactivate mykey123

# Check if an API key is valid
python scripts/add_api_key.py --check mykey123

# Generate a new API key without adding it to the database
python scripts/add_api_key.py --generate
```

### Options

- `--key KEY`: Specify a custom API key to add (if not provided, one will be auto-generated)
- `--owner OWNER`: Owner/description of the API key (required when adding)
- `--list`: List all active API keys in a formatted table
- `--deactivate KEY`: Deactivate (soft delete) an API key
- `--check KEY`: Check if an API key is valid and active
- `--generate`: Generate a secure random API key without adding it to the database

### Examples

**Creating API keys:**
```bash
# Auto-generated key
$ python scripts/add_api_key.py --owner "Production Server"
✅ API key added successfully!
   Key: a4f2c8e9d1b7f3a5c2e8d9b1f4a7c3e2d8f1b9a4c7e3d2f8b1a9c4e7d3f2b8a1
   Owner: Production Server

# Custom key
$ python scripts/add_api_key.py --key prod-key-2024 --owner "Production Server"
✅ API key added successfully!
   Key: prod-key-2024
   Owner: Production Server
```

**Listing API keys:**
```bash
$ python scripts/add_api_key.py --list
Key                                      Owner                          Created At                Active
----------------------------------------------------------------------------------------------------
a4f2c8e9d1b7f3a5c2e8d9b1f4a7c3e2... Production Server              2024-01-15T10:30:00       Yes
prod-key-2024                            Production Server              2024-01-15T10:35:00       Yes
```

**Checking API keys:**
```bash
$ python scripts/add_api_key.py --check prod-key-2024
✅ API key is valid
   Owner: Production Server
   Created: 2024-01-15T10:35:00

$ python scripts/add_api_key.py --check invalid-key
❌ API key is invalid or inactive
```

**Deactivating API keys:**
```bash
$ python scripts/add_api_key.py --deactivate prod-key-2024
✅ API key 'prod-key-2024' has been deactivated.
```

**Generating keys:**
```bash
$ python scripts/add_api_key.py --generate
Generated API key: f8e3d2c1b9a8f7e6d5c4b3a2f1e9d8c7b6a5f4e3d2c1b9a8f7e6d5c4b3a2f1e9
```

### Security Notes

- Generated API keys use `secrets.token_hex()` for cryptographically secure random generation
- Default key length is 32 bytes (64 hexadecimal characters)
- Keys are stored in plaintext in the database for lookup
- The `--list` command displays full API keys - use with caution in shared environments
- Deactivated keys cannot be reactivated; create new keys instead

### Exit Codes

- `0`: Success
- `1`: Error (key not found, duplicate key, invalid operation, etc.)
