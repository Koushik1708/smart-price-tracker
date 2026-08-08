import requests

url = 'http://localhost:8001'
login_data = {'username': 'testuser3@example.com', 'password': 'password123'}
resp = requests.post(f'{url}/auth/login', data=login_data)
token = resp.json().get('access_token')

headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
track_data = {'url': 'https://amazon.in/dp/B08L5WHFT9'}

print('Tracking product...')
resp = requests.post(f'{url}/products/track', headers=headers, json=track_data)
print('Response:', resp.status_code, resp.text)
