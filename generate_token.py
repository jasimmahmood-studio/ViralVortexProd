"""
ViralVortex — YouTube Token Generator
Run this ONCE on your PC/Mac to generate YOUTUBE_TOKEN_B64
Usage: python generate_token.py
"""

import os
import sys
import json
import base64
import pickle


def main():
    print("=" * 60)
    print("🌀 ViralVortex — YouTube Token Generator")
    print("=" * 60)

    # ── Check client_secrets.json ────────────────────────────
    secrets_files = ["client_secrets.json", "client_secret.json", "credentials.json"]
    secrets_file  = next((f for f in secrets_files if os.path.exists(f)), None)

    if not secrets_file:
        print("\n❌ client_secrets.json not found!")
        print("\nTo get it:")
        print("  1. Go to console.cloud.google.com")
        print("  2. APIs & Services → Credentials")
        print("  3. Click your OAuth 2.0 Client ID")
        print("  4. Click 'Download JSON'")
        print("  5. Rename to client_secrets.json")
        print("  6. Put it in the same folder as this script")
        input("\nPress Enter to exit...")
        return

    print(f"\n✅ Found: {secrets_file}")

    # ── Install dependencies ─────────────────────────────────
    print("\n📦 Installing required packages...")
    os.system("pip install google-auth-oauthlib google-api-python-client -q")

    # ── Run OAuth flow ───────────────────────────────────────
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        SCOPES = [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube",
        ]

        print("\n🌐 Opening browser for Google sign-in...")
        print("   Sign in with your YouTube channel account")
        print("   Then click Allow\n")

        flow  = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
        creds = flow.run_local_server(port=8080, open_browser=True)

        print("\n✅ Authentication successful!")

        # ── Save pickle ──────────────────────────────────────
        with open("youtube_token.pickle", "wb") as f:
            pickle.dump(creds, f)
        print("✅ Saved: youtube_token.pickle")

        # ── Generate base64 ──────────────────────────────────
        token_b64 = base64.b64encode(pickle.dumps(creds)).decode()

        # Save to file
        with open("YOUTUBE_TOKEN_B64.txt", "w") as f:
            f.write(token_b64)

        print("✅ Saved: YOUTUBE_TOKEN_B64.txt")

        # ── Print instructions ───────────────────────────────
        print("\n" + "=" * 60)
        print("🎉 SUCCESS! Now add this to Railway:")
        print("=" * 60)
        print("\n1. Go to railway.app → your project → Variables")
        print("2. Add new variable:")
        print("   Name  : YOUTUBE_TOKEN_B64")
        print("   Value : (copy from YOUTUBE_TOKEN_B64.txt file)")
        print("\n📄 The token is saved in YOUTUBE_TOKEN_B64.txt")
        print("   Open that file, select all, copy and paste into Railway")
        print("=" * 60)

        # Also print first 50 chars as preview
        print(f"\nToken preview: {token_b64[:50]}...")
        print(f"Token length : {len(token_b64)} characters")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  - Make sure you're running this on your PC (not a server)")
        print("  - Make sure port 8080 is not blocked")
        print("  - Try adding http://localhost:8080 to OAuth redirect URIs")
        print("    in Google Cloud Console → Credentials → your OAuth Client")

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
