import requests

address = "111 South Broadway 12866"

url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=1"

response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})

if response.status_code == 200:
    try:
        data = response.json()
        if data:
            location = data[0]
            print(f"Latitude: {location['lat']}, Longitude: {location['lon']}")
        else:
            print("Location not found")
    except requests.exceptions.JSONDecodeError:
        print("Error decoding the JSON response")
else:
    print(f"Error: Received status code {response.status_code}")