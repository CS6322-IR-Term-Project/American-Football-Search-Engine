from flask import Flask, render_template, url_for, request
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
import os, requests, json, re, html
import pysolr

app = Flask(__name__)

solr = pysolr.Solr('http://localhost:8983/solr/nutch', timeout=10)

@app.route("/", methods = ['GET', 'POST'])
def home_page():
    google_results = []
    bing_results = []

    if request.method == 'POST':
        query = request.form['query']

        # results for custom search, google and bing
        custom_results = custom_search(query)
        
        return render_template('index.html', custom_results = custom_results, google_results=google_results, bing_results=bing_results, query=query)
    
    return render_template('index.html', google_results=google_results, bing_results=bing_results)

def create_doc(result):
    doc = {
        'id': result.get('id'),
        'title': result.get('title'),
        'url': result.get('url'),
        'anchor': result.get('anchor'),
        'content': None
    }

    content = result.get('content')
    if content is not None:
        meta_info = " ".join(re.findall("[a-zA-Z]+", content[0][:500]))
        doc['content'] = [meta_info]

    return doc


def custom_search(query):
    results = query_search(query)
    custom_results = [create_doc(result) for result in results]
    return custom_results

def query_search(query):
    results = solr.search('*:*', **{
        'fl': 'id, title, url, anchor, content',  # Select the fields to return
        'rows': 10
    })

    docs = [create_doc(result) for result in results.docs]
    return docs


if __name__ == '__main__':
    app.run(debug=True)