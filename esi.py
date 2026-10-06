import requests
import pandas as pd

def markets_region_history(region_id, type_id):
    response = requests.get(f'https://esi.evetech.net/markets/{region_id}/history?type_id={type_id}')
    df = pd.DataFrame(response.json())

    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    return df

def markets_prices():
    response = requests.get('https://esi.evetech.net/markets/prices')
    df = pd.DataFrame(response.json())

    df = df.set_index('type_id')

    return df
