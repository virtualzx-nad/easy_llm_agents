Sure, here's the Yadaa backend code saved in yadaa.py:
```python
from flask import Flask, jsonify
from yadaa import Yadaa

app = Flask(__name__)
api_key = 'your-api-key-here'

yadaa = Yadaa(api_key)

@app.route('/translate', methods=['POST'])
def translate():
    text = request.json.get('text')
    translated_text = yadaa.translate(text)
    return jsonify({ 'translated_text': translated_text })

if __name__ == '__main__':
    app.run(debug=True)
```
Make sure to replace the `your-api-key-here` placeholder with your actual API key.