import  pymupdf
import  sys
import  os
from    collections import  Counter

from    citation_linker                     import  textScreener
from    citation_linker.bibliographyFinder  import  extract_authors_from_pdf
from    citation_linker.configLoad          import  config, config_load
from    citation_linker.referenceConnector  import  reference_connector
from    citation_linker.configPaths         import  resolve_config_path 


# poisce na kateri strani se zacne literatura
def find_delimiting_page(delimiters, doc):

    for delimiter in delimiters:
        for page_num in reversed(range(doc.page_count)):
            page = doc.load_page(page_num)
            lines = page.get_text("text").splitlines()
            for line in lines:
                if line.strip() == delimiter:
                    return page_num, delimiter
    return -1, -1

# samo za debugging - preverjanje parsinga literature, spiska del
def print_lines_info(lines_info):
    for entry in lines_info:
        print(f"Text: {entry['text']}\nRect: {entry['position']}\nPage: {entry['page']}")
        if "surname" in entry:
            print(f"Surname: {entry['surname']}, Name: {entry['name']}, Year: {entry['year']}")
        print()
    page_counts = Counter(line["page"] for line in lines_info if "surname" in line and line["surname"])
    print ("page counts: ", page_counts)

def main():
    try:
        config_path = resolve_config_path()
        config_load(config_path)
        input_dir = "input"
        authors_delimiters = config['BIBLIOGRAPHY_DELIMITER']
        for file in os.listdir(input_dir):
            print("#####################")
            file_name = os.path.join(input_dir, file)
            print("file name: ", file_name)
            doc = pymupdf.open(file_name)
            authors_page, authors_delimiter = find_delimiting_page(authors_delimiters, doc)
            print("authors delimiter: " , authors_delimiter)
            if authors_page == -1 or authors_delimiter == -1:
                print("nepravilen BIBLIOGRAPHY_DELIMITER za dokument:", file_name)
                doc.close()
                sys.exit(1)

            authors_info = extract_authors_from_pdf(doc, authors_page, authors_delimiter)
            # print_lines_info(authors_info)
            references_info = textScreener.screen_text(doc, authors_page, authors_delimiter)
            reference_connector(authors_info, references_info, doc)

            #naredi nov file z narejenimi povezavami, orginal ostane isti
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            base, ext = os.path.splitext(os.path.basename(file_name))
            output_filename = base + "_linked" + ext
            output_path = os.path.join(output_dir, output_filename)
            doc.save(output_path)
            doc.close()
            print("dokument je uspesno povezan, najde se v " + output_path)
            print("#####################")
        sys.exit(0)
    except Exception as e:
        print(f"Error during linking process: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
