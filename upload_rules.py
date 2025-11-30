import requests
import json
import os
import sys

API_URL = "http://3.145.105.148:5000/api/rules"
JSON_FILE = "rules.json"

def upload_rules():
    # 1. Locate the file
    if not os.path.exists(JSON_FILE):
        print(f"❌ Error: File '{JSON_FILE}' not found.")
        print("   Please create a file named 'rules.json' in this folder.")
        return

    # 2. Load the JSON content
    try:
        with open(JSON_FILE, 'r') as f:
            payload = json.load(f)
            # Ensure payload is a list (if your API expects a list of rules)
            if not isinstance(payload, list):
                print("⚠️ Warning: JSON root is not a list. If uploading a single rule, this might be okay.")
            print(f"📖 Loaded data from {JSON_FILE}...")
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in '{JSON_FILE}'.\n   Details: {e}")
        return

    # 3. Send to EC2
    try:
        print(f"🚀 Uploading to: {API_URL}")
        headers = {'Content-Type': 'application/json'}
        
        # We use POST to create new rules. Change to PUT if you are replacing the whole list.
        response = requests.post(API_URL, json=payload, headers=headers)

        # 4. Check results
        if response.status_code in [200, 201]:
            print("✅ Success!")
            print("Server Response:", response.json())
        else:
            print(f"⚠️ Failed (Status: {response.status_code})")
            print("Response text:", response.text)

    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Failed. verify that:")
        print("   1. Your EC2 instance is running.")
        print("   2. Port 5000 is open in your AWS Security Group (Inbound Rules).")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

if __name__ == "__main__":
    upload_rules()
