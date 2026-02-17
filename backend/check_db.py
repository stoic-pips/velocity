import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import get_settings
from database.supabase_sync import SupabaseSync, BotConfigLoadError

def check_db_health():
    print("=" * 60)
    print("  Dunam Velocity – Database Health Check")
    print("=" * 60)
    
    sync = SupabaseSync()
    
    if not sync.is_connected:
        print("[FAIL] Supabase client not connected.")
        return
        
    print("[PASS] Supabase client initialized.")
    
    # Test User ID (you may need to provide one or we check a known one)
    # Since we can't easily guess a valid user_id without auth context, 
    # we can try to list one if RLS allows (unlikely for authenticated),
    # or we ask user to verify with their ID.
    # For a robust check, we might skip specific user check or use a test ID if available.
    
    # Check if table exists (by trying to select limit 1, assuming some public access or service role if configured)
    # The 'service_role' key bypasses RLS, but standard key enforces it.
    # If we are using standard key, we might get empty results for 'select * from bot_configs' if no user inferred.
    
    try:
        # Just check if we can query the table structure (even if empty result due to RLS)
        res = sync._client.table("bot_configs").select("count", count="exact").execute()
        print(f"[PASS] 'bot_configs' table is accessible. Total rows (visible): {res.count}")
    except Exception as e:
        print(f"[FAIL] Error accessing 'bot_configs': {e}")

    print("\n[INFO] To fully verify RLS, ensure you see your data in the dashboard.")
    print("Health check complete.")

if __name__ == "__main__":
    check_db_health()
