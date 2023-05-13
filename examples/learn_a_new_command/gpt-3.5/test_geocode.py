import geocode

# Test with valid address
address = '1600 Amphitheatre Parkway, Mountain View, CA'
expected_lat = 37.4224764
expected_lng = -122.0842499
lat, lng = geocode.geocode_address(address)
assert lat == expected_lat, f'Expected latitude {expected_lat}, but got {lat}'
assert lng == expected_lng, f'Expected longitude {expected_lng}, but got {lng}'

# Test with invalid address
address = 'invalid address'
expected_lat = None
expected_lng = None
lat, lng = geocode.geocode_address(address)
assert lat == expected_lat, f'Expected latitude {expected_lat}, but got {lat}'
assert lng == expected_lng, f'Expected longitude {expected_lng}, but got {lng}'