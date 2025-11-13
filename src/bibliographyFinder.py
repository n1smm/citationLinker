import  pymupdf
import  re

import  pdb


# ce je vrstica z avtorjem_ico izbere potrebne podatke (ime, priimek, leto)
def find_starting_lines_authors(line_info):
    token_count = 0
    text = line_info["text"]
    # pdb.set_trace()
    if ":" in text:
        parts = text.split(":")
        before_colon = parts[0].strip()
    else:
        before_colon = text.strip()

    # tokens = [t.strip() for t in before_colon.split(",")]
    tokens = [t.strip() for t in re.split(r",|\bin\b", before_colon)]
    if len(tokens) < 2:
        return False

    surname = tokens[0]

    if not (surname and surname[0].isupper() and re.match(r"^[\w\- ']+$", surname, re.UNICODE)):
        return False
    token_count += 1

    name = tokens[1] if len(tokens) > 2 else None
    if name and not (name[0].isupper()):
        return False
    if not name:
        name = "yyy"
        token_count -= 1
    token_count += 1

    year_search_pattern = re.compile(r'\d{4}[a-zA-iZ]?$')

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

    #letnica
    if token_count < len(tokens) and not ":" in text:
        year = tokens[token_count].split()[0]
    elif token_count < len(tokens) and ":" in text:
        year = tokens[len(tokens) - 1].split()[0]
    else:
        return False

    if not year_search_pattern.match(year):
        return False

    if (not others):
        others = ["yyy"]
    line_info.update({"surname": surname, "name": name, "year": year, "others": others})
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
                        })
                        
                        find_starting_lines_authors(lines_info[-1])
        page_idx += 1
    return lines_info
