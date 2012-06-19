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
    term = unicodedata.normalize('NFKD', unicode(term)).encode('ASCII', 'ignore')
    term = term.strip()
    term = term.replace('&', 'and')
    term = re.sub(r'[\s]+', ' ', term)
    term = re.sub(settings.CHARACTER_FILTER, '', term)
    return term


def get_autocompleter_phrases_for_term(term, max_words=None):
    """
    For any term, given the whole phrases the autocompleter can match on
    """
    words = term.split()
    num_words = len(words)
    phrases = []

    if max_words != None:
        for i in range(0, num_words):
            phrases.append(' '.join(words[i:i + max_words]))
    else:
        for i in range(0, num_words):
            phrases.append(' '.join(words[i:num_words]))

    return phrases


def get_all_variations(term, phrase_aliases):
    """
    Given the term and dict of phrase to phrase alias mappings,
    return all perumations of term with possible alias phrases substituted
    """
    term_stack = [term]
    term_aliases = {term: 1}
    while len(term_stack) != 0:
        term = term_stack.pop()
        phrase_map = get_phrase_index_for_term(term)
        for phrase in phrase_map.keys():
            if phrase in phrase_aliases:
                phrase_alias = phrase_aliases[phrase]
                start_end = phrase_map[phrase]
                phrase_start = start_end[0]
                phrase_end = start_end[1]
                term_words = term.split()
                term_words[phrase_start:phrase_end] = [phrase_alias]
                term_alias = ' '.join(term_words)
                if term_alias not in term_aliases:
                    term_aliases[term_alias] = 1
                    term_stack.append(term_alias)
    return term_aliases.keys()


def get_phrase_index_for_term(term):
    """
    For an term, return of index of every phrase in the term to it's
    word position (start word number, end word number,) within the term.

    Note: if a phrase appears twice in a term, then the very last position
    will be recorded. For our purposes, this works because other occurences
    will be handled when this function is called recursively
    """
    words = term.split()
    num_words = len(words)
    phrase_map = {}
    for i in range(0, num_words):
        for j in range(1, num_words + 1):
            if i >= j:
                continue
            phrase = ' '.join(words[i:j])
            phrase_map[phrase] = (i, j,)
    return phrase_map
