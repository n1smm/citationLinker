import pymupdf
import re
from inParenthesesExtractor import check_in_parentheses
from configLoad import config
from utils import years_span_parser, soft_year_expand, years_sort, alternative_names_concat

# Preveri posebne primere iz konfiguracije
def check_special_case(author_token, page, page_idx):
    for special_case in config['SPECIAL_CASE']:
        if special_case in author_token:
            position = page.search_for(author_token, quads=False)
            return {
                "year": "0",
                "surname": "special_case",
                "name": "xxx",
                "text": author_token,
                "position": position,
                "page": page_idx,
                "years": ["xxx"],
                "year_span": "xxx",
                "others": ["xxx"],
            }
    return None

# Poišči letnice in letnične razpone v nizu
def find_years(author_token):
    year_search_pattern = re.compile(r'(?<!\d)(\d{4}[a-zA-Z]?)(?!\d)')
    years_span_pattern = re.compile(r'\d{4} {0,2}[-–—]{1,2} {0,2}\d{4}')
    year_matches = year_search_pattern.findall(author_token)
    year_span_matches = years_span_pattern.findall(author_token)
    return year_matches, year_span_matches

# Razdeli niz na tokene
def tokenize(author_token):
    tokens = re.split(r'[\s.,;:()\[\]{}!?]+', author_token)
    return [t for t in tokens if t]

# Poišči indeks letnice ali letničnega razpona v tokenih
def find_year_index(tokens, year_matches, year_span_matches):
    if year_matches and not year_span_matches:
        return next(i for i, tok in enumerate(tokens) if year_matches[0] in tok)
    elif year_span_matches:
        idx = next((i for i, tok in enumerate(tokens) if year_span_matches[0] in tok), None)
        if idx is not None:
            return idx
        return next((i for i, tok in enumerate(tokens) if year_matches[0] in tok))
    return None

# Poišči priimek in ime pred letnico
def find_surname_and_name(tokens, year_idx):
    surname = ""
    name = ""
    if year_idx > 0 and tokens[year_idx - 1][0].isupper():
        surname = tokens[year_idx - 1]
    else:
        for i in range(year_idx - 2, max(year_idx - 5, -1), -1):
            if tokens[i].strip() and tokens[i][0].isupper():
                surname = tokens[i]
                break
    for i in range(year_idx - 2, max(year_idx - 5, -1), -1):
        if tokens[i][0].isupper() and tokens[i] != surname:
            name = tokens[i]
            break
    return surname, name

# Če ni imena/priimka in je prvi token leto, vzemi iz prejšnjega reference
def check_previous_ref(ref, last_ref, year_idx, surname, name):
    if not name and not surname and year_idx == 0 and not ref["outside_name"]:
        if last_ref:
            surname = last_ref["surname"]
    return surname, name

# Obdelaj letnice in letnične razpone
def process_years(year_matches, year_span_matches, years):
    new_years = []
    year_span = ""
    if year_span_matches:
        new_years = years_span_parser(year_span_matches[0], years)
        if len(years) >= 2:
            year_span = f"{years[0]}-{years[-1]}" or "xxx"
        else:
            year_span = "xxx"
    if not year_span_matches or not years:
        new_years = soft_year_expand(year_matches[0], "xxx")
        year_span = f"{new_years[0]}-{new_years[-1]}" or "xxx"
    return new_years, year_span

# predela in razdeli vse relevantne informacji za vsako potencialno referenco
# posebni primeri so uvozeni iz .config file-a npr "nav. d."
# drugi posebni primer (avtor leto; leto) doda tudi v drugi token avtorja
# vrne strukturo z razdelanimi informacijami za eno potencialno referenco
def split_info(ref, author_token, page_idx, page, last_ref):
    # Preveri posebni primer
    special = check_special_case(author_token, page, page_idx)
    if special:
        return special

    # Poišči letnice in letnične razpone
    year_matches, year_span_matches = find_years(author_token)
    if not year_matches and not year_span_matches:
        return None

    # Tokeniziraj avtorjev niz
    tokens = tokenize(author_token)
    year_idx = find_year_index(tokens, year_matches, year_span_matches)
    if year_idx is None:
        return None

    # Poišči priimek in ime
    surname, name = find_surname_and_name(tokens, year_idx)
    surname, name = check_previous_ref(ref, last_ref, year_idx, surname, name)

    # Zberi dodatne letnice
    years = []
    if len(year_matches) > 1:
        for match in year_matches[1:]:
            years.append(match)

    # Obdelaj letnice in letnične razpone
    new_years, year_span = process_years(year_matches, year_span_matches, years)
    if new_years and len(new_years) > 1:
        years.extend(new_years)
    years = years_sort(years)

    # Poišči pozicijo v strani
    position = page.search_for(author_token, quads=False)
    if not position:
        return None

    others = []
    for t in tokens:
        others.extend(alternative_names_concat(t))
    others.extend(alternative_names_concat(author_token))
    if not others or len(others) < 1:
        others.append("xxx")


    # Sestavi rezultat
    ref_info = {
        "year": year_matches[0],
        "surname": surname or "xxx",
        "name": name or "xxx",
        "text": author_token or "xxx",
        "position": position,
        "page": page_idx,
        "years": years or ["xxx"],
        "year_span": year_span or "xxx",
        "others": others,
    }
    return ref_info


# TODO - ce je outside_name ampak notri razdeljeno z ; pomeni da so vse letnice isti avtor
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
        print("-------")
        if ref["others"] and ref["others"][0] != "xxx":
            for other in ref["others"]:
                print(f"other: {other}")
        if ref["years"] and ref["years"][0] != "xxx":
            for year in ref["years"]:
                print(f"year: {year}")
            print("span: ", ref["year_span"])
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

    

