from multiprocessing import Pool
import sys
import json
import requests

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

    


# parameters are

word = sys.argv[1]
process_count = sys.argv[2]
file = sys.argv[3]

def kf(u):
    urn_pref = "URN:NBN:no-nb_digibok_"
    if not "URN" in str(u):
        u = urn_pref + str(u)
    return get_konks(u, word)
    


with open(file) as f:
    urns = json.load(f)

if __name__ == '__main__':
    p = Pool(int(process_count))
    res = p.map(kf, urns)
    p.close()
    p.terminate()
    print(json.dumps(res))
