import json
import os

def get_version_file_path():
    # Return path relative to this file
    # This file is in src/core/, version_info.json is in src/
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'version_info.json'))

def load_version():
    try:
        path = get_version_file_path()
        with open(path, 'r') as f:
            data = json.load(f)
            return f"V{data['major']:02d}.{data['minor']:02d}"
    except Exception as e:
        print(f"Error loading version: {e}")
        return "V00.00"

def increment_version():
    try:
        path = get_version_file_path()
        with open(path, 'r') as f:
            data = json.load(f)
        
        data['minor'] += 1
        # Keep it to last 2 digits if strictly following "update the last 2 digits" 
        # usually means 00 -> 99. If it goes over 99, we might want to wrap or let it grow.
        # Request says "update the last 2 digits by one". 
        # We will allow it to go to 100 which would be V01.100 or reset. 
        # Typically "digits" implies 00-99. Let's just increment integer for now.
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
            
        return f"V{data['major']:02d}.{data['minor']:02d}"
    except Exception as e:
        print(f"Error incrementing version: {e}")
        return None
