Without seeing the actual code, it's difficult to determine where the syntax error is occurring. However, based on the error message, it is likely that there is an unterminated string literal on the first line of the code. 

To fix this error, check the first line of the code for any missing or mismatched quotation marks, parentheses, or brackets. Make sure all strings and other literals are properly enclosed in their respective delimiters. 

For example, if the first line reads:

`API_ENDPOINT = 'https://maps.googleapis.com/maps/api/geocode/json`

The error is likely due to the missing closing apostrophe at the end of the string. To fix it, simply add the closing apostrophe:

`API_ENDPOINT = 'https://maps.googleapis.com/maps/api/geocode/json'`