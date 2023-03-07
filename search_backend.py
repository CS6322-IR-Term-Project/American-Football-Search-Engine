from flask import Flask, render_template, url_for, request
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
import os, requests, json, re, html

app = Flask(__name__)

GOOGLE_SEARCH_API_KEY = os.environ.get('GOOGLE_API')
BING_SEARCH_API_KEY = os.environ.get('BING_API')
SEARCH_ENGINE_ID = os.environ.get('SEARCH_ENGINE_ID')
SERVICE_NAME = 'customsearch'
SERVICE_VERSION = 'v1'

# Create a client object
service = build(SERVICE_NAME, SERVICE_VERSION, developerKey=GOOGLE_SEARCH_API_KEY)

@app.route("/", methods = ['GET', 'POST'])
def home_page():
    google_results = []
    bing_results = []

    if request.method == 'POST':
        query = request.form['query']

        # results for google and bing
        google_results = google_search(query)
        bing_results = bing_search(query)
        
        return render_template('index.html', google_results=google_results, bing_results=bing_results, query=query)
    
    return render_template('index.html', google_results=google_results, bing_results=bing_results)

def google_search(query):
    # Call the API with the query and search engine ID
    res = service.cse().list(q=query, cx=SEARCH_ENGINE_ID).execute()

    # Extract the search results
    items = res['items'] if 'items' in res else []

    # Return the search results
    return items

def bing_search(query): 
    # Set the search parameters
    params = { 
        'q': query, 
        "textDecorations": True,
        "safeSearch": "Strict",
        "textFormat": "Raw"
    }

    endpoint = "https://api.bing.microsoft.com/v7.0/search"

    # Set the headers for the request
    headers = {
        "Ocp-Apim-Subscription-Key": BING_SEARCH_API_KEY
    }

    response = requests.get(endpoint, headers=headers, params=params).json()
    results = response["webPages"]["value"]

   # Extract the URLs and text for each result
    urls_and_texts = []

    for result in results:
        url = result["url"]
        html_content = result["snippet"]
        name = result["name"]

        # text cleaning for description
        soup = BeautifulSoup(html_content, "html.parser")
        plain_text = soup.get_text(strip=True)
        plain_text = html.unescape(plain_text)

        # Remove non-ASCII characters
        plain_text = re.sub(r'[^\x00-\x7F]+', ' ', plain_text)

        # Remove leading/trailing whitespace and multiple consecutive spaces
        plain_text = re.sub(r'\s+', ' ', plain_text).strip()

        urls_and_texts.append({
            "url": url,
            "text": plain_text,
            "name": name
        })

    return urls_and_texts

if __name__ == '__main__':
    app.run(debug=True)