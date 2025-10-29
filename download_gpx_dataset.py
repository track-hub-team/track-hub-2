import kagglehub
import os
import shutil

print("📥 Downloading GPX dataset from Kaggle...")
print("   Dataset: roccoli/gpx-hike-tracks")
print("   Size: ~200MB")
print("")

# Download latest version
try:
    path = kagglehub.dataset_download("roccoli/gpx-hike-tracks")
    
    print(f"✅ Dataset downloaded to: {path}")
    print("")
    
    # Find CSV file
    csv_found = False
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.csv'):
                csv_path = os.path.join(root, file)
                # Copy to project root for easier access
                shutil.copy(csv_path, 'gpx_dataset.csv')
                
                print(f"✅ CSV file copied to: gpx_dataset.csv")
                print(f"   Original location: {csv_path}")
                print(f"   File size: {os.path.getsize('gpx_dataset.csv') / (1024*1024):.2f} MB")
                print("")
                print("📊 Next step: Import the data")
                print("   python import_gpx_data.py")
                
                csv_found = True
                break
        if csv_found:
            break
    
    if not csv_found:
        print("⚠️  No CSV file found in the downloaded dataset")
        print(f"   Check manually in: {path}")
        
except Exception as e:
    print(f"❌ Error downloading dataset: {e}")
    print("")
    print("💡 Alternative: Download manually from:")
    print("   https://www.kaggle.com/datasets/roccoli/gpx-hike-tracks")