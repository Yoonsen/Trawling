import json
import sqlite3
import requests
import pandas as pd
import dask
import pandas as pd
import dhlab.module_update as mu
mu.update('mods_meta')
import mods_meta as mm
import dhlab.nbtext as nb
import re
from IPython.display import Markdown
from collections import Counter
from dhlab.nbtokenizer import tokenize

mu.update('collocations')


import collocations as coll

def categorize(list_of_words):
    proprium = [x for x in list_of_words if x[0].upper() == x[0]]
    other = [x for x in list_of_words if not x in proprium]

    return {'propr':proprium,
           'other': other }

def nb_search(
    term = '', creator = '', 
    number = 50, 
    page = 0, 
    mediatype = 'bøker', 
    lang = "nob",
    period = (18000101, 20401231)
):
    """Søk etter term og få ut json"""
    
    number = min(number, 50)
    
    filters = []
    aq = []
    

    params = {
        'page':page, 
        'size':number
    }
    
    if lang != '':
        aq.append('languages:{lang}'.format(lang = lang ))
    
    if creator != '':
        filters.append('creator:{c}'.format(c=creator))
    
    if mediatype != '':
        filters.append('mediatype:{mediatype}'.format(mediatype=mediatype))
    
    if period != ():
        filters.append('date:[{date_from} TO {date_to}]'.format(date_from = period[0], date_to = period[1]))
    
    if filters != []:
        params['filter'] = filters
    
    if aq != []:
        params['aq'] = aq
        
    if term != '':
        params['q'] = term
    
    r = requests.get("https://api.nb.no:443/catalog/v1/items", params = params)
    return r.json()

def find_urns_sesam(term = '', creator = '', number=50, page=0, lang='nob', mediatype='bilder', period=()):
    """generates urls from super_search for pictures"""
    x = nb_search(
        term = term, creator = creator, 
        number = number, page = page, mediatype=mediatype, period = period, 
        lang = lang
    )
    try:
        sesamid =[
            f['id']
            for f in x['_embedded']['items'] 
            if 'thumbnail_custom' in f['_links']
        ]
    except:
        sesamid = []
    return sesamid


def fetch_keys(m, path, delimiter = "/", res = [], start_list = '#'):
    """path /-delimited string, return res if fails, array indices indicaed with start_list"""
    
    # get the sequence of path elements
    path = path.split(delimiter)
    
    x = m
    try:
        for i in range(0, len(path)):
            if path[i].startswith(start_list):
                # then the item is an array selector
                index = int(path[i].split(start_list)[-1])
                x = x[index]
            else:
                x = x[path[i]]
    except KeyError:
        x = res
    return x
        
def find_item(data, item):
    res = []
    if isinstance(data, list):
        print('list', data)
        for subdata in data:
            res += find_item(subdata, item)
    elif isinstance(data, dict):
        for key in data:
            if item in data[key]:
                print('dictvalue',key, data[key])
                res.append(data[key][item])
            else:
                res += find_item(data[key], item)
    return res

def metadata(id):
    r = requests.get("https://api.nb.no:443/catalog/v1/items/" + str(id))

    d = r.json()
    res = {
        'title': fetch_keys(d, 'metadata/title'),
        'contr':[(fetch_keys(x, 'name'), fetch_keys(x, 'roles/#0/name')) for x in fetch_keys(d, 'metadata/people')],
        'pages': fetch_keys(d, 'metadata/physicalDescription/extent'),
        'urn': fetch_keys(d, 'metadata/identifiers/urn'),
        'year': fetch_keys(d, 'metadata/originInfo/issued'),
        'topics':fetch_keys(d, 'metadata/subject/topics'),
        'genres': fetch_keys(d, 'metadata/genres'),
        'target_group':fetch_keys(d, 'metadata/targetAudienceNotes')
                            
    }

    return res

def get_attribute(data, attribute, default_value=''):
    if data:
        if attribute in data:
            return data[attribute]
        else:
            return default_value
    else:
        return default_value


def iiif_search(ident, querystring):
    with requests.session() as sesjon:
        r = sesjon.get('https://api.nb.no/catalog/v1/contentsearch/%s/search' % (ident), params = {'q': querystring})
        jsonObj = r.json()
        concRows = []

        if 'hits' in jsonObj:
            # return a dictionary per hit
            for hit in jsonObj['hits']:
                if 'match' in hit:
                    matchDict = {}
                    matchDict['identifier'] = ident
                    matchDict['word'] = hit['match']
                    #matchDict['annotations'] = get_attribute(hit, 'annotations')
                    matchDict['before'] = get_attribute(hit, 'before')
                    matchDict['after'] = get_attribute(hit, 'after')
                    concRows.append(matchDict)
        else:
            # return empty list if object is not found
            return []
    return concRows

def get_konks(urn, phrase, window=1000, n = 1000):
    import requests
    
    querystring = '"'+ phrase +'"' 
    query = {
        'q':querystring,
        'fragments': n,
        'fragSize':window
       
    }
    with requests.session() as sesjon:
        r = sesjon.get("https://api.nb.no/catalog/v1/items/{urn}/contentfragments".format(urn=urn), params = query)
        res = r.json()
        results = []
        try:
            for x in res['contentFragments']:
                pid = x['pageid']
                hit = x['text']
                splits = hit.split('<em>')
                s2 = splits[1].split('</em>')
                before = splits[0]
                word = s2[0]
                after = s2[1]
                results.append({'urn': urn, 'before': before, 'word':word, 'after':after})
        except:
            True
    return results

def get_konkordanser(word = '', urns = None):
    konks = []
    for u in urns:
        urn_pref = "URN:NBN:no-nb_digibok_"
        if not "URN" in str(u):
            u = urn_pref + str(u)
        konks += iiif_search(u, word)
    return konks

def konks(w):
    print(w)
    return get_konkordanser(word = w, urns = list(set(list(df.urn))))

    

def collocations_from_nb(word, corpus, func = get_konkordanser):
    """Get a concordance, and count the words in it. Assume konks reside a dataframe with columns 'after' and 'before'"""
    concordance = nb.frame(func(word, corpus))
    return nb.frame_sort(nb.frame(Counter(tokenize(' '.join(concordance['after'].values + concordance['before'].values))), word))

def count_from_conc(concordance):
    """From a concordance, count the words in it. Assume konks reside a dataframe with columns 'after' and 'before'"""
    word = concordance['word'][0]
    return nb.frame_sort(nb.frame(Counter(tokenize(' '.join(concordance['after'].values + concordance['before'].values))), word))



def konk_mot_nb(word, urns, processes = 50, filename = 'temporary_filename_nbkonk.json', program = 'multi_konk.py'):
    """For concordance against a larger corpus, hundreds of books"""
    
    # store URNs in a filename
    with open(filename, 'w') as f:
        json.dump([str(x) for x in urns], f)

    res_byte = sb.run(['python', program, word, str(processes), filename], stdout=PIPE)

    # decode result from conc
    try:
        res_string = res_byte.stdout.decode('utf-8')
    except:
        res_string = res_byte.stdout.decode('cp1252')
    
    # pick out non empty hits
    
    
    #result = [konk for k in json.loads(res_string) if k != [] for konk in k]
    
    return res_string

from time import time

def collocations_nb_parallell(word, corpus, processes = 20, printword = True):
    """a word and a corpus as a dataframe with URNs as index"""
    t = time()
    konk = konk_mot_nb(word, [str(x) for x in corpus.index], processes = processes)
    konks = [k for y in json.loads(konk) if y != [] for k in y]
    if printword:
        print(word, time() - t)
        t = time()
    try:
        res = count_from_conc(pd.DataFrame(konks))
    except:
        res = []
    return res



