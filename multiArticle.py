import  pymupdf
import  sys
import  os
import  shutil
import  string
import  math
import  re
from    collections import  Counter
from    pathlib     import  Path



sys.path.insert(0, "./src")
from    textScreener        import screen_text
from    bibliographyFinder  import extract_authors_from_pdf
from    configLoad          import config, config_load
from    referenceConnector  import reference_connector
from    debugUtils          import print_references_info, print_bibliography_info, print_delimiter_info, preview_page_lines



# poisce na kateri strani se zacne literatura
def find_delimiting_page(delimiters, doc):

    starting_page = math.floor((doc.page_count / 100) * 60)
    for delimiter in delimiters:
        for page_num in range(starting_page, doc.page_count):
            page = doc.load_page(page_num)
            lines = page.get_text("text").splitlines()
            for line in lines:
                if line.strip() == delimiter:
                    return page_num, delimiter
                if config['DEBUG'][0] == "True":
                    # print_delimiter_info(line, page_num, starting_page) 
                    pass
    return -1, -1

# razdeli file, tako da je vsak clanek svoj pdf v tmp_multi
def split_into_parts(doc, ranges, tmp_dir, src_path):
    parts = []
    gap_start = 0
    page_count = doc.page_count
    for idx, (start, end) in enumerate(ranges.values()):
        start_clamped = max(0, min(start, doc.page_count - 1))
        end_clamped = max(0, min(end, doc.page_count - 1))

        # vmesni deli ki niso clanki
        if gap_start < start_clamped:
            tmp_doc = pymupdf.open()
            tmp_doc.insert_pdf(doc, from_page=gap_start, to_page=start_clamped -1)
            tmp_path = os.path.join(tmp_dir, f"{Path(src_path).stem}_part_{idx:02d}_gap.pdf")
            tmp_doc.save(tmp_path)
            tmp_doc.close()
            tmp_part = {"path": tmp_path, "isRange":False}
            parts.append(tmp_part)
            print(f"Created gap {idx}/2: pages {gap_start}..{start_clamped -1} -> {tmp_path}")

        # clanki, ki jih je treba polinkati 
        if start_clamped > end_clamped:
            continue
        tmp_doc = pymupdf.open()
        tmp_doc.insert_pdf(doc, from_page=start_clamped, to_page=end_clamped)
        tmp_path = os.path.join(tmp_dir, f"{Path(src_path).stem}_part_{idx:02d}.pdf")
        # sprintaj par vrstic na prvi in zadnji strani
        first_page_text = doc.load_page(start_clamped).get_text().splitlines()[:5]
        last_page_text = doc.load_page(end_clamped).get_text().splitlines()[:5]
        #print za preverjanje
        if config['DEBUG'][0] == "True":
            # preview_page_lines(start_clamped, end_clamped, doc)
            pass

        tmp_doc.save(tmp_path)
        tmp_doc.close()
        tmp_part = {"path": tmp_path, "isRange":True}
        parts.append(tmp_part)
        gap_start = end_clamped + 1
        print(f"Created part {idx}: pages {start_clamped}..{end_clamped} -> {tmp_path}")

    #od zadnjega clanka do konca publikacije
    if gap_start < page_count -1:
        tmp_doc = pymupdf.open()
        tmp_doc.insert_pdf(doc, from_page=gap_start, to_page=page_count -1)
        tmp_path = os.path.join(tmp_dir, f"{Path(src_path).stem}_part_final_gap.pdf")
        tmp_doc.save(tmp_path)
        tmp_doc.close()
        tmp_part = {"path": tmp_path, "isRange":False}
        parts.append(tmp_part)
        print(f"Created gap final: pages {gap_start}..{page_count -1} -> {tmp_path}")

    return parts


def merge_linked_parts(linked_parts, file_name, output_dir):
    final = pymupdf.open()
    for part in linked_parts:
        part_doc = pymupdf.open(part)
        final.insert_pdf(part_doc)
        part_doc.close()

    base, ext = os.path.splitext(os.path.basename(file_name))
    output_filename = base + "_linked" + ext
    output_path = os.path.join(output_dir, output_filename)
    final.save(output_path)
    final.close()
    print("Saved merged final file:", output_path)


def main():
    config_load()
    input_dir = "input"
    authors_delimiters = config['BIBLIOGRAPHY_DELIMITER']
    try:
        src_file = os.listdir(input_dir)[0]
        src_file_name = os.path.join(input_dir,src_file)
        print(src_file_name)
    except (IndexError, FileNotFoundError) as e:
        print(f"error: {e}")
        return
    tmp_dir = "tmp_multi"
    out_dir = "output"
    tmp_output_dir = "tmp_output"
    os.makedirs(tmp_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(tmp_output_dir, exist_ok=True)
    doc = pymupdf.open(src_file_name)
    parts = split_into_parts(doc, config['ARTICLE_BREAKS'], tmp_dir, src_file_name)
    doc.close()
    linked_parts = []

    for part in parts:
        print("#####################")
        if not part["isRange"]:
            file_name = part["path"]
            doc = pymupdf.open(file_name)
            base, ext = os.path.splitext(os.path.basename(file_name))
            output_filename = base + "_linked" + ext
            output_path = os.path.join(tmp_output_dir, output_filename)
            doc.save(output_path)
            doc.close()
            linked_parts.append(output_path)
            print("gap_file output name: ", output_path)
            continue
        file_name = part["path"]
        print("file name: ", file_name)
        doc = pymupdf.open(file_name)
        authors_page, authors_delimiter = find_delimiting_page(authors_delimiters, doc)
        if authors_page == -1 or authors_delimiter == -1:
            print("nepravilen BIBLIOGRAPHY_DELIMITER za dokument:", file_name)
            print("authors delimiter: " , authors_delimiter, " authors page: ", authors_page)
            return -1

        authors_info = extract_authors_from_pdf(doc, authors_page, authors_delimiter)
        references_info = screen_text(doc, authors_page, authors_delimiter)
        if config['DEBUG'][0] == "True":
            print_bibliography_info(authors_info)
            print_references_info(references_info)
            pass

        reference_connector(authors_info, references_info, doc)

        #naredi nov file z narejenimi povezavami, original ostane isti
        base, ext = os.path.splitext(os.path.basename(file_name))
        output_filename = base + "_linked" + ext
        output_path = os.path.join(tmp_output_dir, output_filename)
        linked_parts.append(output_path)
        doc.save(output_path)
        doc.close()
        print("dokument je uspesno povezan, " + output_path)
        print("#####################")
    merge_linked_parts(linked_parts, src_file, out_dir)
    shutil.rmtree(tmp_dir)
    shutil.rmtree(tmp_output_dir)


if __name__ == "__main__":
    main()
