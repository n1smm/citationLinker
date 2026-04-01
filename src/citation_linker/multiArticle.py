import  pymupdf
import  sys
import  os
import  shutil
import  string
import  math
import  re
import  logging
from    collections import  Counter
from    pathlib     import  Path



from    citation_linker.textScreener        import  screen_text
from    citation_linker.bibliographyFinder  import  extract_authors_from_pdf
from    citation_linker.configLoad          import  config, config_load
from    citation_linker.referenceConnector  import  reference_connector
from    citation_linker.configPaths         import  resolve_config_path, resolve_dir_paths 
from    citation_linker.appLogger           import  get_logger, ArticleContext
from    citation_linker.debugUtils          import  (print_references_info,
                                                     print_bibliography_info,
                                                     print_delimiter_info,
                                                     preview_page_lines)


# poisce na kateri strani se zacne literatura
def find_delimiting_page(delimiters, doc, ctx=None, article_start_page=0):
    logger = get_logger()
    starting_page = math.floor((doc.page_count / 100) * 60)
    for delimiter in delimiters:
        for page_num in range(starting_page, doc.page_count):
            # posodobi kontekst za trenutno stran
            if ctx:
                ctx.page_in_article = page_num + 1  # 1-based page within article
                ctx.page_in_doc = article_start_page + page_num + 1  # 1-based global page in source PDF
            
            page = doc.load_page(page_num)
            lines = page.get_text("text").splitlines()
            for line in lines:
                if line.strip() == delimiter:
                    # resetiraj page_in_article, ker nismo vec na specificni strani
                    if ctx:
                        ctx.page_in_article = None
                    return page_num, delimiter
    
    # resetiraj kontekst
    if ctx:
        ctx.page_in_article = None
    return -1, -1

# razdeli file, tako da je vsak clanek svoj pdf v tmp_multi
def split_into_parts(doc, ranges, tmp_dir, src_path):
    logger = get_logger()
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
            tmp_part = {"path": tmp_path, "isRange":False, "start_page": gap_start, "end_page": start_clamped -1}
            parts.append(tmp_part)
            logger.info(f"Created gap {idx}/2: pages {gap_start}..{start_clamped -1} -> {tmp_path}")

        # clanki, ki jih je treba polinkati 
        if start_clamped > end_clamped:
            continue
        tmp_doc = pymupdf.open()
        tmp_doc.insert_pdf(doc, from_page=start_clamped, to_page=end_clamped)
        tmp_path = os.path.join(tmp_dir, f"{Path(src_path).stem}_part_{idx:02d}.pdf")
        # sprintaj par vrstic na prvi in zadnji strani
        first_page_text = doc.load_page(start_clamped).get_text().splitlines()[:5]
        last_page_text = doc.load_page(end_clamped).get_text().splitlines()[:5]
        tmp_doc.save(tmp_path)
        tmp_doc.close()
        tmp_part = {"path": tmp_path, "isRange":True, "start_page": start_clamped, "end_page": end_clamped}
        parts.append(tmp_part)
        gap_start = end_clamped + 1
        logger.info(f"Created part {idx}: pages {start_clamped}..{end_clamped} -> {tmp_path}")
        # logger.debug(f"First page lines: {first_page_text}")
        # logger.debug(f"Last page lines: {last_page_text}")

    #od zadnjega clanka do konca publikacije
    if gap_start < page_count -1:
        tmp_doc = pymupdf.open()
        tmp_doc.insert_pdf(doc, from_page=gap_start, to_page=page_count -1)
        tmp_path = os.path.join(tmp_dir, f"{Path(src_path).stem}_part_final_gap.pdf")
        tmp_doc.save(tmp_path)
        tmp_doc.close()
        tmp_part = {"path": tmp_path, "isRange":False, "start_page": gap_start, "end_page": page_count -1}
        parts.append(tmp_part)
        logger.info(f"Created gap final: pages {gap_start}..{page_count -1} -> {tmp_path}")

    return parts


def merge_linked_parts(linked_parts, file_name, output_dir):
    logger = get_logger()
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
    logger.info(f"Saved merged final file: {output_path}")


def main():
    try:
        
        # preberi config file
        config_path = resolve_config_path()
        io_dirs = resolve_dir_paths()
        config_load(config_path)

        # inicializacija loggerja in konteksta za clanke
        logger = get_logger()
        ctx = ArticleContext()
        logger.addFilter(ctx)

        logger.info(f"IO dirs: {io_dirs}")
        
        # nastavi nivo logiranja glede na DEBUG flag
        if config["DEBUG"][0] == "True":
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        
        input_dir = io_dirs["input"]
        authors_delimiters = config['BIBLIOGRAPHY_DELIMITER']
        try:
            src_file = os.listdir(input_dir)[0]
            src_file_name = os.path.join(input_dir,src_file)
            logger.info(f"Source file: {src_file_name}")
        except (IndexError, FileNotFoundError) as e:
            logger.critical(f"Error finding input file: {e}")
            return 1
        tmp_dir = io_dirs["input"].with_name(io_dirs["input"].name + "_multi")
        out_dir = io_dirs["output"]
        tmp_output_dir = io_dirs["output"].with_name(io_dirs["output"].name + "_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)
        os.makedirs(tmp_output_dir, exist_ok=True)
        doc = pymupdf.open(src_file_name)
        parts = split_into_parts(doc, config['ARTICLE_BREAKS'], tmp_dir, src_file_name)
        doc.close()
        linked_parts = []
        
        # stevci za clanke in vmesne dele
        article_counter = 0
        gap_counter = 0

        for part in parts:
            logger.info("=" * 60)
            if not part["isRange"]:
                # vmesni del (gap)
                gap_counter += 1
                ctx.article_num = f"gap_{gap_counter}"
                ctx.page_in_article = None
                ctx.page_in_doc = None
                
                file_name = part["path"]
                doc = pymupdf.open(file_name)
                base, ext = os.path.splitext(os.path.basename(file_name))
                output_filename = base + "_linked" + ext
                output_path = os.path.join(tmp_output_dir, output_filename)
                doc.save(output_path)
                doc.close()
                linked_parts.append(output_path)
                logger.info(f"Gap file output: {output_path}")
                continue
            
            # clanek - nastavi kontekst
            article_counter += 1
            article_start_page = part["start_page"]  # original start page in source PDF
            article_end_page = part["end_page"]      # original end page in source PDF
            ctx.article_num = article_counter
            ctx.page_in_article = None
            ctx.page_in_doc = article_start_page + 1  # 1-based global page number
            
            # obdelava clanka z try/except za graceful error handling
            try:
                file_name = part["path"]
                logger.info(f"Processing article file: {file_name}")
                doc = pymupdf.open(file_name)
                # pass article_start_page to find_delimiting_page for correct page tracking
                authors_page, authors_delimiter = find_delimiting_page(authors_delimiters, doc, ctx, article_start_page)
                if authors_page == -1 or authors_delimiter == -1:
                    logger.warning(f"Bibliography delimiter not found in document: {file_name} - skipping article")
                    doc.close()
                    continue

                # pass ctx and article_start_page to all helper functions
                authors_info = extract_authors_from_pdf(doc, authors_page, authors_delimiter, ctx, article_start_page)
                references_info = screen_text(doc, authors_page, authors_delimiter, ctx, article_start_page)
                print_bibliography_info(authors_info, ctx, article_start_page)
                print_references_info(references_info, ctx, article_start_page)

                reference_connector(authors_info, references_info, doc, ctx, article_start_page)

                #naredi nov file z narejenimi povezavami, original ostane isti
                base, ext = os.path.splitext(os.path.basename(file_name))
                output_filename = base + "_linked" + ext
                output_path = os.path.join(tmp_output_dir, output_filename)
                linked_parts.append(output_path)
                doc.save(output_path)
                doc.close()
                logger.info(f"Document successfully linked: {output_path}")
            except Exception as e:
                logger.error(f"Unexpected error processing article {file_name} - skipping. Error: {e}", exc_info=True)
                if 'doc' in locals():
                    doc.close()
                continue
            
            logger.info("=" * 60)
        merge_linked_parts(linked_parts, src_file, out_dir)
        shutil.rmtree(tmp_dir)
        shutil.rmtree(tmp_output_dir)
        return 0
    except Exception as e:
        logger.critical(f"Error during linking process: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
