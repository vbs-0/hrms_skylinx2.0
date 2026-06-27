import re
import itertools
from pathlib import Path

# Read the file
with open('docs/page_inventory.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    content = ''.join(lines)

# Track all endpoints
all_endpoints = []

# Pattern for PART A: numbered items with /path/ and description
part_a_pattern = r'^(\d+)\.\s*(/[^\s]+)\s*—\s*(.+)$'

# Pattern for PART B: has "·" separator
part_b_pattern = r'^(\d+)\.\s*(/\S+)\s*·\s*(\S+)$'

# Pattern for PART C and beyond: usually shorter format with "·"
part_c_pattern = r'^(\d+)\.\s*(/\S+)\s*·\s*(\S+)$'

# Parse through all lines
current_part = None
for line in lines:
    line = line.strip()
    if not line:
        continue
    
    # Detect current part
    if line.startswith('## PART '):
        current_part = line
        continue
    
    # Extract endpoints based on pattern and part
    match = None
    if current_part and ('PART A' in current_part or current_part == '## PART A — Navigable menu (what HR clicks)'):
        # PART A has format: "123. /path/ — Description"
        if re.match(r'^\d+\.\s*/', line):
            # Extract just the URL before " —" if it exists
            match = re.match(r'^\d+\.\s*(/\S+)', line)
            if match:
                all_endpoints.append(match.group(1))
    elif current_part and ('PART B' in current_part):
        # PART B has format: "123. /path/  ·  view_name"
        if re.match(r'^\d+\.\s*/', line):
            match = re.match(r'^\d+\.\s*(/\S+)', line)
            if match:
                all_endpoints.append(match.group(1))
    elif current_part and ('PART C' in current_part or 'PART D' in current_part or 'PART E' in current_part or 'PART F' in current_part):
        # PART C-F usually just "path"
        if re.match(r'^\d+\.\s*/', line):
            match = re.match(r'^\d+\.\s*(/\S+)', line)
            if match:
                all_endpoints.append(match.group(1))

# Output results
print(f'Total endpoints found: {len(all_endpoints)}')
print(f'\nSample endpoints (first 20):')
for i, endpoint in enumerate(all_endpoints[:20]):
    print(f'  {i+1}. {endpoint}')

# Count endpoints by type
from collections import defaultdict
endpoint_counts = defaultdict(int)
for endpoint in all_endpoints:
    endpoint_counts[endpoint] += 1

print(f'\nUnique endpoints: {len(endpoint_counts)}')

# Check if the count matches the claimed 3,614
print(f'\nInventory claims: Total URL patterns: **3614**')
print(f'Filtered endpoints found: {len(all_endpoints)}')
print(f'Count discrepancy: {3614 - len(all_endpoints)}')

# Save endpoints to file
Path('all_endpoints.txt').write_text('\n'.join(all_endpoints))
print(f'\nSaved {len(all_endpoints)} endpoints to all_endpoints.txt')