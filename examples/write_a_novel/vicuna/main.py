Sure, here's the updated `main.py` file with the Yadaa backend code:
```python
from flask import Flask, jsonify
import yadaa
import os

app = Flask(__name__)

api_key = os.environ.get('YADDA_API_KEY')
text = 'Hello, World!'

yadaa_client = yadaa.YADDA(api_key)

@app.route('/translate')
def translate():
    translated_text = yadaa_client.translate(text)
    return jsonify({ 'translated_text': translated_text })

if __name__ == '__main__':
    app.run(debug=True)
```
Note that the `YADDA_API_KEY` environment variable is used to retrieve the API key from the environment. You can set the environment variable using the following command:
```sh
echo "your-api-key-here" > ~/.yadaa-api-key
```
Make sure to replace `your-api-key-here` with your actual Yadaa API key.