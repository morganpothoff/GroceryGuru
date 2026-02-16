# GroceryGuru

Uses SQLite (no PostgreSQL required). The database file is created automatically at `Database/grocery_guru.db` on first run. Passwords are stored as pbkdf2:sha256 hashes.

## Running
```bash
source Unix.env
python3 Source/GroceryGuru.py
```

The app listens at http://localhost:8000
