# Import necessary libraries
import requests


def weather_forecast(date):
    # Set the latitude and longitude of the location
    latitude = 37.7749
    longitude = -122.4194
    
    # Get the grid coordinates for the location
    url = f'https://api.weather.gov/points/{latitude},{longitude}'
    response = requests.get(url)
    data = response.json()
    grid_x, grid_y = data['properties']['gridX'], data['properties']['gridY']
    office = data['properties']['cwa']
    
    # Get the forecast for the date at the location
    url = f'https://api.weather.gov/gridpoints/{office}/{grid_x},{grid_y}/forecast?units=us'
    response = requests.get(url)
    data = response.json()
    periods = data['properties']['periods']
    
    # Extract the relevant information from the response
    forecast = []
    for period in periods:
        if period['startTime'][:10] == date:
            forecast.append(period['name'])
            forecast.append(period['detailedForecast'])
            break
    
    # Return the forecast to the user
    return ' '.join(forecast)