from flask import Flask, render_template, url_for, request, jsonify
from googleapiclient.discovery import build
import os

app = Flask(__name__)

SEARCH_API_KEY = os.environ.get('GOOGLE_API')
SEARCH_ENGINE_ID = os.environ.get('SEARCH_ENGINE_ID')
SERVICE_NAME = 'customsearch'
SERVICE_VERSION = 'v1'

# Create a client object
service = build(SERVICE_NAME, SERVICE_VERSION, developerKey=SEARCH_API_KEY)

@app.route("/", methods = ['GET', 'POST'])
def home_page():
    results = []
    if request.method == 'POST':
        query = request.form['query']
        results = search(query)
        
        return render_template('index.html', results=results, query=query)

    return render_template('index.html', results=results)

def search(query):
    # Call the API with the query and search engine ID
    res = service.cse().list(q=query, cx=SEARCH_ENGINE_ID).execute()

    # Extract the search results
    items = res['items'] if 'items' in res else []

    # Return the search results
    return items

if __name__ == '__main__':
    app.run(debug=True)