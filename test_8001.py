import requests
import sys

BASE_URL = 'http://localhost:8001'

def run():
    print('Testing /auth/login...')
    resp = requests.post(f'{BASE_URL}/auth/login', data={'username': 'admin@letsgo.com', 'password': 'admin'})
    if resp.status_code != 200:
        print('Login failed:', resp.status_code)
        sys.exit(1)
    
    token = resp.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    endpoints = [
        '/dashboard/summary',
        '/dashboard/activity',
        '/dashboard/price-drops',
        '/dashboard/recent-products'
    ]

    for ep in endpoints:
        resp = requests.get(f'{BASE_URL}{ep}', headers=headers)
        print(f'{ep} -> {resp.status_code}')

run()
