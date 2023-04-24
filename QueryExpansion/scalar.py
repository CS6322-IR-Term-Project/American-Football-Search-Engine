from nltk.corpus import stopwords
from nltk.tokenize import wordpunct_tokenize
from nltk import WordNetLemmatizer
from tqdm import tqdm
import string
from collections import defaultdict, Counter

from sklearn.feature_extraction.text import TfidfVectorizer

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
                          
def extract_cooccurring_terms(tfidf_matrix, feature_names, query_tokens):
    # Extract co-occurring terms
    cooccurring_terms = Counter()
    for doc_index in range(tfidf_matrix.shape[0]):
        for term_index in tfidf_matrix[doc_index].nonzero()[1]:
            term = feature_names[term_index]

            if term in query_tokens:
                row = tfidf_matrix[doc_index].tocoo()
                cooccurring_terms.update([feature_names[i] for i in row.col if i != term_index])

    return cooccurring_terms


def association_main(query, solr_results):
    query_token = tokenizer(query)
    documents_processed = []

    for result in solr_results:
        document = result['content'][0]
        document_tokens = tokenizer(document)
        doc_str = ' '.join(document_tokens)
        documents_processed.append(doc_str)
    
    # Create custom stop words list
    custom_stop_words = ['button', 'bar', 'app', 'account', 'shop', 'main', 'about', 'skip', 'watch', 'link', 'file', 'upload', 'ref', 'edit', 'content', 'html', 'head', 'body', 'href', 'src', 'alt', 'header', 'footer', 'nav', 'menu', 'search', 'com']

    # Build TF-IDF Vectorizer
    tfidf = TfidfVectorizer(stop_words=custom_stop_words)
    tfidf_matrix = tfidf.fit_transform(documents_processed)

    # get the feature names
    feature_names = tfidf.get_feature_names_out()

    # find co-occuring terms
    cooccurring_terms = extract_cooccurring_terms(tfidf_matrix, feature_names, query_token)

    #(cooccurring_terms)

    # Filter terms
    filtered_terms = []

    for term, count in cooccurring_terms.items():
        if count > 1 and count < len(solr_results) and len(term) > 2:
            filtered_terms.append(term)
    
    feature_names = tfidf.get_feature_names_out()
    tfidf_scores = tfidf.transform([query]).toarray()[0].tolist()
    
    ranked_terms = sorted(zip(feature_names, tfidf_scores), key=lambda x: (x[1], cooccurring_terms[x[0]]), reverse=True)
    
    # Rank and add terms
    expanded_query = query

    for term, _ in ranked_terms:
        if term not in query.split():
            expanded_query += " " + term
            if len(expanded_query.split()) > 5:
                break
    
    print("expanded query ==", expanded_query)

    return expanded_query

