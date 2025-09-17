import  pymupdf
import  re
import  sys
import  os
import  argparse
from    collections import  Counter
sys.path.insert(0, "./src")

import  textScreener
from    bibliographyFinder import extract_authors_from_pdf
from    configLoad import config, config_load



# poveze literaturo z navajanji v tekstu in doda goto povezave (hyperlinke)
def reference_connector(authors_info, references_info, doc):
    last_link = None
    for ref  in references_info:
        for author in authors_info:
            
            # najprej poisce ce obstaja leto iz navajanja v literaturi
            # potem poisce ce se ujema tudi avtor
            if author["year"] and ref["year"] in author["year"]:
                if (
                        ref["surname"] in author["surname"]
                        or ref["name"] in author["surname"]
                        or ref["surname"] in author["name"]
                        or ref["name"] in author["name"]
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
                    

# samo za debugging - preverjanje parsinga literature, spiska del
def print_lines_info(lines_info):
    for entry in lines_info:
        print(f"Text: {entry['text']}\nRect: {entry['position']}\nPage: {entry['page']}")
        if "surname" in entry:
            print(f"Surname: {entry['surname']}, Name: {entry['name']}, Year: {entry['year']}")
        print()
    page_counts = Counter(line["page"] for line in lines_info if "surname" in line and line["surname"])
    print ("page counts: ", page_counts)

def find_delimiting_page(delimiter, doc):
    for page_num in reversed(range(doc.page_count)):
        page = doc.load_page(page_num)
        lines = page.get_text("text").splitlines()
        for line in lines:
            if line.strip() == delimiter:
                return page_num
    return -1

# prebere argumente podane ob zagonu skripte
def args_parser():
    parser = argparse.ArgumentParser(description="Dodajanje povezav med navajanji in literaturo.")
    parser.add_argument("file_name", help="Ime oz. pot do dokumenta; mora biti PDF.")
    parser.add_argument("bibliography_delimiter",
                        help="tukaj vpisite besedo ali stavek, ki zaznamuje zacetek literature;"
                        " npr. \"literatura\" ali \"Spisek del\""
                        )
    parser.add_argument("--start-page", type=int, default=1, help="zacetna stran (default = 1)")
    parser.add_argument("--end-page", type=int, help="koncna stran (default = zadnja stran dokumenta)")
    args = parser.parse_args()
    return args

# glavna funkcija: odpre file in klice ostale funkcije
# strukture v uporabi:
#   authors_info: (iz literature)
    # - text
    # - position
    # - page
    # - surname
    # - name
    # - year
#   references_info: (najdena navajanja v tekstu)
    # - year
    # - surname
    # - name
    # - text
    # - position
    # - page
#uporaba: pdfReader.py --help
def main():
    config_load()
    args = args_parser()
    file_name = args.file_name
    authors_delimiter = args.bibliography_delimiter
    doc = pymupdf.open(file_name)
    authors_page = find_delimiting_page(authors_delimiter, doc)
    authors_info = extract_authors_from_pdf(doc, authors_page, authors_delimiter)
    # print_lines_info(authors_info)
    references_info = textScreener.screen_text(doc, authors_page, authors_delimiter, authors_info)
    reference_connector(authors_info, references_info, doc)

    #naredi nov file z narejenimi povezavami, orginal ostane isti
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    base, ext = os.path.splitext(file_name)
    output_filename = base + "_linked" + ext
    output_path = os.path.join(output_dir, output_filename)
    doc.save(output_path)
    doc.close()
    print("#####################")
    print("dokument je uspesno povezan, najde se v " + output_path)

if __name__ == "__main__":
    main()

