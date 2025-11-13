import pymupdf
import re
from inParenthesesExtractor import check_in_parentheses
from configLoad import config


# predela in razdeli vse relevantne informacji za vsako potencialno referenco
# posebni primeri so uvozeni iz .config file-a npr "nav. d."
# drugi posebni primer (avtor leto; leto) doda tudi v drugi token avtorja
# vrne strukturo z razdelanimi informacijami za eno potencialno referenco
def split_info(ref, author_token, page_idx, page, last_ref):
    #posebni primer
    for special_case in config['SPECIAL_CASE']:
        if special_case in author_token:
            position = page.search_for(author_token, quads=False)
            ref_info = { 
                        "year": "0",
                        "surname": "special_case",
                        "name": "xxx",
                        "text": author_token,
                        "position": position,
                        "page": page_idx
                        }
            return ref_info
    
    #preglej letnico, tokeniziraj, najdi index letnice v toknih
    year_search_pattern = re.compile(r'(?<!\d)(\d{4}[a-zA-Z]?)(?!\d)')
    year_matches = year_search_pattern.findall(author_token)
    if not year_matches:
        # print("sth wrong with finding year in :", author_token)
        return None
    tokens = re.split(r'[\s.,;:()\[\]{}!?]+', author_token)
    tokens = [t for t in tokens if t]
    year_idx = next(i for i, tok in enumerate(tokens) if year_matches[0] in tok)

    # preglej token ali 2 pred letnico in jih smatraj kot 1. priimek, 2. ime
    surname = ""
    name = ""
    # if tokens[year_idx -1] and tokens[year_idx -1][0].isupper():
    for i in range(year_idx - 2, max(year_idx - 5, -1), -1):
        if tokens[i].strip()[0].isupper():
            surname = tokens[i]
    for i in range(year_idx - 2, max(year_idx - 5, -1), -1):
        if tokens[i][0].isupper() and tokens[i] != surname:
            name = tokens[i]
            break
    # if year_idx >= 2 and tokens[year_idx - 2] and tokens[year_idx - 2][0].isupper():
    #     name = tokens[year_idx - 2]

    # ce ni imena/priimka in je prvi token leto, 
    # ter ni navajanja zunaj oklepaja vzami iz prejsnjega priimek ali ime
    # to je posebni primer kjer se v oklepaju navaja dva dela istega avtorja
    if not name and not surname and year_idx == 0 and not ref["outside_name"]:
        if last_ref:
            surname =  last_ref["surname"]

    #iskanje tocne pozicije
    position = page.search_for(author_token, quads=False)
    if not position:
        # print("no position found for ", author_token, ", page: ", page_idx)
        return None


    #struktura ki se jo bo dodalo v slovar potencialnih referenc
    ref_info = ({
        "year": year_matches[0],
        "surname": surname or "xxx",
        "name": name or "xxx",
        "text": author_token or "xxx",
        "position": position,
        "page": page_idx
        })

    return ref_info

# reference iz temp_refs, ki so drugacne za vsako stran, jih prenese v references_info
# se z nekaj dodatnimi informacijami
def add_info_to_references(temp_refs, page, page_idx, references_info):
    for ref in temp_refs:
        text = ref["text"]
        author_tokens = []
        #mozno da sta dva avtorja v oklepaju, razdeli v tokne
        if not ref["outside_name"]:
            author_tokens = re.split(r'[;]', text)
        else:
            author_tokens = [text]
        #vnasanje podrobnejsih informacij v references_info iz toknov
        for token in author_tokens:
            last_ref = references_info[-1] if references_info and len(references_info) > 0 else None
            curr_ref = split_info(ref, token, page_idx, page, last_ref)
            if curr_ref:
                references_info.append(curr_ref)

# debuging oz. za preverjanje koncega slovarja najdenih referenc: references_info
def print_references_info(references_info):
    for ref in references_info:
        if not ref:
            continue
        print(f"year: {ref.get('year', '')}")
        print(f"surname: {ref.get('surname', '')}")
        print(f"name: {ref.get('name', '')}")
        print(f"text: {ref.get('text', '')}")
        print(f"position: {ref.get('position', '')}")
        print(f"page: {ref.get('page', '')}")
        print("\n------------------\n")
#debug print za temp ref
def print_temp_ref_text(temp_refs):
    print('\n'.join(ref["text"] for ref in temp_refs))    
    print("----------------------------------------")

# precesa celoten tekst in izbere dele k bi lahko bili reference,
# zakljuci ko pride do virov
# TODO precesaj se zadnjo stran pred literaturo
def screen_text(doc, page_idx, delimiter):

    references_info = []

    for i in range(0, page_idx + 1):
        page = doc[i]
        text = page.get_text()
        temp_refs = check_in_parentheses(text) #inParenthesesExtractor.py
        add_info_to_references(temp_refs, page, i, references_info)
        if i == page_idx:
            break
    #sprocesiraj se zadnjo stran do literature
    page = doc[page_idx]
    text = page.get_text()
    delimiter_index = text.find(delimiter)
    if delimiter_index != -1:
        text = text[:delimiter_index]
    temp_refs = check_in_parentheses(text) #inParenthesesExtractor.py
    add_info_to_references(temp_refs, page, page_idx, references_info)
    print_references_info(references_info)
    return references_info

    

