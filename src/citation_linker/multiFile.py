import  pymupdf
import  sys
import  os
from    collections import  Counter

from    citation_linker                     import  textScreener
from    citation_linker.bibliographyFinder  import  extract_authors_from_pdf
from    citation_linker.configLoad          import  config, config_load
from    citation_linker.referenceConnector  import  reference_connector
from    citation_linker.configPaths         import  resolve_config_path, resolve_dir_paths
from    citation_linker.io_safe             import  atomic_replace_save, normalize_path, FileLockError


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
        io_dirs = resolve_dir_paths()
        input_dir = normalize_path(io_dirs["input"])
        output_dir = normalize_path(io_dirs["output"])
        output_dir.mkdir(parents=True, exist_ok=True)
        authors_delimiters = config['BIBLIOGRAPHY_DELIMITER']
        for file_path in sorted(path for path in input_dir.iterdir() if path.is_file()):
            print("#####################")
            file_name = str(file_path)
            print("file name: ", file_name)
            doc = pymupdf.open(file_name)
            authors_page, authors_delimiter = find_delimiting_page(authors_delimiters, doc)
            print("authors delimiter: " , authors_delimiter)
            if authors_page == -1 or authors_delimiter == -1:
                print("nepravilen BIBLIOGRAPHY_DELIMITER za dokument:", file_name)
                doc.close()
                return 1

            authors_info = extract_authors_from_pdf(doc, authors_page, authors_delimiter)
            # print_lines_info(authors_info)
            references_info = textScreener.screen_text(doc, authors_page, authors_delimiter)
            reference_connector(authors_info, references_info, doc)

            #naredi nov file z narejenimi povezavami, orginal ostane isti
            base, ext = os.path.splitext(os.path.basename(file_name))
            output_filename = base + "_linked" + ext
            output_path = output_dir / output_filename
            atomic_replace_save(output_path, lambda temp_path: doc.save(temp_path))
            doc.close()
            print("dokument je uspesno povezan, najde se v " + str(output_path))
            print("#####################")
        return 0
    except FileLockError as e:
        print(f"Error: destination file is locked: {e}")
        return 1
    except Exception as e:
        print(f"Error during linking process: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
