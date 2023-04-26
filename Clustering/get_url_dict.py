from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import json

def get_url_dict():
    url_dict = {}

    with open('../flat_clustering.txt', 'r') as f:
        for line in f:
            try:
                url, cluster = line.strip().split(',')
                if cluster in url_dict:
                    url_dict[cluster].append(url)
                else:
                    url_dict[cluster] = [url]
            except ValueError:
                pass
    return url_dict

url_dict = get_url_dict()

# Load the precomputed dictionary from the file
with open('flat_clustering_id_url.json', 'w') as f:
    json.dump(url_dict, f)