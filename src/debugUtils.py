import  pymupdf
import  string
import  re
from    collections import Counter 

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
    
# samo za debugging - preverjanje parsinga literature, spiska del
def print_bibliography_info(lines_info):
    for entry in lines_info:
        print(f"Text: {entry['text']}\nRect: {entry['position']}\nPage: {entry['page']}")
        if "surname" in entry:
            print(f"Surname: {entry['surname']}, Name: {entry['name']}, Year: {entry['year']}")
        if not "yyy" in entry["others"][0]:
            for idx,other in enumerate(entry["others"]):
                print(f"Other {idx}: {other}")
        if not "yyy" in entry["years"][0]:
    # print_references_info(references_info)
            # for idx, y in enumerate(entry["years"]):
            #     print(f"Year{idx}: {y}")
            print("year_span:", entry["year_span"])
        print()
    page_counts = Counter(line["page"] for line in lines_info if "surname" in line and line["surname"])
    print ("page counts: ", page_counts)

# za odstranjevanje nevidnih znakov iz teksta
def normalize_soft_text(text):
    # Remove soft hyphens between letters
    text = re.sub(r'(?<=\w)\xad(?=\w)', '', text)
    # Replace soft hyphens surrounded by whitespace with a space
    text = re.sub(r'\s*\xad\s*', ' ', text)
    # Replace non-breaking spaces with a regular space
    text = text.replace('\xa0', ' ')
    return text

# debug print za iskanje nevidnih znakov (ko se isce delimiter)
def print_delimiter_info(line, page_num=None, starting_page=None):
    clean_line = ''.join(c for c in line if c in string.printable).replace('\xad', '').strip()
    clean_line = normalize_soft_text(line)
    print()
    if page_num is not None and starting_page is not None:
        print("page_num: ", page_num, " starting page: ", starting_page)
    print("LINE: ", line)
    print("LINE REPR:", repr(line))
    print(f"LINE:{' ' * 14}{line}")
    print(f"CLEAN LINE REPR:{' ' * 2}{repr(clean_line.strip())}")
    print("CLEAN LINE REPR:", repr(clean_line.strip()))
    print()
    print("CLEAN LINE: ", clean_line)
    print("LINE: ", line)
    
# printa prvo in zadnjo stran razdeljenih dokumentov
# za pregled ce so clanki pravilno razdeljeni
def preview_page_lines(start_clamped, end_clamped, doc):
    first_page_text = doc.load_page(start_clamped).get_text().splitlines()[:5]
    last_page_text = doc.load_page(end_clamped).get_text().splitlines()[:5]
    print()
    print(f" ---- Preview first page ({start_clamped}):")
    for line in first_page_text:
        print(line)
    print()
    print(f" ---- Preview last page ({end_clamped}):")
    for line in last_page_text:
        print(line)
    print()
