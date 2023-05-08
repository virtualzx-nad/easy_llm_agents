```vbnet
import yadaa

def translate_text(api_key):
    yadaa_client = yadaa.YADDAA(api_key)
    return yadaa_client.translate(text)

if __name__ == '__main__':
    translate_text(api_key)
```
This code will create an endpoint that takes in an API key as an argument and returns the translated text using the yadaa library.