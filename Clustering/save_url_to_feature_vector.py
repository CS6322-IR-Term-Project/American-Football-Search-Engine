from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import json

def save_url_to_feature_vector(solr_results_file, filename):
    with open(solr_results_file, 'r') as f:
        solr_results = json.load(f)
    
    urls = [result['url'][0] for result in solr_results]
    vectorizer = TfidfVectorizer()
    vectorizer.fit(urls)
    feature_vectors = vectorizer.transform(urls).toarray()
    url_to_feature_vector = dict(zip(urls, feature_vectors))
    
    with open(filename, 'w') as f:
        json.dump(url_to_feature_vector, f)

save_url_to_feature_vector("../solr_results.json", "url_to_feature_vector.json")   