from flask import Flask, render_template, url_for, request
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from flask_cors import CORS
from QueryExpansion.association import association_main
from QueryExpansion.metric import metric_cluster_main
import os, requests, json, re, html
from spellchecker import SpellChecker
from operator import itemgetter
import pysolr

app = Flask(__name__)
CORS(app)
solr = pysolr.Solr('http://localhost:8983/solr/nutch', timeout=10)

@app.route("/", methods = ['GET', 'POST'])
def home_page():
    google_results = []
    bing_results = []

    if request.method == 'POST':
        query = request.form['query']
        user_selection = request.form.get('selection')

        # results for custom search, google and bing
        custom_results = custom_search(query)

        if is_hits(user_selection):
            custom_results = get_hits_results(custom_results)

        elif is_clustering(user_selection):
            custom_results = get_clustering_results(custom_results, user_selection)

        elif is_query_expansion(user_selection):
            custom_results = query_expansion(query, custom_results, user_selection)  
                  
        return render_template('index.html', custom_results = custom_results, google_results=google_results, bing_results=bing_results, query=query)
    
    return render_template('index.html', google_results=google_results, bing_results=bing_results)

def is_hits(user_selection):
    return user_selection == 'hits'

def is_query_expansion(user_selection):
    return user_selection in ['association-expansion', 'metric-expansion', 'scalar-expansion']

def is_clustering(user_selection):
    return user_selection in ['flat-clustering', 'hierarchical-clustering']

def apply_spell_check(query):
    spell = SpellChecker()

    # split the sentence into individual words
    words = query.split()

    # find those words that may be misspelled
    misspelled = spell.unknown(words)

    # create a dictionary of corrections
    corrections = {word: spell.correction(word) for word in misspelled}

    return ' '.join(corrections.get(word, word) for word in words)

def query_expansion(query, custom_results, selection):
    if selection == 'association-expansion':
        expanded_query = association_main(query, custom_results)
        custom_results = custom_search(expanded_query)
    elif selection == 'metric-expansion':
        expanded_query = metric_cluster_main(query, custom_results)
        custom_results = custom_search(expanded_query)
    elif selection == 'scalar-expansion':
        pass
    
    return custom_results



def create_doc(result):

    doc = {
        'id': result.get('id'),
        'title': result.get('title'),
        'url': result.get('url'),
        'anchor': result.get('anchor'),
        'meta_info': result.get('meta_info'),
        'digest': result.get('digest'),
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
    updated_query = f"\"{query}\""

    results = solr.search('text:' + updated_query, **{
        'fl': 'id, title, url, anchor, content, meta_info, digest',  # Select the fields to return
        'rows': 100
    })

    if len(results) == 0:
        results = solr.search('text:' + query, **{
            'fl': 'id, title, url, anchor, content, meta_info, digest',  # Select the fields to return
            'rows': 25
        })


    docs = [create_doc(result) for result in results.docs]
    return docs


def get_hits_results(clust_inp):
    authority_score_file = open("RelevanceModel/authority_score_1", 'r').read()
    authority_score_dict = json.loads(authority_score_file)

    clust_inp = sorted(clust_inp, key=lambda x: authority_score_dict.get(x['url'][0], 0.0), reverse=True)

    return clust_inp


def get_clustering_results(custom_results, user_selection):
    if user_selection == 'flat-clustering':
        f = open('clustering_f.txt')
        lines = f.readlines()
        f.close()
    elif user_selection == 'hierarchical-clustering':
        f = open('clustering_h8.txt')
        lines = f.readlines()
        f.close()

    cluster_map = {}

    for line in lines:
        line_split = line.split(",")
        if line_split[1] == "":
            line_split[1] = "99"
        cluster_map.update({line_split[0]: line_split[1]})

    for curr_resp in custom_results:
        url_collection = curr_resp["url"][0]
        curr_cluster = cluster_map.get(url_collection, "99")
        curr_resp.update({"cluster": curr_cluster})
        curr_resp.update({"done": "False"})
        

    clust_resp = []
    curr_rank = 1

    for curr_resp in custom_results:
        if curr_resp["done"] == "False":
            curr_cluster = curr_resp["cluster"]
            curr_resp.update({"done": "True"})
            curr_resp.update({"rank": str(curr_rank)})
            curr_rank += 1
            clust_resp.append({"title": curr_resp["title"], "url": curr_resp["url"], "content": curr_resp["content"],
                               "meta_info": curr_resp["meta_info"], "rank": curr_resp["rank"]})
            for remaining_resp in custom_results:
                if remaining_resp["done"] == "False":
                    if remaining_resp["cluster"] == curr_cluster:
                        remaining_resp.update({"done": "True"})
                        remaining_resp.update({"rank": str(curr_rank)})
                        curr_rank += 1
                        clust_resp.append({"title": remaining_resp["title"], "url": remaining_resp["url"],
                                           "content": remaining_resp["content"],
                                           "meta_info": remaining_resp["meta_info"], "rank": remaining_resp["rank"]})
    
    return clust_resp



if __name__ == '__main__':
    app.run(debug=True)