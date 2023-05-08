Sure, here's the help documentation for the Yadaa endpoint in Markdown format:

Yadaa Endpoint
================

The Yadaa endpoint is a simple REST API endpoint that allows users to translate text using the Yadaa API. This endpoint expects a POST request with a JSON payload containing the text to translate and the API key for the Yadaa API.

Example Request
--------------

The following is an example request to the Yadaa endpoint using `curl`:
```json
POST /yadaa HTTP/1.1
Host: localhost:3000
Content-Type: application/json

{
  "text": "Hello, Yadaa!",
  "apiKey": "abc123"
}
```
Example Response
---------------

The following is an example response from the Yadaa endpoint:
```
HTTP/1.1 200 OK
Content-Type: application/json

{
  "translation": "안녕, Yadaa!",
  "translationScore": 1.0
}
```
This response includes the translated text and a translation score (a measure of how well the translation is) as a JSON object.

Authenticating with Bearer Token
-------------------------------

To authenticate the API request, you can include a bearer token in the `Authorization` header of the request. For example:
```javascript
Authorization: Bearer abc123
```
Note that the bearer token must be valid and have the appropriate permissions to access the Yadaa API.

Using with FastAPI
------------------

To use the Yadaa endpoint with FastAPI, you can import the `FastAPI` and `requests` modules and create an instance of `FastAPI` with a single endpoint for the Yadaa endpoint:
```python
from fastapi import FastAPI, HTTPException
from requests.request import Request
import requests

app = FastAPI()

@app.post("/yadaa")
async def yadaa(text: str, api_key: str, data: str = Depends(None)):
    headers = {"Content-Type": "application/json"}
    params = {"text": text, "apiKey": api_key}
    resp = requests.post("http://localhost:3000/yadaa", json=data, headers=headers, params=params).json()
    return {"translation": resp["translation"], "translationScore": resp["translationScore"]}
```
In this code, the `yadaa` function expects a POST request to the `/yadaa` endpoint with a JSON payload containing the text to translate and the API key. The function sends a request to the Yadaa API using `requests` and returns the translated text and translation score as a dictionary.

To test the endpoint, you can use `curl` or a HTTP client like `Postman` to send a POST request to `http://localhost:8000/yadaa` with the following JSON payload:
```json
{
  "text": "Hello, Yadaa!",
  "apiKey": "abc123"
}
```
This will return the translated text and translation score as a JSON object.