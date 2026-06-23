"""Test HIP强制提升 fix in _feedback_self_patch"""
import sys, time, json
sys.path.insert(0, '.')
from pathlib import Path
from brain.act import _feedback_self_patch

# Check HIP before
HIP = Path.home() / '.zero_brain' / 'hippocampus_memory.json'
before = len(json.loads(HIP.read_bytes()).get('causal_chains', []))
print(f'Before: {before} chains')

start = time.time()
_feedback_self_patch()
elapsed = time.time() - start

after = len(json.loads(HIP.read_bytes()).get('causal_chains', []))
print(f'After: {after} chains (+{after-before})')
print(f'Elapsed: {elapsed:.1f}s')
