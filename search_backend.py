from flask import Flask, render_template, url_for, request
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from nltk import WordNetLemmatizer
import string
from flask_cors import CORS
from QueryExpansion.association import association_main
from QueryExpansion.metric import metric_cluster_main
import os, requests, json, re, html
from spellchecker import SpellChecker
from operator import itemgetter
from nltk.corpus import stopwords
from nltk.tokenize import wordpunct_tokenize
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pysolr

app = Flask(__name__)
CORS(app)
solr = pysolr.Solr('http://localhost:8983/solr/nutch', timeout=10)

@app.route("/", methods = ['GET', 'POST'])
def home_page():
    google_results = []
    bing_results = []
    selected_value = 'page-rank' # set selected query to page rank by default

    if request.method == 'POST':
        query = request.form['query']
        user_selection = request.form.get('selection')
        selected_value = user_selection

        # results for custom search, google and bing
        custom_results = custom_search(query)

        if is_hits(user_selection):
            custom_results = get_hits_results(custom_results)

        elif is_clustering(user_selection):
            custom_results = get_clustering_results(query, custom_results, user_selection)

        elif is_query_expansion(user_selection):
            query, custom_results = query_expansion(query, custom_results, user_selection)  
                  
        return render_template('index.html', custom_results = custom_results, google_results=google_results, bing_results=bing_results, query=query, selected_value=selected_value)
    
    return render_template('index.html', google_results=google_results, bing_results=bing_results, selected_value=selected_value)

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
        custom_results = custom_search(query)
        print(custom_results[0])
    elif selection == 'metric-expansion':
        expanded_query = metric_cluster_main(query, custom_results)
        custom_results = custom_search(expanded_query)
    elif selection == 'scalar-expansion':
        # Extract the relevant and non-relevant documents from the results
        relevant_docs = [doc['content'][0] for doc in custom_results[:30]]   # Assume the top 5 documents are relevant
        nonrelevant_docs = [doc['content'][0] for doc in custom_results[-30:]]   # Assume the last 5 documents are non-relevant
        #expanded_query = rocchio(query.split(), relevant_docs, nonrelevant_docs)
        expanded_query = metric_cluster_main(query, custom_results)
        custom_results = custom_search(expanded_query)

        #custom_results = custom_search(' '.join(expanded_query))
        
    
    return (expanded_query, custom_results)



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
    updated_query = ' '.join(tokenizer(query))
    results = None

    while (results is None or len(results) == 0 and len(updated_query) > 0):
        results = solr.search('text:' + f"\"{updated_query}\"", **{
            'fl': 'id, title, url, anchor, content, meta_info, digest',  # Select the fields to return
            'rows': 100
        })

        updated_query = slice_from_back(updated_query)
        print(updated_query)

    docs = [create_doc(result) for result in results.docs]
    return docs

def slice_from_back(s):
    print("s == ", s)
    words = s.split()  # split the input string into words
    if len(words) > 0:
        words.pop()  # remove the last word
    return ' '.join(words)  # join the remaining words together with spaces and return the resulting string


def get_hits_results(clust_inp):
    authority_score_file = open("RelevanceModel/authority_score_1", 'r').read()
    authority_score_dict = json.loads(authority_score_file)

    clust_inp = sorted(clust_inp, key=lambda x: authority_score_dict.get(x['url'][0], 0.0), reverse=True)

    return clust_inp

def tokenizer(query):
    # remove stop words
    english_stopwords = stopwords.words("english")

    # tokenize extracted_text
    formatted_text = wordpunct_tokenize(query)

    # remove stop words
    stop_words_removed = [token for token in formatted_text if token not in english_stopwords]

    # remove punctuation
    punctuation_removed = [token for token in stop_words_removed if token not in string.punctuation]

    # lemmatize
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(token) for token in punctuation_removed]

    return tokens

def get_clustering_results(query, results, user_selection):
    if (user_selection == 'flat-clustering'):
        print("user selection is " + user_selection + " processing flat_clustering" )
        return process_results(query, results, 'flat_clustering.txt')
    
    print("user selection is " + user_selection + " processing hierarchical_clustering" )
    return process_results(query, results, 'hierarchical_clustering.txt')
    

def process_results(query, results, clusters_file):
    # Parse the URL clusters from the text file
    clusters = {}
    with open(clusters_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            try:
                url, value = line.split(',', maxsplit=1)
                clusters[url] = float(value)
            except ValueError:
                pass
    
    # Extract the text from the query and results
    texts = [query] + [result['content'][0] for result in results]
    
    # Create a bag-of-words representation of the texts
    vectorizer = CountVectorizer()
    vectors = vectorizer.fit_transform(texts)
    
    # Compute the cosine similarity between the query and each result
    similarities = cosine_similarity(vectors[0:1], vectors[1:]).flatten()
    
    # Adjust the similarity scores based on the URL clusters
    for i, result in enumerate(results):
        url = result['url'][0]
        if url in clusters:
            cluster_value = clusters[url]
            cluster_value = clusters[url]
            similarities[i] *= cluster_value
    
    # Rank the results by their similarity to the query
    ranked_results = sorted(results, key=lambda result: (similarities[results.index(result)], clusters.get(result['url'][0], 0)), reverse=True)
    
    
    return ranked_results


    


if __name__ == '__main__':
    app.run(debug=True)