from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import json

def get_cluster_results(file_path):
    cluster_results = {}
    with open(file_path, 'r') as f:
        for line in f:
            try:
                url, cluster_id = line.strip().split(',')
                cluster_id = float(cluster_id)
                if cluster_id not in cluster_results:
                    cluster_results[cluster_id] = []
                cluster_results[cluster_id].append(url)
            except ValueError:
                pass
    return cluster_results

def generate_centroids():
    np.set_printoptions(threshold=np.inf)
    cluster_results = get_cluster_results('../flat_clustering.txt')
    url_to_cluster = {}

    for cluster_id, urls in cluster_results.items():
        for url in urls:
            url_to_cluster[url] = cluster_id

    # Fit a TfidfVectorizer on all URLs from all clusters
    urls = []
    
    for cluster_id, cluster_urls in cluster_results.items():
        urls.extend(cluster_urls)

    vectorizer = TfidfVectorizer()
    vectorizer.fit(urls)

    # Precompute the feature vectors for all URLs
    url_to_feature_vector = {}
    feature_vectors = vectorizer.transform(urls).toarray()

    for url, feature_vector in zip(urls, feature_vectors):
        url_to_feature_vector[url] = feature_vector

    # Precompute the centroid for each cluster
    cluster_centroids = {}

    for cluster_id, urls in cluster_results.items():
        # You can compute the centroid of the cluster by averaging the precomputed feature vectors of all the URLs in the cluster
        feature_vectors = np.array([url_to_feature_vector[url] for url in urls])
        centroid = np.mean(feature_vectors, axis=0)
        cluster_centroids[cluster_id] = centroid.tolist()

    return cluster_centroids
   

clustered_results = generate_centroids()


with open('cluster_centroids.json', 'w') as f:
    json.dump(clustered_results, f)



