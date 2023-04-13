
from easy_llm_agents.commands import BaseCommand

class WeatherForecastCommand(BaseCommand, command='weather_forecast', description='Get weather forecast for the next 5 days. The following should be supplied in content:\n\n- `city`: name of the city\n\n- `country`: two-letter country code'):
    
    def generate_prompt(self):
        # Lazy import requests module
        import requests
        
        url = 'https://api.openweathermap.org/data/2.5/forecast'
        params = {
            'q': f'{self.content[0]["city"]},{self.content[0]["country"]}',
            'units': 'metric',
            'appid': self.metadata["openweathermap_api_key"],
            'cnt': 5
        }
        
        resp = requests.get(url, params=params)
        
        if not resp.ok:
            return f'Error retrieving weather forecast: {resp.reason}'
        
        try:
            data = resp.json()
            forecasts = [f'Day {i+1}: {day["weather"][0]["description"]} with temperatures between {day["main"]["temp_min"]} and {day["main"]["temp_max"]} °C' for i, day in enumerate(data['list'])]
            
            return '\n'.join(forecasts)
        
        except Exception as e:
            return f'Error parsing weather forecast data: {str(e)}'

