import json
import os
import sys

PROJECT_PATH = r'C:\Users\VISHNU\Downloads\nifty100_project'
sys.path.append(PROJECT_PATH)

from src.api.main import app

def export_openapi():
    openapi_schema = app.openapi()
    os.makedirs(os.path.join(PROJECT_PATH, 'docs'), exist_ok=True)
    with open(os.path.join(PROJECT_PATH, 'docs', 'openapi.json'), 'w') as f:
        json.dump(openapi_schema, f, indent=2)
    print("Exported docs/openapi.json")

if __name__ == "__main__":
    export_openapi()
