
import  pymupdf
import  re
from    enum            import Enum 
from    .utils          import years_span_parser, soft_year_expand, alternative_names_concat
from    .configLoad     import config
from    .appLogger      import get_logger


logger = get_logger()


### poglej vrstice  - ce ima vrstica priimek, ime, leto vzemi ves tekst do naslednjega moznega zacetka elementa, oz konca tektsta
### parser je sestavljen iz FE: npr <priimek> <separator:<,>> <ime> <separator:<,>> <extra char:<(,">> <leto> <extra char:<),">>
### kako je razdeljeno ko je vec avtorjev
### ko imamo ves teks, posljemo v tokenizer da razdeli dele, 
"""
bib_structures = [
    [
        {"type": "Surname"},
        {"type": "separator", "options": [","]},
        {"type": "Name"},
        {"type": "separator", "options": [":,", "::,"]},
        {"type": "extra_char", "value": "("}, ### extra char bi moral biti zmeraj v parih (oklepajni char?)
        {"type": "Year"},
        {"type": "extra_char", "value": ")"},
        {"type": "separator", "options": ["::"]},
        {"type": "Title"},
        {"type": "separator", "options": ["."]},
        {"type": "ignore"}
    ],
    # ... more structures
]

#other option

 compiled_schema = {
   "name": "default_style",
   "elements": [
     {"type": "SURNAME",   "required": True,  "validator": is_capitalized_word},
     {"type": "SEPARATOR", "required": True,  "matcher": one_of([",", ";"])},
     {"type": "NAME",      "required": True,  "validator": is_capitalized_name},
     {"type": "EXTRA_CHAR","required": False, "matcher": one_of(["(", '"', "'"])},
     {"type": "YEAR",      "required": True,  "regex": re.compile(r"\d{4}[a-zA-Z]?")},
     {"type": "EXTRA_CHAR","required": False, "matcher": paired_closer},  # ) or " or '
     {"type": "SEPARATOR", "required": False, "matcher": one_of([":", ".", "—"])},
     {"type": "TITLE",     "required": True,  "validator": is_title_start_upper},
     {"type": "IGNORE",    "required": False}
   ]
 }
"""

# tipi
class Bib_types(Enum):
    SURNAME = 0
    NAME = 1
    TITLE = 2
    YEAR = 3
    SEPARATOR = 4
    EXTRA_CHAR = 5
    IGNORE = 6

# globalni regexi
year_search_pattern = re.compile(r'\d{4}[a-zA-Z]?$')
year_span_pattern = re.compile(r'\d{4} {0,2}[-–—]{1,2} {0,2}\d{4}')

# validatorji
# za preverjanje imena,priimka,naslova, all - ali morajo vse besede imeti veliko zacetnico ali samo prva)
# malo prostora za cca 20% besed niso kapitalizirane
def is_capitalized(text, all=False):
    text = text.strip()
    if not text or not text[0] or not text[0].isupper():
        return False

    if not all:
        return text[0].isupper()

    tokens = text.split()
    upper_count = 0
    for tok in tokens:
        if tok.strip()[0].isupper():
            upper_count += 1
    if upper_count / len(tokens) >= 0.8:
        return True
    return False

# iskanje leta ali razpona npr 1028a ali 1999-2002
# TODO dodaj moznost prepoznavanja ali gre za span ali year
def is_year_or_span(text):
    text = text.strip()
    if bool(year_span_pattern.search(text)):
        return "YEAR_SPAN"
    elif bool(year_span_pattern.search(text)):
        return "YEAR"
    return "IGNORE"

# preveri ce se text ujema z moznimi separatorji ali extra karakterji/ separatorji
def is_separator_or_char(text, char_list=[","]):
    text = text.strip()
    for char in char_list:
        if text == char:
            return True
    return False

# poisci separator ali extra_char
def find_separator_char(text, char_list=[","]):
    text = text.strip()
    idx = -1
    text = ""

    for char in char_list:
        idx = text.find(char)
        if idx != -1:
            return idx

    return idx

        
def validator_selector(text, typ_element):
    typ = typ_element.get("TYPE") or "IGNORE"
    if typ == "SURNAME" and is_capitalized(text, all=True):
        return "SURNAME"

    if typ == "NAME" and is_capitalized(text, all=True):
        return "NAME"

    elif typ == "TITLE" and is_capitalized(text, all=False):
        return "TITLE"

    elif typ == "EXTRA_CHAR" and is_separator_or_char(text, typ_element.get("OPTIONS", "")):
        return "EXTRA_CHAR"

    elif typ == "YEAR":
        return is_year_or_span(text)

    elif typ == "SEPARATOR" and is_separator_or_char(text, typ_element.get("OPTIONS", "")):
        return "SEPARATOR"

    else:
        return "IGNORE"




##pogleda kaj je prvi token, in gleda do separatorja
## morata biti vsaj dva matcha
#def is_valid_type(token, bib_structure):
#    pass


def line_has_author(line_text):
    bib_structures = config.get("BIB_STRUCTURE", "")
    orig_line_text = line_text.strip()

    for struct in bib_structures:
        hits = 0
        line_text = orig_line_text
        for typ_element in struct:
            typ = typ_element.get("type", "").upper()
            if (typ in ("SURNAME", "NAME", "TITLE")
                and line_text and line_text[0].isupper()):
                hits += 1
                
            elif typ in ("SEPARATOR", "EXTRA_CHAR"):
                options = typ_element.get("OPTIONS") or [","]
                options = sorted(options, key=len, reverse=True)

                cut_idx = -1
                used_option = None
                for opt in options:
                    pos = line_text.find(opt)
                    if pos != -1:
                        cut_idx = pos
                        used_option = opt
                        break
                if cut_idx == -1:
                    continue
                line_text = line_text[cut_idx + len(used_option):].strip()

            elif typ == "YEAR":
                if year_search_pattern.search(line_text):
                    hits += 1
            if hits > 2:
                return True
    return False


def content_token_sorting(text, typ_elements, n=1):
    tokens = []

    curr_text = text
    if n == 1:
        valid_type = validator_selector(text, typ_elements[0])
        tokens.append({
            "text": text.strip(),
            "type": valid_type
            })
        return tokens

    elif n > 1 and n < 3:
        for elem in typ_elements[:]:
            if len(curr_text) < 1:
                return tokens
            typ = elem.get("type", "").upper()
            
            if typ == "EXTRA_CHAR":
                char_idx = find_separator_char(text, elem.get("OPTIONS", [""]))
                curr_text = curr_text[char_idx:]
                if char_idx + 1 < len(curr_text):
                    curr_text =  curr_text[:char_idx] + curr_text[char_idx+1:]
                    typ_elements.remove(elem)
                else:
                    curr_text = ""
                    typ_elements.remove(elem)
        if curr_text and curr_text[0] and  len(typ_elements) == 1:
            tokens += content_token_sorting(text, typ_elements, len(typ_elements))
        return tokens

    return tokens

# primerja vse moznosti v token bank in izbere najboljso
def stronger_match(token_bank):

    len = -1
    winner = 0
    for idx,tkns in enumerate(token_bank):
        if len(tkns) > len:
            winner = idx
            len = len(tkns)
    return token_bank[winner]

# naredi dict z vsemi info od bib entry
def create_bib_entry(tokens):
    bib_entry = {
        "surname": "yyy",
        "name":"yyy",
        "year":"yyy",
        "others": [],
        "years": [],
        "year_span": "yyy"
    }
    for tkn in tokens:
        typ = tkn.get("type")
        text = tkn.get("text")
        if typ == "SURNAME":
            bib_entry["surname"] = text or "yyy"
        elif typ == "NAME":
            bib_entry["name"] = text or "yyy"
        # TODO check ce je yearspan ali mora potem tudi prva letnica iz span biti v year
        elif typ == "YEAR":
            bib_entry["year"] = text or "yyy"
            bib_entry["years"].append(text)
        # TODO dodaj se year span v years
        elif typ == "YEAR_SPAN":
            bib_entry["year_span"] = text
        elif typ == "OTHERS":
            bib_entry["others"].append(text)
        # Add more types as needed
    return bib_entry

    


def tokenize_author_entry(line_text):
    bib_structures = config.get("BIB_STRUCTURE", "")

    line_text = ""
    pre_separator_count = 0
    separator_idx = -1
    token_bank = [[]]
    bib_entry = {}

    for struct_idx, struct in enumerate(bib_structures):
        curr_text = line_text
        tokens = token_bank[struct_idx]

        for idx,typ_element in enumerate(struct):
            typ = typ_element.get("type", "").upper()
            pre_separator_count += 1
            # if typ == "EXTRA_CHAR" and separator_idx > 0:
            #     pre_separator_count -= 1
            if typ == "SEPARATOR":
                if pre_separator_count > 2:
                    return # not correct formatting

                options = typ_element.get("OPTIONS") or [","]
                options = sorted(options, key=len, reverse=True)

                separator_idx = find_separator_char(curr_text, options)
                if separator_idx == -1:
                    return ## error not correct formatting
                curr_tokens_text = curr_text[:separator_idx]
                curr_text = curr_text[idx+1:]
                curr_types = typ_element[idx - pre_separator_count:idx]
                curr_tokens = content_token_sorting(curr_tokens_text, curr_types, pre_separator_count)
                tokens.extend(curr_tokens)
                pre_separator_count = 0 #at the end of this block

    tokens = stronger_match(token_bank)
    bib_entry = create_bib_entry(tokens)







# poisce in vrne list[dict] z vsemi informacijami glede avtorjev v bibliografiji
# stil bibliografije lahko doloci uporabnik (za razliko od extract_authors_from_pdf) nekaj v stilu:
# npr <priimek> <separator:<,>> <ime> <separator:<,>> <extra char:<(,">> <leto> <extra char:<),">>
def extract_authors_modular(doc, page_idx, delimiter, ctx=None, article_start_page=0):
    start_bib = False
    is_gathering_lines = False
    lines_info = []
    start_page_idx = page_idx
    author_entry_lines = ""

    while page_idx < len(doc):
        if ctx:
            ctx.page_in_article = (page_idx - start_page_idx) + 1
            ctx.page_in_doc = article_start_page + page_idx + 1

        page = doc[page_idx]
        for block in page.get_text("dict")["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    line_text = " ".join([span["text"] for span in line["spans"]])
                    if delimiter in line_text or start_bib:
                        start_bib = True
                        line_rect = pymupdf.Rect(line["bbox"])
                        if line_has_author(line_text.strip()) and  not is_gathering_lines:
                            is_gathering_lines = True
                            author_entry_lines += line_text.strip()
                        if is_gathering_lines:
                            if not line_has_author(line_text.strip()):
                                author_entry_lines += " " + line_text.strip()
                            else:
                                tokenize_author_entry(author_entry_lines)
                                author_entry_lines = ""
                                is_gathering_lines = False
                if author_entry_lines and is_gathering_lines:
                    tokenize_author_entry(author_entry_lines)
                    author_entry_lines = ""
                            
                            


