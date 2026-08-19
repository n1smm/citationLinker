import  pymupdf
import  re
from    .configLoad import config
from    .utils import year_span_match
from    .appLogger import get_logger, record_link_hit, record_link_match

logger = get_logger()

# iskanje bliznjih zadetkov, tako lahko deluje tudi z zelo preprostim sklanjanjem
# ali razliki v velikih zacetnicah
def close_match(ref, author):
    if len(ref) > 2 and len(author) > 2:
        return ref.lower()[:-2] in author.lower()
    else:
        return False

def close_match_array(ref, array):
    for author in array:
        if author and len(ref) > 2 and len(author) > 2:
            if author != "yyy" and ref != "xxx":
                logger.debug(f"Checking close match: ref={ref} vs author={author}")
            if ref.lower()[:-2] in author.lower():
                return True
    return False

# poglej ce se ujema del enega lista z drugim
def match_array_array(array1, array2):
    if config['DEEP_SEARCH'][0] != "True":
        return False
    match = 0
    for elem1 in array1:
        for elem2 in array2:
            if (len(elem1) > 2 
                and len(elem2) > 2
                and elem1 in elem2 
                and elem1[0].isupper()
                and elem2[0].isupper()
                and elem2 not in config['ALTERNATIVE_BIB']
                and elem1 not in config['ALTERNATIVE_BIB']
                and not any(option in elem1 for option in config['ALTERNATIVE_BIB'])
                and not any(option in elem2 for option in config['ALTERNATIVE_BIB'])
                ):
                match +=1
                if match >= 2:
                    return True
    return False

# dodatni check za pravilen rect pri annotiranju
def is_same_line(rect1, rect2, tolerance=2):
    return abs(rect1.y0 - rect2.y0) < tolerance and abs(rect1.y1 - rect2.y1) < tolerance


# poisce samo letnico za annotiranje, da ne oznaci celotnega iskalnega niza
def extract_year_annot(word, word_rect, rect):
    match = re.search(r"\d{4}[a-zA-Z]?", word)
    word_len = len(word)
    if  not match:
        return None
    
    start_percent = (match.start() / word_len) * 100
    end_percent = ((word_len - match.end()) / word_len) * 100

    # priblizno oceni (procentualno) od kje do kje bi moral biti rect za letnico
    width = word_rect.x1 - word_rect.x0
    new_x0 = word_rect.x0 + width * (start_percent / 100)
    new_x1 = word_rect.x1 - width * (end_percent / 100)
    new_rect = pymupdf.Rect(new_x0, word_rect.y0, new_x1, word_rect.y1)
    return new_rect

# povezi priimek in ime v en string (za dvojne priimke)
def uniteSurnameName(surname, name):
    return (surname + " " + name)

# preverjanje ce se katerikoli del citata in bibliografije ujema (true/false)
def is_author_match(ref, author):
    return (
        close_match(ref["surname"], author["surname"])
        or close_match(ref["name"], author["surname"])
        or close_match(ref["surname"], author["name"])
        or close_match(ref["name"], author["name"])
        or close_match(uniteSurnameName(ref["surname"], ref["name"]), author["surname"])
        or close_match(uniteSurnameName(ref["surname"], ref["name"]), author["name"])
        or close_match_array(ref["surname"], author["others"])
        or close_match_array(ref["name"], author["others"])
        or match_array_array(ref["others"], author["others"])
    )

# pogleda ce se leta 
def soft_year_match(author, ref):
    if (author["year_span"] in ref["year"] or
        author["year"] in ref["year_span"] or
        author["year_span"] in ref["year_span"]
        ):
        return True
    if year_span_match(author["year_span"], ref["year_span"]):
        return True
    author_years = set(str(y) for y in author.get("years", []))
    ref_years = set(str(y) for y in ref.get("years", []))
    if author_years & ref_years:
        return True
    return False

# ce najde ujemanje, pripravi linkanje citata z literaturo
def process_reference_match(ref, author, doc, config, ctx=None, article_start_page=0):
    # posodobi kontekst glede na stran reference (ki je lokalna 0-based stran)
    if ctx:
        ref_local_page = int(ref["page"])
        ctx.page_in_article = ref_local_page + 1
        ctx.page_in_doc = article_start_page + ref_local_page + 1
    
    num_ref_found = 1
    curr_page = int(ref["page"])
    raw_position = ref.get("position")
    if not raw_position:
        logger.warning(f"process_reference_match: ref has no position — skipping link for {ref.get('surname', '?')} {ref.get('year', '?')}")
        return 0, last_link
    ref_rects = raw_position if isinstance(raw_position, list) else [raw_position]
    author_point = author["position"].tl
    page = doc[curr_page]
    words = page.get_text("words")
    last_link = {
        "page": int(author["page"]),
        "to": author_point
    }
    for rect in ref_rects:
        curr_link = {
            "kind": pymupdf.LINK_GOTO,
            "from": rect,
            "page": int(author["page"]),
            "to": author_point
        }
        page.insert_link(curr_link)
        is_annot = False
        for w in words:
            word_rect = pymupdf.Rect(w[0], w[1], w[2], w[3])
            if rect.intersects(word_rect) and ref["year"] in w[4] and re.fullmatch(r"\d{4}[a-zA-Z]?", ref["year"]) and is_same_line(rect, word_rect):
                rect = extract_year_annot(w[4], word_rect, rect)
                is_annot = True
                break
        if is_annot and rect:
            if config['ANNOT_TYPE'] and config['ANNOT_TYPE'][0] == 'underline':
                annot = page.add_underline_annot(rect)
            else:
                annot = page.add_highlight_annot(rect)
            annot.set_colors({"stroke": config['STROKE']})
            annot.update()
    return num_ref_found, last_link

# poveze literaturo z navajanji v tekstu in doda goto povezave (hyperlinke)
def reference_connector(authors_info, references_info, doc, ctx=None, article_start_page=0):
    last_link = None
    num_ref_found = 0
    last_bib_id = None
    for ref  in references_info:
        # posodobi kontekst glede na stran reference (lokalna 0-based stran)
        if ctx:
            ref_local_page = int(ref["page"])
            ctx.page_in_article = ref_local_page + 1
            ctx.page_in_doc = article_start_page + ref_local_page + 1
        
        # preskoči iskanje v bibliografiji za posebne primere
        if ref["surname"] == "special_case":
            # posebni primer bo obdelan spodaj
            pass
        else:
            for author in authors_info:

                # najprej poisce ce obstaja leto iz navajanja v literaturi
                # potem poisce ce se ujema tudi avtor
                if author["year"] and ref["year"] in author["year"]:
                    if is_author_match(ref, author):
                        nrf, last_link = process_reference_match(ref, author, doc, config, ctx, article_start_page)
                        num_ref_found += nrf
                        record_link_hit()
                        record_link_match(
                            (ref.get("surname", ""), ref.get("year", ""), str(ref.get("page", ""))),
                            (author.get("surname", ""), author.get("year", ""), str(author.get("page", ""))),
                        )
                        last_bib_id = (author.get("surname", ""), author.get("year", ""), str(author.get("page", "")))
                        logger.debug(f"Matched {ref['surname']} {ref['year']} to author {author['surname']} on page {author['page']}")
                        # break po najdenem ujemanju, da ne nadaljuje in prepise last_link
                        break
                        #konec if za leto
                elif config["SOFT_YEAR"][0] == "True":
                    #logika za dodatno ujemanje
                    if is_author_match(ref, author):
                        if soft_year_match(author, ref):
                            nrf, last_link = process_reference_match(ref, author, doc, config, ctx, article_start_page)
                            num_ref_found += nrf
                            record_link_hit()
                            record_link_match(
                                (ref.get("surname", ""), ref.get("year", ""), str(ref.get("page", ""))),
                                (author.get("surname", ""), author.get("year", ""), str(author.get("page", ""))),
                            )
                            last_bib_id = (author.get("surname", ""), author.get("year", ""), str(author.get("page", "")))
                            logger.debug(f"Soft-matched {ref['surname']} {ref['year']} to author {author['surname']} on page {author['page']}")
                            # break po najdenem ujemanju, da ne nadaljuje in prepise last_link
                            break




        # ce gre za posebni primer, kjer se navajanje navezuje na prejsnjo delo (npr. "nav. d.")
        if ref["surname"] == "special_case" and last_link:
            raw_position = ref.get("position")
            if not raw_position:
                logger.warning(f"special_case ref has no position — skipping: '{ref.get('text', '?')}'")
                continue
            ref_rects = raw_position if isinstance(raw_position, list) else [raw_position]
            num_ref_found += 1
            record_link_hit()
            record_link_match(
                (ref.get("surname", ""), ref.get("year", ""), str(ref.get("page", ""))),
                last_bib_id or ("special_case", "0", ""),
            )
            curr_page = int(ref["page"])
            page = doc[curr_page]
            logger.debug(f"Special case '{ref['text']}' on page {ref['page']} linking to page {last_link['page']}, point: {last_link['to']}")
            for rect in ref_rects:
                logger.debug(f"Authors point to: {last_link['to']}")
                curr_link = {
                        "kind": pymupdf.LINK_GOTO,
                        "from": rect,
                        "page": last_link["page"],
                        "to": last_link["to"]
                        }
                page.insert_link(curr_link)
                if config['ANNOT_TYPE'] and config['ANNOT_TYPE'][0] == 'underline':
                    annot = page.add_underline_annot(rect)
                else:
                    annot = page.add_highlight_annot(rect)
                annot.set_colors({"stroke":config['STROKE']})
                annot.update()
    
    # resetiraj kontekst na stanje na nivoju clanka preden vrnes rezultat
    if ctx:
        ctx.page_in_article = None
        ctx.page_in_doc = article_start_page + 1
    
    return (num_ref_found)
