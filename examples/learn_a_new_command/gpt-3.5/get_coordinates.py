import requests
import json

def get_coordinates(location):
    api_key = 'YOUR_API_KEY'
    url = f'https://api.positionstack.com/v1/forward?access_key={api_key}&query={location}'
    response = requests.get(url)
    if response.status_code == 200:
        data = json.loads(response.text)
        if data['data']:
            latitude = data['data'][0]['latitude']
            longitude = data['data'][0]['longitude']
            return (latitude, longitude)
        else:
            return None
    else:
        return None