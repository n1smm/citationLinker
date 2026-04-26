
import  pymupdf
import  re
from    enum            import Enum 
from    .utils          import years_span_parser, soft_year_expand, alternative_names_concat
from    .configLoad     import config
from    .appLogger      import get_logger
from    .lineSpacing    import find_common_line_spacing, is_empty_line


logger = get_logger()


### poglej vrstice  - ce ima vrstica priimek, ime, leto vzemi ves tekst do naslednjega moznega zacetka elementa, oz konca tektsta
### parser je sestavljen iz FE: npr <priimek> <separator:<,>> <ime> <separator:<,>> <extra char:<(,">> <leto> <extra char:<),">>
### kako je razdeljeno ko je vec avtorjev
### ko imamo ves teks, posljemo v tokenizer da razdeli dele, 
r"""
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
def is_year_or_span(text):
    text = text.strip()
    if bool(year_span_pattern.search(text)):
        return "YEAR_SPAN"
    elif bool(year_search_pattern.search(text)):
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

    for char in char_list:
        idx = text.find(char)
        if idx != -1:
            return idx

    return idx


def find_separator_outside_wrappers(text, separator_options, wrapper_options=None):
    text = text.strip()
    if not text:
        return -1, ""

    separator_options = [opt for opt in (separator_options or []) if isinstance(opt, str) and opt]
    if not separator_options:
        return -1, ""
    separator_options = sorted(separator_options, key=len, reverse=True)

    wrapper_chars = {
        opt for opt in (wrapper_options or [])
        if isinstance(opt, str) and len(opt) == 1
    }
    paired_wrappers = {"(": ")", "[": "]", "{": "}", "<": ">"}
    symmetric_wrappers = {char for char in wrapper_chars if paired_wrappers.get(char) == char}
    for quote_char in ('"', "'"):
        if quote_char in wrapper_chars:
            symmetric_wrappers.add(quote_char)

    idx = 0
    stack = []
    while idx < len(text):
        curr_char = text[idx]

        if curr_char in symmetric_wrappers:
            if stack and stack[-1] == curr_char:
                stack.pop()
            else:
                stack.append(curr_char)
            idx += 1
            continue

        if stack and curr_char == stack[-1]:
            stack.pop()
            idx += 1
            continue

        if curr_char in wrapper_chars and curr_char in paired_wrappers:
            stack.append(paired_wrappers[curr_char])
            idx += 1
            continue

        if not stack:
            for option in separator_options:
                if text.startswith(option, idx):
                    return idx, option
        idx += 1

    return -1, ""

        
def validator_selector(text, typ_element):
    typ = (typ_element.get("TYPE") or typ_element.get("type") or "IGNORE").upper()
    if typ == "SURNAME" and is_capitalized(text, all=True):
        return "SURNAME"

    if typ == "NAME" and is_capitalized(text, all=True):
        return "NAME"

    elif typ == "TITLE" and is_capitalized(text, all=False):
        return "TITLE"

    elif typ == "EXTRA_CHAR" and is_separator_or_char(text, typ_element.get("OPTIONS") or typ_element.get("options", "")):
        return "EXTRA_CHAR"

    elif typ == "YEAR":
        return is_year_or_span(text)

    elif typ == "SEPARATOR" and is_separator_or_char(text, typ_element.get("OPTIONS") or typ_element.get("options", "")):
        return "SEPARATOR"

    else:
        return "IGNORE"


def _normalize_structure_type(raw_type):
    if not isinstance(raw_type, str):
        return ""
    normalized = raw_type.strip().replace("-", "_").replace(" ", "_").upper()
    aliases = {
        "SURNAME": "SURNAME",
        "NAME": "NAME",
        "TITLE": "TITLE",
        "YEAR": "YEAR",
        "SEPARATOR": "SEPARATOR",
        "EXTRA_CHAR": "EXTRA_CHAR",
        "EXTRACHAR": "EXTRA_CHAR",
        "IGNORE": "IGNORE",
    }
    return aliases.get(normalized, normalized)


def _normalize_options(raw_options):
    if isinstance(raw_options, list):
        return [opt.strip() for opt in raw_options if isinstance(opt, str) and opt.strip()]
    if isinstance(raw_options, str):
        return [opt.strip() for opt in raw_options.split(",") if opt.strip()]
    return []


def normalize_bib_structures(raw_bib_structures):
    if not isinstance(raw_bib_structures, list) or not raw_bib_structures:
        return []

    if all(isinstance(struct, list) for struct in raw_bib_structures):
        candidate_structures = raw_bib_structures
    elif all(isinstance(elem, dict) for elem in raw_bib_structures):
        candidate_structures = [raw_bib_structures]
    else:
        candidate_structures = [raw_bib_structures]

    normalized_structures = []
    for raw_struct in candidate_structures:
        if not isinstance(raw_struct, list):
            continue
        normalized_struct = []
        for raw_elem in raw_struct:
            if isinstance(raw_elem, dict):
                typ = _normalize_structure_type(raw_elem.get("type") or raw_elem.get("TYPE"))
                if not typ:
                    continue
                elem = {"type": typ}
                if typ in ("SEPARATOR", "EXTRA_CHAR"):
                    options = _normalize_options(raw_elem.get("options") or raw_elem.get("OPTIONS"))
                    if typ == "SEPARATOR" and not options:
                        options = [","]
                    elem["options"] = options
                normalized_struct.append(elem)
                continue

            if not isinstance(raw_elem, str):
                continue
            token = raw_elem.strip()
            if not token:
                continue

            if re.fullmatch(r"[^\w\s]+", token):
                if normalized_struct and normalized_struct[-1].get("type") in ("SEPARATOR", "EXTRA_CHAR"):
                    prev_options = normalized_struct[-1].setdefault("options", [])
                    if token not in prev_options:
                        prev_options.append(token)
                continue

            raw_type, raw_opts = (token.split(":", 1) + [""])[:2]
            typ = _normalize_structure_type(raw_type)
            if not typ:
                continue

            elem = {"type": typ}
            if typ in ("SEPARATOR", "EXTRA_CHAR"):
                options = _normalize_options(raw_opts)
                if typ == "SEPARATOR" and not options:
                    options = [","]
                elem["options"] = options
            normalized_struct.append(elem)

        if normalized_struct:
            normalized_structures.append(normalized_struct)

    return normalized_structures




##pogleda kaj je prvi token, in gleda do separatorja
## morata biti vsaj dva matcha
#def is_valid_type(token, bib_structure):
#    pass


def line_has_author(line_text):
    bib_structures = normalize_bib_structures(config.get("BIB_STRUCTURE", ""))
    if not bib_structures:
        return False
    orig_line_text = line_text.strip()

    for struct in bib_structures:
        if not isinstance(struct, list):
            continue
        hits = 0
        line_text = orig_line_text
        for typ_element in struct:
            if not isinstance(typ_element, dict):
                continue
            typ = (typ_element.get("type") or typ_element.get("TYPE") or "").upper()
            if (typ in ("SURNAME", "NAME", "TITLE")
                and line_text and line_text[0].isupper()):
                hits += 1
                
            elif typ in ("SEPARATOR", "EXTRA_CHAR"):
                options = typ_element.get("OPTIONS") or typ_element.get("options") or [","]
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
    if not typ_elements:
        return tokens
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
            if not typ:
                typ = (elem.get("TYPE") or "").upper()
            
            if typ == "EXTRA_CHAR":
                char_idx = find_separator_char(curr_text, elem.get("OPTIONS") or elem.get("options", [""]))
                if char_idx == -1:
                    continue
                curr_text = curr_text[char_idx:]
                if char_idx + 1 < len(curr_text):
                    curr_text =  curr_text[:char_idx] + curr_text[char_idx+1:]
                    typ_elements.remove(elem)
                else:
                    curr_text = ""
                    typ_elements.remove(elem)
        if curr_text and curr_text[0] and  len(typ_elements) == 1:
            tokens += content_token_sorting(curr_text, typ_elements, len(typ_elements))
        return tokens

    return tokens

# primerja vse moznosti v token bank in izbere najboljso
def stronger_match(token_bank):

    winner_len = -1
    winner = 0
    for idx,tkns in enumerate(token_bank):
        if len(tkns) > winner_len:
            winner = idx
            winner_len = len(tkns)
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
    valid_structures = normalize_bib_structures(config.get("BIB_STRUCTURE", ""))
    if not valid_structures:
        return create_bib_entry([])
    token_bank = [[] for _ in valid_structures]
    bib_entry = create_bib_entry([])

    for struct_idx, struct in enumerate(valid_structures):
        curr_text = line_text
        tokens = token_bank[struct_idx]
        segment_types = []
        wrapper_options = []

        for typ_element in struct:
            if not isinstance(typ_element, dict):
                continue
            typ = (typ_element.get("type") or typ_element.get("TYPE") or "").upper()
            if typ != "EXTRA_CHAR":
                continue
            options = typ_element.get("OPTIONS") or typ_element.get("options") or []
            if isinstance(options, str):
                options = [options]
            wrapper_options.extend([opt for opt in options if isinstance(opt, str) and opt.strip()])

        for typ_element in struct:
            if not isinstance(typ_element, dict):
                continue
            typ = (typ_element.get("type") or typ_element.get("TYPE") or "").upper()
            if typ == "SEPARATOR":
                if len(segment_types) > 2:
                    break # not correct formatting

                options = typ_element.get("OPTIONS") or typ_element.get("options") or [","]
                options = sorted(options, key=len, reverse=True)

                separator_idx, used_option = find_separator_outside_wrappers(curr_text, options, wrapper_options)
                if separator_idx == -1:
                    continue
                curr_tokens_text = curr_text[:separator_idx]
                curr_text = curr_text[separator_idx + len(used_option):].strip()
                curr_tokens = content_token_sorting(curr_tokens_text, segment_types[:], len(segment_types))
                tokens.extend(curr_tokens)
                segment_types = []
                continue

            segment_types.append(typ_element)

        if segment_types and curr_text:
            curr_tokens = content_token_sorting(curr_text, segment_types[:], len(segment_types))
            tokens.extend(curr_tokens)

    tokens = stronger_match(token_bank)
    bib_entry = create_bib_entry(tokens)
    return bib_entry







# poisce in vrne list[dict] z vsemi informacijami glede avtorjev v bibliografiji
# stil bibliografije lahko doloci uporabnik (za razliko od extract_authors_from_pdf) nekaj v stilu:
# npr <priimek> <separator:<,>> <ime> <separator:<,>> <extra char:<(,">> <leto> <extra char:<),">>
# TODO po extrahiranju bib_entry vrni vrstico nazaj (na naslednji mozni bib entry)
def extract_authors_modular(doc, page_idx, delimiter, ctx=None, article_start_page=0):
    start_bib = False
    is_gathering_lines = False
    lines_info = []
    start_page_idx = page_idx
    author_entry_lines = ""
    common_line_spacing = find_common_line_spacing(doc, start_page_idx, delimiter)
    spacing_tolerance = 0.75

    if ctx:
        ctx.common_line_spacing = common_line_spacing

    while page_idx < len(doc):
        if ctx:
            ctx.page_in_article = (page_idx - start_page_idx) + 1
            ctx.page_in_doc = article_start_page + page_idx + 1

        spacing_check = { "last": 0.0,
                         "current": 0.0,
                         "tolerance": spacing_tolerance,
                         "common_line_spacing": common_line_spacing}
        page = doc[page_idx]
        for block in page.get_text("dict")["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    line_text = " ".join([span["text"] for span in line["spans"]])
                    if delimiter in line_text or start_bib: # zacne parsing bibliografije
                        start_bib = True
                        spacing_check["current"] = float(pymupdf.Rect(line["bbox"]).y0)
                        if spacing_check["last"] <= spacing_tolerance:
                            spacing_check["last"] = spacing_check["current"]
                        if line_has_author(line_text.strip()) and  not is_gathering_lines:
                            # preveri prvi naslednji zadetek potencialnega vnosa dela/avtorja
                            is_gathering_lines = True
                            author_entry_lines = line_text.strip()
                            line_rect = pymupdf.Rect(line["bbox"])
                        elif is_gathering_lines:
                            if not line_has_author(line_text.strip()) and not is_empty_line(spacing_check):
                                # zbiranje celetno enote dela/avtorja 
                                author_entry_lines += " " + line_text.strip()
                            else:
                                # obdelava in preverjanje zbranega teksta
                                line_info = tokenize_author_entry(author_entry_lines)
                                line_info.update({
                                    "text": author_entry_lines,
                                    "position": line_rect,
                                    "page": page_idx,
                                })
                                lines_info.append(line_info)
                                author_entry_lines = ""
                                is_gathering_lines = False
                    spacing_check["last"] = spacing_check["current"]
                if author_entry_lines and is_gathering_lines:
                    line_info = tokenize_author_entry(author_entry_lines)
                    line_info.update({
                        "text": author_entry_lines,
                        "position": line_rect,
                        "page": page_idx,
                    })
                    lines_info.append(line_info)
                    author_entry_lines = ""
        page_idx += 1
                             
    if ctx:
        ctx.page_in_article = None
        ctx.page_in_doc = article_start_page + 1
    return lines_info

"""
mozno da vrstica del footerja/headerja - treba izlociti iz bib entry
vrstice samo z newline (prazne) se ne zapisejo z pymupdf
ce so special chars mora vse znotraj njih biti smatrano kot del celote, to se pravi znotraj ne isce separatorjev


"""
