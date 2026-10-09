import os
import requests
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get API key
api_key = os.getenv("OPENAQ_API_KEY")

if not api_key:
    raise ValueError("OPENAQ_API_KEY not found in .env")

# OpenAQ test endpoint
url = "https://api.openaq.org/v3/locations/8118"

headers = {
    "X-API-Key": api_key
}

# Send request
response = requests.get(
    url,
    headers=headers,
    timeout=30
)

print("Status Code:", response.status_code)

if response.ok:
    data = response.json()

    print("OpenAQ API connection successful.")

    if data.get("results"):
        location = data["results"][0]
        print("Location:", location.get("name"))
        print("Location ID:", location.get("id"))
    else:
        print("API connected, but no location data returned.")

else:
    print("OpenAQ API request failed.")
    print("Response:", response.text)