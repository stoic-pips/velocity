import requests
import json

headers = {
    'X-API-Key': 'change-me-to-a-strong-random-string'
}

try:
    response = requests.get('http://localhost:8000/api/symbols', headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
