import requests
import json
import time

url = 'http://localhost:8001'

# 1. Register or login
reg_data = {'email': 'testrunner@example.com', 'password': 'password123'}
try:
    requests.post(f'{url}/auth/register', json=reg_data)
except Exception:
    pass

login_data = {'username': 'testrunner@example.com', 'password': 'password123'}
resp = requests.post(f'{url}/auth/login', data=login_data)
token = resp.json().get('access_token')
print('Token:', token)

headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
track_data = {'url': 'https://amazon.in/dp/B08N5W4NNB'}

print('Tracking product...')
resp = requests.post(f'{url}/products/track', headers=headers, json=track_data)
print('Response:', resp.status_code, resp.text)
