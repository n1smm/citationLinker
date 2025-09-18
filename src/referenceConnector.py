import  pymupdf
from    configLoad import config

def close_match(ref, author):
    if len(ref) > 2 and len(author) > 2:
        return ref.lower()[:-1] in author.lower()
    else:
        return False

# poveze literaturo z navajanji v tekstu in doda goto povezave (hyperlinke)
def reference_connector(authors_info, references_info, doc):
    last_link = None
    for ref  in references_info:
        for author in authors_info:
            
            # najprej poisce ce obstaja leto iz navajanja v literaturi
            # potem poisce ce se ujema tudi avtor
            if author["year"] and ref["year"] in author["year"]:
                if (
                        close_match(ref["surname"], author["surname"])
                        or close_match(ref["name"], author["surname"])
                        or close_match(ref["surname"], author["name"])
                        or close_match(ref["name"], author["name"])
                    ):
                    # vzame vse pozicije, kjer se nahaja ujemanje (npr. prelom strani sta 2 poziciji)
                    curr_page = int(ref["page"])
                    ref_rects = (ref["position"] if isinstance(ref["position"], list)
                                 else [ref["position"]])
                    author_point = author["position"].tl
                    page = doc[curr_page]
                    # doda goto referenco in oblikuje navedbo
                    for rect in ref_rects:
                        last_link = {
                                "kind": pymupdf.LINK_GOTO,
                                "from": rect,
                                "page": int(author["page"]),
                                "to": author_point
                                }
                        page.insert_link(last_link)
                        annot = page.add_underline_annot(rect)
                        annot.set_colors({"stroke":config['STROKE']})
                        annot.update()

        # ce gre za posebni primer, kjer se navajanje navezuje na prejsnjo delo (npr. "nav. d.")
        if ref["surname"] == "special_case" and last_link:
            ref_rects = (ref["position"] if isinstance(ref["position"], list)
                             else [ref["position"]])
            curr_page = int(ref["page"])
            page = doc[curr_page]
            for rect in ref_rects:
                curr_link = {
                        "kind": pymupdf.LINK_GOTO,
                        "from": rect,
                        "page": last_link["page"],
                        "to": last_link["to"]
                        }
                page.insert_link(curr_link)
                annot = page.add_underline_annot(rect)
                annot.set_colors({"stroke":config['STROKE']})
                annot.update()
