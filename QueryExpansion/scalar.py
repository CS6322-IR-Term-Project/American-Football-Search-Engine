import re

import numpy as np
from nltk.corpus import stopwords
from nltk import PorterStemmer
from nltk.tokenize import wordpunct_tokenize
import string
#import pysolr
import json
from tqdm import tqdm

porter_stemmer = PorterStemmer()
stop_words = set(stopwords.words('english'))


def tokenizer(query):
    # remove stop words
    english_stopwords = set(stopwords.words("english"))
    custom_stop_words = ['menu', 'button', 'bar', 'app', 'account', 'shop', 'main', 'about', 'skip', 'watch', 'link', 'file', 'upload', 'ref', 'edit', 'content', 'html', 'head', 'body', 'href', 'src', 'alt', 'header', 'footer', 'nav', 'menu', 'search', 'com']
    english_stopwords.update(custom_stop_words)

    # tokenize query
    formatted_text = wordpunct_tokenize(query)

    # remove stop words and punctuation
    tokens = [token.lower() for token in formatted_text if token.lower() not in english_stopwords and token not in string.punctuation]

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

def get_scalar_cluster(doc_tokens, token_2_stem, stem_2_tokens, query):
    """
    Args:
        doc_tokens(2-D list): tokens in each documents having structure:
                              [[token_1, token_2, ...], [...], ...]
        token_2_stem(dict): a map from token to its stem having structure {token:stem}
        stem_2_tokens(dict): a map from stem to its corresponding tokens having structure:
                             {stem:set(token_1, token_2, ...)}
        query(list): a list of tokens from query
        
    Return:
        query_expands(list): ranked list of expand stem tokens ids for each token in the query
    """
    # build map from stem to index
    stems = sorted(stem_2_tokens.keys())
    stem_2_idx = {s:i for i, s in enumerate(stems)}

    # frequency of stems in each document
    f = np.zeros((len(doc_tokens), len(stems)), dtype=np.int64)
    for doc_id, tokens in enumerate(doc_tokens):
        for token in tokens:
            if token in token_2_stem:
                stem = token_2_stem[token]
                stem_idx = stem_2_idx[stem]
                f[doc_id, stem_idx] += 1

    # correlation matrix
    c = np.dot(f.T, f)
    c_diag = np.expand_dims(np.diag(c), axis=0)

    # normalize correlation matrix
    s = c / (c + c_diag + c_diag.T)
    s_norm = np.linalg.norm(s, axis=1)

    # expand query
    query_expands_id = []
    for token in query:
        stem = token_2_stem[token]
        stem_id = stem_2_idx[stem]

        # calculate cosine simialrity for the token with all other stems
        stem_vec = np.expand_dims(s[stem_id, :], axis=0)
        stem_norm = np.linalg.norm(stem_vec)
        s_stem = np.dot(stem_vec, s.T).squeeze()
        s_stem = (s_stem / stem_norm) / s_norm

        # pick the top 4 stems for each query token
        idx_sort = np.argsort(s_stem)[::-1]
        idx_sort = idx_sort[:3]
        query_expands_id.extend(idx_sort.tolist())

    # convert stem ids to stem and rank by score
    query_expands = []
    for i, stem_idx in enumerate(query_expands_id):
        score = s_stem[stem_idx]
        query_expands.append((stems[stem_idx], score))
    
    # sort expanded stems by score in descending order
    query_expands.sort(key=lambda x: x[1], reverse=True)

    output = [stem for stem, score in query_expands]
    
    for i in range(0, len(output)):
        print(output[i])
        if i == 5:
            break


    return output

def scalar_main(query, solr_results):
    """
    Args:
        query(str): a text string of query
        solr_results(list): result for the query from function 'get_results_from_solr'

    Return:
        query(str): a text string of expanded query
    """
    vocab = set()
    doc_tokens = []

    # tokenize query and query results, then build vocabulary
    query = tokenizer(query)
    vocab.update(query)
    for result in solr_results:
        if 'content' not in result:
            tokens = []
        else:
            tokens = tokenizer(result['content'][0])
        doc_tokens.append(tokens)
        vocab.update(tokens)

    vocab = sorted(vocab)
    token_2_stem, stem_2_tokens = make_stem_map(vocab)

    # expand query
    query_expands_stem = get_scalar_cluster(doc_tokens, token_2_stem, stem_2_tokens, query)

    # convert from stem to tokens
    query_expands = set()
    for stem in query_expands_stem:
        query_expands.update(stem_2_tokens[stem])

    # generate new query
    for token in query:
        query_expands.discard(token)
    query.extend(query_expands)
    query = ' '.join(query)

    return query

