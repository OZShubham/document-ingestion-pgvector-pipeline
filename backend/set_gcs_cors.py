"""
Script to set CORS configuration on GCS bucket
"""

from google.cloud import storage
from config import Config
import os

def set_bucket_cors():
    """Set CORS configuration on the GCS bucket"""
    
    # Initialize client
    dir_path = os.path.dirname(os.path.abspath(__file__))
    credentials_path = os.path.join(dir_path, 'secrets', 'credentials.json')
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    
    client = storage.Client(project=Config.PROJECT_ID)
    bucket = client.bucket(Config.BUCKET_NAME)
    
    # Define CORS configuration
    cors_config = [
        {
            "origin": [
                "http://localhost:5173",
                "http://localhost:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:3000",
                # Add your production frontend URL here
                # "https://your-frontend.com"
            ],
            "method": ["GET", "HEAD", "PUT", "POST", "DELETE", "OPTIONS"],
            "responseHeader": [
                "Content-Type",
                "Content-Length",
                "Content-MD5",
                "Content-Disposition",
                "Cache-Control",
                "X-Goog-ACL",
                "X-Goog-Content-Length-Range",
            ],
            "maxAgeSeconds": 3600
        }
    ]
    
    # Set CORS configuration
    bucket.cors = cors_config
    bucket.patch()
    
    print(f"✅ CORS configuration set on bucket: {Config.BUCKET_NAME}")
    print(f"\n📋 Current CORS configuration:")
    print(f"   Origins: {cors_config[0]['origin']}")
    print(f"   Methods: {cors_config[0]['method']}")
    print(f"   Max Age: {cors_config[0]['maxAgeSeconds']} seconds")
    
    # Verify
    bucket.reload()
    print(f"\n✅ Verified CORS configuration:")
    for i, cors_rule in enumerate(bucket.cors):
        print(f"\n   Rule {i+1}:")
        print(f"      Origins: {cors_rule.get('origin', [])}")
        print(f"      Methods: {cors_rule.get('method', [])}")
        print(f"      Max Age: {cors_rule.get('maxAgeSeconds', 0)}s")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     GCS CORS CONFIGURATION SCRIPT                            ║
║                                                                              ║
║  This script will configure CORS on your GCS bucket to allow:               ║
║  • Uploads from localhost during development                                ║
║  • PUT requests for signed URL uploads                                      ║
║  • OPTIONS preflight requests                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    confirm = input(f"\n⚠️  Set CORS on bucket '{Config.BUCKET_NAME}'? (yes/no): ")
    
    if confirm.lower() == 'yes':
        try:
            set_bucket_cors()
            print("\n✅ CORS configuration complete!")
            print("\n💡 You can now upload files from your React frontend.")
            print("   Restart your React dev server if needed.")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ Operation cancelled")