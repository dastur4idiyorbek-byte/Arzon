"""ARZON 2.0 migration cleanup note."""

# This script is intentionally disabled because ARZON 2.0 removed legacy
# CoinHarakati, referral balance, and pending-store-balance models.
# Do not add or call this script against a live database.

if __name__ == "__main__":
    raise SystemExit("demo_tozalash.py is disabled for ARZON 2.0")
