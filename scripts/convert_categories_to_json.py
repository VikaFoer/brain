"""
Script to convert categories from text format to JSON
Format: number<TAB>name
"""
import json
import sys


def convert_text_to_json(text: str) -> list:
    """
    Convert text format to JSON format
    Format: number<TAB>name
    Returns: list of dicts with 'code' and 'name'
    """
    categories = []
    
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Split by tab or multiple spaces
        parts = line.split('\t')
        if len(parts) < 2:
            # Try splitting by multiple spaces (at least 2 spaces)
            import re
            parts = re.split(r'\s{2,}', line, 1)
            if len(parts) < 2:
                # Try single space split (take first as code, rest as name)
                parts = line.split(None, 1)
        
        if len(parts) >= 2:
            code_str = parts[0].strip()
            name = parts[1].strip()
            
            try:
                code = int(code_str)
                categories.append({"code": code, "name": name})
            except ValueError:
                # If code is not a number, use None
                categories.append({"code": None, "name": line.strip()})
        elif len(parts) == 1:
            # No code, just name
            categories.append({"code": None, "name": parts[0].strip()})
    
    return categories


def main():
    """Main function"""
    # Read from stdin or file
    if len(sys.argv) > 1:
        # Read from file
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            text = f.read()
        output_file = sys.argv[2] if len(sys.argv) > 2 else 'categories.json'
    else:
        # Read from stdin
        print("Paste categories (format: number<TAB>name), then press Ctrl+D (Linux/Mac) or Ctrl+Z (Windows):")
        text = sys.stdin.read()
        output_file = 'categories.json'
    
    categories = convert_text_to_json(text)
    print(f"📋 Parsed {len(categories)} categories")
    
    # Write JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Created {output_file} with {len(categories)} categories")
    print(f"\n💡 To import, use:")
    print(f"   curl -X POST 'http://localhost:8000/api/legal-acts/import-categories' \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d @{output_file}")


if __name__ == "__main__":
    main()

