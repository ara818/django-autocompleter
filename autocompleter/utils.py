import re
import unicodedata

from autocompleter import settings

def get_normalized_term(term):
    """
    Convert the term into a basic form that's easier to search.
    1) Force convert from text to unicode if necessary
    2) Make lowercase
    3) Convert to ASCII, switching characters with accents to their non-accented form
    4) Trim white space off end and beginning
    4) Replace & with and
    5) Replace extra spaces
    6) Remove all characters that are not alphanumeric
    """
    if type(term) == str:
        term = term.decode('utf-8')
    term = term.lower()
    term = unicodedata.normalize('NFKD', unicode(term)).encode('ASCII','ignore')
    term = term.strip()
    term = term.replace('&', 'and')
    term = re.sub(r'[\s]+', ' ', term)
    term = re.sub(settings.CHARACTER_FILTER, '', term)
    return term

def get_prefixes_for_term(term):
    """
    For any term, give the autocomplete prefixes
    """
    words = term.split()
    num_words = len(words)
    prefixes = []
    for i in range(0, num_words):
        prefixes.append(' '.join(words[i:num_words]))
    
    return prefixes
        