from pathlib import Path

# Read the file
with open('docs/page_inventory.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Count total lines
lines = content.splitlines()
print(f"Total lines: {len(lines)}")

# Count number of items in each section
import re

hidden_count = 0
numbered_items = []
section_counts = {}

current_section = "UNKNOWN"
for line in lines:
    stripped = line.strip()
    # Parse section headers
    if stripped.startswith('## PART '):
        current_section = stripped
        section_counts[current_section] = 0
    elif stripped.startswith('### ') and ' (' in stripped and ')' in stripped:
        # Extract count from section header like "### (top-level)  (51)"
        match = re.search(r'\((\d+)\)', stripped)
        if match:
            section_counts[current_section] = int(match.group(1))
    elif stripped and stripped[0].isdigit() and '. ' in stripped:
        numbered_items.append(stripped)
        hidden_count += 1 if '(hidden)' in stripped else 0

print(f"\nTotal numbered items: {len(numbered_items)}")
print(f"Number of items tagged (hidden): {hidden_count}")
print(f"\nSection summary:")
for section, count in section_counts.items():
    print(f"  {section}: {count} items")

print("\nFirst 10 numbered endpoints:")
for i, item in enumerate(numbered_items[:10]):
    print(f"  {i+1}. {item}")

# Check if the file has 3,614 total items as claimed
print(f"\nClaimed total URL patterns: **3614**")
print(f"Actual numbered items found: {len(numbered_items)}")