import  pymupdf
import  re

import  pdb
from utils import years_span_parser, soft_year_expand, alternative_names_concat


# viri ki imajo strukturo tako: leto. naslov npr:(1964. Slovenska matica)
def find_sources_year_dot_work(line_info):
    text = line_info["text"]
    tokens = text.split(".")
    year_search_pattern = re.compile(r'\d{4}[a-zA-Z]?$')
    years_span_pattern = re.compile(r'\d{4} {0,2}[-–—]{1,2} {0,2}\d{4}')
    others = []
    years = []
    year_span = "yyy"

    if year_search_pattern.match(tokens[0].strip()):
        year = tokens[0].strip()
    else:
        year = "yyy"

    for token in tokens[1:-1]:
        if years_span_pattern.search(token.strip()):
            years = years_span_parser(token.strip(), years)
            year_span = f"{years[0]}-{years[-1]}" if len(years) > 1 else "yyy"
            # print(f"year_span is :{year_span}")
        others.append(token.strip())

    if year == "yyy" and not years:
        return False
    if not years:
        years = soft_year_expand(year, "yyy")
    if not others or not others[0]:
        return False

    for t in tokens:
        others.extend(alternative_names_concat(t))
    others = list(set(others))

    line_info.update({"surname": "SOURCE", "name": "SOURCE", "year": year, "others": others, "years": years, "year_span": year_span})
    return True

# ce je vrstica z avtorjem_ico izbere potrebne podatke (ime, priimek, leto)
def find_starting_lines_authors(line_info):
    token_count = 0
    years = []
    year_span = "yyy"
    text = line_info["text"]
    # pdb.set_trace()
    dot_delimiter = re.compile(r"\d{4}[a-zA-Z]?\.")
    dot_match = dot_delimiter.search(text);
    if ":" in text:
        parts = text.split(":")
        before_colon = parts[0].strip()
    elif dot_match:
        before_colon = text[:dot_match.end() -1]
    else:
        before_colon = text.strip()

    tokens = [t.strip() for t in re.split(r",|\bin\b", before_colon)]
    if len(tokens) < 2:
        return False

    surname = tokens[0]

    if not (surname and surname[0].isupper()): # and re.match(r"^[\w\- ']+$", surname, re.UNICODE)):
        return False
    token_count += 1

    name = tokens[1] if len(tokens) > 2 else None
    if name and not (name[0].isupper()):
        return False
    if not name:
        name = "yyy"
        token_count -= 1
    token_count += 1

    year_search_pattern = re.compile(r'\d{4}[a-zA-Z]?$')

    #ostali avtorji ce so
    others = []
    for idx, token in enumerate(tokens):
        if (token 
            and idx > 1
            and not year_search_pattern.match(token) 
            and idx < len(tokens) -1 
            and len(token) > 0
            and token[0].isupper()):
                other_tokens = token.split()
                for o in other_tokens:
                    if o and len(o):
                        others.append(o.strip())
                        token_count +=1

    #letnica
    year = None
    for token in tokens:
        if year_search_pattern.match(token):
            year = token.split()[0]
            break
    if not year:
        years_span_pattern = re.compile(r'\d{4} {0,2}[-–—]{1,2} {0,2}\d{4}')
        if years_span_pattern.search(text):
            years = years_span_parser(text, years)
            year_span = f"{years[0]}-{years[-1]}" if len(years) > 1 else "yyy"
        else:
            return False
    # if token_count < len(tokens) and not ":" in text:
    #     print(tokens[token_count])
    #     year = tokens[token_count].split()[0]
    # elif token_count < len(tokens) and ":" in text:
    #     print(tokens[token_count])
    #     year = tokens[len(tokens) - 1].split()[0]
    # else:
    #     return False

    if not others:
        others = ["yyy"]
    if not years and year:
        years = soft_year_expand(year, "yyy")
        year_span = f"{years[0]}-{years[-1]}" or "yyy"
    if not year:
        year = "yyy"

    for t in tokens:
        others.extend(alternative_names_concat(t))
    others = list(set(others))

    line_info.update({"surname": surname, "name": name, "year": year, "others": others, "years": years, "year_span": year_span})
    return True



# zacne shranjevati sele od kljucne besede, ki zaznamuje zacetek literature
#   zbere: celotne vrstice, pozicijo vrstice, stran, in ce je vrstica z avtorjem tudi
#   ime, priimek in leto
def extract_authors_from_pdf(doc, page_idx, search_text):

    start = False
    lines_info = []
    while page_idx < len(doc):
        page = doc[page_idx]
        for block in page.get_text("dict")["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    line_text = " ".join([span["text"] for span in line["spans"]])
                    if search_text in line_text or start:
                        start = True
                        line_rect = pymupdf.Rect(line["bbox"])
                        lines_info.append({
                            "text": line_text,
                            "position": line_rect,
                            "page": page_idx,
                            "surname": "yyy",
                            "name": "yyy",
                            "others": ["yyy"],
                            "year": "yyy", 
                            "years": ["yyy"],
                            "year_span": "yyy",
                        })
                        
                        if not find_starting_lines_authors(lines_info[-1]):
                            find_sources_year_dot_work(lines_info[-1])
        page_idx += 1
    return lines_info
