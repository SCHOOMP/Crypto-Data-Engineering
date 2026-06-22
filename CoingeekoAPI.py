import requests
import os

CoinGekkoKey = os.getenv("CoinGekkoKey")

url = "https://api.coingecko.com/api/v3/simple/price?vs_currencies=usd&ids=bitcoin&x_cg_demo_api_key=CG-zzvvaXgb4EU3DH7bw88fEhZZ"
params = {
         'ids': 'bitcoin',
         'vs_currencies': 'USD'
}

headers = { 'x-cg-demo-api-key': CoinGekkoKey }

response = requests.get(url, params = params)
if response.status_code == 200:
         data = response.json()
         Bitcoin_price = data['bitcoin']['usd']
         print(f'The price of Bitcoin in USD is ${Bitcoin_price}')
else:
         print('Failed to retrieve data from the API')