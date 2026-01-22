import  pymupdf
import  re
import  sys
import  os
import  argparse
from    collections import  Counter

from    citation_linker                     import  textScreener
from    citation_linker.bibliographyFinder  import  extract_authors_from_pdf
from    citation_linker.configLoad          import  config, config_load
from    citation_linker.referenceConnector  import  reference_connector
from    citation_linker.configPaths         import  resolve_config_path 

import  pdb;

# poisce priblizno ujemanje, za preposta sklanjanja Frank Franka
                    

# samo za debugging - preverjanje parsinga literature, spiska del
def print_lines_info(lines_info):
    for entry in lines_info:
        print(f"Text: {entry['text']}\nRect: {entry['position']}\nPage: {entry['page']}")
        if "surname" in entry:
            print(f"Surname: {entry['surname']}, Name: {entry['name']}, Year: {entry['year']}")
        print()
    page_counts = Counter(line["page"] for line in lines_info if "surname" in line and line["surname"])
    print ("page counts: ", page_counts)

# poisce na kateri strani se zacne literatura
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
    parser.add_argument("--config", help="path do .config datoteke")
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
#uporaba: citationLinker.py --help
def main():
    try:
        args = args_parser()
        config_path = resolve_config_path(args.config)
        config_load(config_path)
        file_name = args.file_name
        authors_delimiter = args.bibliography_delimiter
        doc = pymupdf.open(file_name)
        authors_page = find_delimiting_page(authors_delimiter, doc)
        if authors_page == -1:
            print(f"Error: Bibliography delimiter '{authors_delimiter}' not found in document")
            doc.close()
            sys.exit(1)
        # pdb.set_trace()
        authors_info = extract_authors_from_pdf(doc, authors_page, authors_delimiter)
        # print_lines_info(authors_info)
        references_info = textScreener.screen_text(doc, authors_page, authors_delimiter)
        refs_found = reference_connector(authors_info, references_info, doc)

        #naredi nov file z narejenimi povezavami, orginal ostane isti
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        base, ext = os.path.splitext(os.path.basename(file_name))
        output_filename = base + "_linked" + ext
        output_path = os.path.join(output_dir, output_filename)
        doc.save(output_path)
        doc.close()
        print("num refs found: ", refs_found)
        print("#####################")
        print("dokument je uspesno povezan, najde se v " + output_path)
        sys.exit(0)
    except Exception as e:
        print(f"Error during linking process: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

