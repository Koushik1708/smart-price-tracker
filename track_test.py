import requests
BASE_URL = 'http://localhost:8001'
resp = requests.post(f'{BASE_URL}/auth/login', data={'username': 'admin@letsgo.com', 'password': 'admin'})
token = resp.json()['access_token']
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
payload = {'url': 'https://www.amazon.in/Sony-WH-1000XM5-Cancelling-Headphones-Optimized/dp/B09XS7JWHX'}
r = requests.post(f'{BASE_URL}/products/track', headers=headers, json=payload)
print('Track response:', r.status_code, r.text)
