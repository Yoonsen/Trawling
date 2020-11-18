from IPython.display import HTML

def konk(corpus, words, n=1):
    
    """n is percent of match - jaccardish"""

    words = [w.strip() for w in words.split()]
    lines = ""
    for p in corpus:
        
        if len(set(words) & set(p)) >= n*len(set(words)):
            line = ' '.join(p)
            for w in words:
                line = line.replace(w, "<span style='color:tomato;'>{w}</span>".format(w=w))
            lines+= "<p>{konk}</p>".format(konk = line)
            #print(line)
    return HTML(lines)