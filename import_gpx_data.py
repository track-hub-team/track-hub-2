import sys
import os
from app import create_app, db
from app.modules.auth.models import User
from app.modules.gpx.services import GPXDatasetService
from werkzeug.datastructures import FileStorage

# Check if CSV exists
if not os.path.exists('gpx_dataset.csv'):
    print("❌ Error: gpx_dataset.csv not found")
    print("   Run first: python download_gpx_dataset.py")
    sys.exit(1)

app = create_app()

with app.app_context():
    print("🔍 Looking for user...")
    
    # Get first user (or create test user)
    user = User.query.first()
    
    if not user:
        print("❌ No users found in database")
        print("   Please create a user first:")
        print("   flask create-admin-user")
        sys.exit(1)
    
    print(f"✅ Using user: {user.email} (ID: {user.id})")
    print("")
    
    # Get file size
    file_size = os.path.getsize('gpx_dataset.csv') / (1024*1024)
    print(f"📂 CSV file: gpx_dataset.csv ({file_size:.2f} MB)")
    print("")
    
    # Confirm before import
    response = input("⚠️  This will import ~12,000 hiking tracks. Continue? (y/n): ")
    if response.lower() != 'y':
        print("❌ Import cancelled")
        sys.exit(0)
    
    print("")
    print("📥 Starting import...")
    print("   This may take 5-10 minutes...")
    print("")
    
    # Import CSV
    try:
        with open('gpx_dataset.csv', 'rb') as f:
            file = FileStorage(
                stream=f,
                filename='gpx_dataset.csv',
                content_type='text/csv'
            )
            
            service = GPXDatasetService()
            result = service.import_from_csv(file, user)
        
        print("")
        print("=" * 50)
        print("✅ IMPORT COMPLETED!")
        print("=" * 50)
        print(f"   Total rows processed: {result['total_rows']}")
        print(f"   Successfully imported: {result['imported']}")
        print(f"   Errors: {len(result['errors'])}")
        print("")
        
        if result['errors']:
            print("⚠️  First 10 errors:")
            for i, error in enumerate(result['errors'][:10], 1):
                print(f"   {i}. {error}")
            print("")
        
        print("🎉 You can now view the hiking tracks:")
        print("   http://localhost:5000/gpx/list")
        print("")
        
    except Exception as e:
        print(f"❌ Error during import: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)