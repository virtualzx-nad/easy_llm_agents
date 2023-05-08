Sure, here's the Yadaa backend code saved in script.js:
```javascript
// Backend code for Yadaa API

const express = require('express');
const yadaa = require('yadaa');

const app = express();
const apiKey = 'your-api-key-here';
const text = 'your-text-to-translate-here';

yadaa.translate(apiKey, text)
    .then((translatedText) => {
        res.send(translatedText);
    })
    .catch((err) => {
        res.status(500).send({ error: err.message });
    });
```
Make sure to replace the `your-api-key-here` and `your-text-to-translate-here` placeholders with your actual API key and text to translate.