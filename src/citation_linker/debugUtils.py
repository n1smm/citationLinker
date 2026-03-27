import  pymupdf
import  string
import  re
from    collections import Counter 
from    citation_linker.appLogger import get_logger

logger = get_logger() 

# debuging oz. za preverjanje koncega slovarja najdenih referenc: references_info
def print_references_info(references_info):
    for ref in references_info:
        if not ref:
            continue
        logger.debug(f"Reference - year: {ref.get('year', '')}, surname: {ref.get('surname', '')}, name: {ref.get('name', '')}")
        logger.debug(f"  text: {ref.get('text', '')}, position: {ref.get('position', '')}, page: {ref.get('page', '')}")
        if ref["others"] and ref["others"][0] != "xxx":
            for other in ref["others"]:
                logger.debug(f"  other: {other}")
        if ref["years"] and ref["years"][0] != "xxx":
            for year in ref["years"]:
                logger.debug(f"  year: {year}")
            logger.debug(f"  span: {ref['year_span']}")
#debug print za temp ref
def print_temp_ref_text(temp_refs):
    logger.debug('\n'.join(ref["text"] for ref in temp_refs))
    
# samo za debugging - preverjanje parsinga literature, spiska del
def print_bibliography_info(lines_info):
    for entry in lines_info:
        logger.debug(f"Bibliography entry - Text: {entry['text']}, Rect: {entry['position']}, Page: {entry['page']}")
        if "surname" in entry and (entry['surname'] != "yyy" and entry['name'] != "yyy"):
            logger.debug(f"  Surname: {entry['surname']}, Name: {entry['name']}, Year: {entry['year']}")
        if not "yyy" in entry["others"][0] and not ("yyy" in entry['surname'] and "yyy" in entry['name']):
            for idx,other in enumerate(entry["others"]):
                logger.debug(f"  Other {idx}: {other}")
        if not "yyy" in entry["years"][0] and not ("yyy" in entry['surname'] and "yyy" in entry['name']):
            logger.debug(f"  year_span: {entry['year_span']}")
    page_counts = Counter(line["page"] for line in lines_info if "surname" in line and line["surname"])
    logger.debug(f"Bibliography page counts: {page_counts}")

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
    if page_num is not None and starting_page is not None:
        logger.debug(f"Delimiter search - page_num: {page_num}, starting page: {starting_page}")
    logger.debug(f"LINE: {line}")
    logger.debug(f"LINE REPR: {repr(line)}")
    logger.debug(f"CLEAN LINE REPR: {repr(clean_line.strip())}")
    logger.debug(f"CLEAN LINE: {clean_line}")
    
# printa prvo in zadnjo stran razdeljenih dokumentov
# za pregled ce so clanki pravilno razdeljeni
def preview_page_lines(start_clamped, end_clamped, doc):
    first_page_text = doc.load_page(start_clamped).get_text().splitlines()[:5]
    last_page_text = doc.load_page(end_clamped).get_text().splitlines()[:5]
    logger.debug(f"Preview first page ({start_clamped}):")
    for line in first_page_text:
        logger.debug(f"  {line}")
    logger.debug(f"Preview last page ({end_clamped}):")
    for line in last_page_text:
        logger.debug(f"  {line}")
