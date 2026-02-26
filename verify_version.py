from src.core.version_manager import load_version, increment_version
import json
import os

print(f"Initial Version: {load_version()}")

# Test Increment
new_ver = increment_version()
print(f"Incremented Version: {new_ver}")

# Verify file content
path = os.path.join(os.path.dirname(__file__), 'src', 'version_info.json')
with open(path, 'r') as f:
    data = json.load(f)
    print(f"File Content: {data}")

if data['major'] == 1 and data['minor'] == 1:
    print("SUCCESS: Version incremented correctly.")
else:
    print("FAILURE: Version did not increment correctly.")
