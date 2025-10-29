import csv

with open('gpx_dataset.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    
    # Get column names
    columns = reader.fieldnames
    print("📋 Column names in CSV:")
    print("=" * 60)
    for i, col in enumerate(columns, 1):
        print(f"{i:2d}. {col}")
    
    print("\n" + "=" * 60)
    print("\n📊 First row sample:")
    print("=" * 60)
    
    # Read first row
    first_row = next(reader)
    for key, value in first_row.items():
        # Truncate long values
        display_value = str(value)[:100]
        if len(str(value)) > 100:
            display_value += "..."
        print(f"\n{key}:")
        print(f"  {display_value}")