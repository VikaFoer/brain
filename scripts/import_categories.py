"""
Script to import categories from text format
Format: number<TAB>name
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.category import Category


def parse_categories_text(text: str) -> list:
    """
    Parse categories from text format:
    Format: number<TAB>name
    Returns: list of tuples (code, name)
    """
    categories = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Split by tab or multiple spaces
        parts = line.split('\t')
        if len(parts) < 2:
            # Try splitting by multiple spaces
            parts = line.split(None, 1)
        
        if len(parts) >= 2:
            code_str = parts[0].strip()
            name = parts[1].strip()
            
            try:
                code = int(code_str)
                categories.append((code, name))
            except ValueError:
                # If code is not a number, use None
                categories.append((None, line.strip()))
        elif len(parts) == 1:
            # No code, just name
            categories.append((None, parts[0].strip()))
    
    return categories


async def import_categories(categories_data: list):
    """Import categories to database"""
    db = SessionLocal()
    try:
        imported = 0
        updated = 0
        
        for code, name in categories_data:
            if not name:
                continue
            
            # Check if category exists by name
            category = db.query(Category).filter(Category.name == name).first()
            
            if not category:
                # Create new category
                category = Category(name=name, code=code, element_count=0)
                db.add(category)
                imported += 1
            else:
                # Update existing category
                if category.code != code:
                    category.code = code
                    updated += 1
        
        db.commit()
        
        print(f"✅ Imported {imported} new categories")
        if updated > 0:
            print(f"✅ Updated {updated} existing categories")
        
        total = db.query(Category).count()
        print(f"✅ Total categories in database: {total}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


def main():
    """Main function"""
    # Read from stdin or file
    if len(sys.argv) > 1:
        # Read from file
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        # Read from stdin
        print("Paste categories (format: number<TAB>name), then press Ctrl+D (Linux/Mac) or Ctrl+Z (Windows):")
        text = sys.stdin.read()
    
    categories = parse_categories_text(text)
    print(f"📋 Parsed {len(categories)} categories")
    
    asyncio.run(import_categories(categories))


if __name__ == "__main__":
    main()

