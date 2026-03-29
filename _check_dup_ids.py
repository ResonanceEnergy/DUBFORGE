"""Check for duplicate XML IDs in generated ALS."""
import gzip
import re
from collections import Counter

with gzip.open('output/ableton/Wild_Ones_V6.als', 'rb') as f:
    xml = f.read().decode('utf-8')

# Find ALL Id attributes
ids = re.findall(r'Id="(\d+)"', xml)
print(f'Total Id attributes: {len(ids)}')

c = Counter(ids)
dups = {k: v for k, v in c.items() if v > 1}
print(f'Unique IDs: {len(c)}')
print(f'Duplicate IDs: {len(dups)}')

if dups:
    for dup_id, count in sorted(dups.items(), key=lambda x: int(x[0]))[:50]:
        # Find context
        pattern = r'<(\w+)[^>]*Id="' + dup_id + r'"'
        contexts = re.findall(pattern, xml)
        print(f'  ID {dup_id} appears {count}x in: {contexts}')
else:
    print('No duplicate IDs found!')

# Also check: are all AutomationTarget IDs unique?
at_ids = re.findall(r'<AutomationTarget Id="(\d+)"', xml)
at_c = Counter(at_ids)
at_dups = {k: v for k, v in at_c.items() if v > 1}
print(f'\nAutomationTarget IDs: {len(at_ids)} total, {len(at_c)} unique, {len(at_dups)} duplicates')
if at_dups:
    for k, v in sorted(at_dups.items(), key=lambda x: int(x[0]))[:20]:
        print(f'  AutomationTarget ID {k} appears {v}x')

# Check ModulationTarget IDs
mt_ids = re.findall(r'<ModulationTarget Id="(\d+)"', xml)
mt_c = Counter(mt_ids)
mt_dups = {k: v for k, v in mt_c.items() if v > 1}
print(f'\nModulationTarget IDs: {len(mt_ids)} total, {len(mt_c)} unique, {len(mt_dups)} duplicates')
if mt_dups:
    for k, v in sorted(mt_dups.items(), key=lambda x: int(x[0]))[:20]:
        print(f'  ModulationTarget ID {k} appears {v}x')

# Check max ID
max_id = max(int(x) for x in ids)
print(f'\nMax ID value: {max_id}')

# Check for ID=0 usage
zero_ids = re.findall(r'<(\w+)\s+Id="0"', xml)
print(f'\nElements with Id="0": {len(zero_ids)}')
for z in zero_ids[:20]:
    print(f'  <{z} Id="0">')
