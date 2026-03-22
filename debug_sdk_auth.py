import sqlite3
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Explicitly load the .env from the current directory
load_dotenv("/Users/anikchand/Documents/onekey/.env")

def debug_auth():
    encryption_key = os.getenv("ENCRYPTION_KEY")
    platform_key_env = os.getenv("ONEKEY_PLATFORM_API_KEY")
    
    print(f"ENCRYPTION_KEY: {encryption_key}")
    print(f"PLATFORM_KEY_ENV: {platform_key_env}")
    
    if not encryption_key or not platform_key_env:
        print("Missing env vars")
        return

    fernet = Fernet(encryption_key.encode())
    
    conn = sqlite3.connect("/Users/anikchand/Documents/onekey/vault.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, platform_unified_key_encrypted FROM users WHERE id=5")
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print("User 5 not found in DB")
        return
    
    uid, email, encrypted_key = row
    print(f"User in DB: {uid} ({email})")
    print(f"Encrypted Key in DB: {encrypted_key[:20]}...")
    
    try:
        decrypted = fernet.decrypt(encrypted_key.encode()).decode()
        print(f"Decrypted Key from DB: {decrypted}")
        print(f"Matches ENV? {decrypted == platform_key_env}")
        
        if decrypted != platform_key_env:
            print("\n!!! MISMATCH DETECTED !!!")
            print(f"Expected: {platform_key_env}")
            print(f"Actual:   {decrypted}")
    except Exception as e:
        print(f"Decryption failed: {e}")

if __name__ == "__main__":
    debug_auth()
