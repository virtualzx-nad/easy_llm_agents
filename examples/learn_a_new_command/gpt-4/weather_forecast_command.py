
import requests
from lm_agent.commands import Command

class WeatherForecastCommand(
    Command,
    command='weather_forecast',
    description="Get weather forecast for a date in the near future. The following should be supplied in content:
    -`date`: date for which the forecast is needed

    - `location`: location for which the forecast is needed"
):
    def generate_prompt(self):
        api_key = self.metadata['openweathermap_api_key']
        location = self.content[0]['location']
        date = self.content[0]['date']

        url = f'https://api.openweathermap.org/data/2.5/forecast?q={location}&appid={api_key}'
        resp = requests.get(url)
        if not resp.ok:
            return 'Failed to get weather forecast'

        forecast_data = resp.json()
        # Process forecast data to extract relevant information for the specified date

        return 'Weather forecast for the specified date and location'

