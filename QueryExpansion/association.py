import re

import numpy as np
from nltk.corpus import stopwords
from nltk import PorterStemmer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import pysolr
import json
from tqdm import tqdm
from collections import defaultdict, Counter
import heapq

porter_stemmer = PorterStemmer()
stop_words = set(stopwords.words('english'))


def tokenize_text(text):
    # remove enters
    text = text.replace('\n', ' ')
    # convert to lowercase
    text = text.lower()
    # tokenize text
    tokens = word_tokenize(text)
    # remove punctuation and numbers
    tokens = [token for token in tokens if token.isalpha()]
    # remove stop words
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token not in stop_words]
    
    return tokens

def make_stem_map(vocab):
    """
    Args:
        vocab(list): a list of vocabulary

    Returns:
        token_2_stem(dict): a map from token to its stem having structure {token:stem}
        stem_2_tokens(dict): a map from stem to its corresponding tokens having structure:
                             {stem:set(token_1, token_2, ...)}
    """
    token_2_stem = {} # 1 to 1
    stem_2_tokens = {} # 1 to n

    for token in vocab:
        stem = porter_stemmer.stem(token)
        if stem not in stem_2_tokens:
            stem_2_tokens[stem] = set()
        stem_2_tokens[stem].add(token)
        token_2_stem[token] = stem

    return token_2_stem, stem_2_tokens 


def build_association(doc_tokens, token_2_stem, stem_2_tokens, query, num_expansions=1):
    """
    Args:
        doc_tokens(2-D list): tokens in each documents having structure:
                              [[token_1, token_2, ...], [...], ...]
        token_2_stem(dict): a map from token to its stem having structure {token:stem}
        stem_2_tokens(dict): a map from stem to its corresponding tokens having structure:
                             {stem:set(token_1, token_2, ...)}
        query(list): a list of tokens from query
        num_expansions(int): the number of expansion tokens to return for each query token
        
    Return:
        query_expands(list): list of expand stem tokens ids for each token in the query
    """
    # build map from stem to index
    stems = sorted(stem_2_tokens.keys())
    stem_2_idx = {s: i for i, s in enumerate(stems)}

    # frequency of stems in each document
    f = np.zeros((len(doc_tokens), len(stems)), dtype=np.int64)
    for doc_id, tokens in enumerate(doc_tokens):
        stems_in_doc = set(token_2_stem.get(t, t) for t in tokens)
        stem_counts = Counter(stems_in_doc)
        for stem, count in stem_counts.items():
            f[doc_id, stem_2_idx[stem]] = count

    # correlation matrix
    c = np.dot(f.T, f)

    # normalize correlation matrix and pick the top expansion tokens
    query_expands_id = []
    for token in query:
        stem = token_2_stem.get(token, token)
        stem_id = stem_2_idx.get(stem)
        if stem_id is None:
            continue

        # normalize correlation matrix for the query token
        c_token = c[stem_id, :]
        norm = np.linalg.norm(c_token)
        if norm == 0:
            continue
        s_token = c_token / norm

        # pick the top expansion stems for each query token
        idx_sort = heapq.nlargest(num_expansions + 1, range(len(s_token)), key=s_token.__getitem__)
        if stem_id in idx_sort:
            idx_sort.remove(stem_id)  # remove the original stem from the list of expansions
        else:
            idx_sort.pop()  # remove the last expansion stem to keep only num_expansions stems
        query_expands_id.extend(idx_sort)

    # convert stem ids to stem
    query_expands = [stems[stem_idx] for stem_idx in query_expands_id]

    return query_expands
                          



def association_main(query, solr_results):
    """
    Args:
        query(str): a text string of query
        solr_results(list): result for the query from function 'get_results_from_solr'

    Return:
        query(str): a text string of expanded query
    """
    # query = 'olympic medal'
    # solr = pysolr.Solr('http://localhost:8983/solr/nutch/', always_commit=True, timeout=10)
    # results = get_results_from_solr(query, solr)
    vocab = set()
    doc_tokens = []

    # tokenize query and query results, then build vocabulary
    query_text = query # keep original query text

    print("query text ==", query_text)

    if 'content:' == query[:8]:
        query = query[8:]
    print("Initial Query ", query)
    query = tokenize_text(query)
    vocab.update(query)

    for result in tqdm(solr_results, desc='Preprocessing results'):
        if 'content' not in result:
            tokens = set()
        else:
            tokens = set()

            for token in result['content']:
                tokens.update(tokenize_text(token))

        doc_tokens.append(tokens)
        vocab.update(tokens)

        print(vocab)

    vocab = list(sorted(vocab))
    token_2_stem, stem_2_tokens = make_stem_map(vocab)

    # expand query
    query_expands_stem = build_association(doc_tokens, token_2_stem, stem_2_tokens, query)
    
    # convert from stem to tokens
    query_expands = set()
    for stem in query_expands_stem:
        query_expands.update(list(stem_2_tokens[stem]))

    # generate new query
    for token in query:
        query_expands.discard(token)

    # update query with query expands 
    expanded_query = list()
    expanded_query.extend(query)
    expanded_query.extend(list(query_expands))
    query = expanded_query

    query = ' '.join(query)
    print('Expanded query:', query)

    return query