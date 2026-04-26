from collections import defaultdict

import pymupdf

""" struct: 
spacing_check = { "last": 0.0,
                 "current": 0.0,
                 "tolerance": spacing_tolerance,
                 "common_line_spacing": common_line_spacing}
"""
def is_empty_line(spacing_check):
    difference = spacing_check["current"] - spacing_check["last"]
    if spacing_check["common_line_spacing"] == None:
        return False
    if difference > spacing_check["tolerance"] + spacing_check["common_line_spacing"]:
        return True
    return False



def _collect_bibliography_line_rects(doc, start_page_idx, delimiter):
    bibliography_started = False
    line_rects = []

    for page_idx in range(start_page_idx, len(doc)):
        page = doc[page_idx]
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                line_text = " ".join(span.get("text", "") for span in spans).strip()
                if not bibliography_started and delimiter not in line_text:
                    continue

                bibliography_started = True
                bbox = line.get("bbox")
                if bbox:
                    line_rects.append((page_idx, pymupdf.Rect(bbox)))

    return line_rects


def _build_spacing_sequence(line_rects, min_spacing, max_spacing):
    spacings = []
    if len(line_rects) < 2:
        return spacings

    prev_page_idx, prev_rect = line_rects[0]
    for page_idx, curr_rect in line_rects[1:]:
        if page_idx != prev_page_idx:
            prev_page_idx, prev_rect = page_idx, curr_rect
            continue

        spacing = curr_rect.y0 - prev_rect.y0
        prev_page_idx, prev_rect = page_idx, curr_rect

        if spacing <= min_spacing or spacing > max_spacing:
            continue
        spacings.append(spacing)

    return spacings


def _bucket_spacing(spacing, tolerance):
    if tolerance <= 0:
        return spacing
    return round(spacing / tolerance) * tolerance


def find_common_line_spacing(
    doc,
    start_page_idx,
    delimiter,
    *,
    tolerance=0.75,
    min_spacing=0.0,
    max_spacing=120.0,
):
    line_rects = _collect_bibliography_line_rects(doc, start_page_idx, delimiter)
    spacing_sequence = _build_spacing_sequence(line_rects, min_spacing, max_spacing)
    if not spacing_sequence:
        return None

    grouped_spacings = defaultdict(list)
    bucket_sequence = []
    for spacing in spacing_sequence:
        bucket = _bucket_spacing(spacing, tolerance)
        grouped_spacings[bucket].append(spacing)
        bucket_sequence.append(bucket)

    longest_run_by_bucket = defaultdict(int)
    run_bucket = None
    run_len = 0
    for bucket in bucket_sequence:
        if bucket == run_bucket:
            run_len += 1
        else:
            if run_bucket is not None:
                longest_run_by_bucket[run_bucket] = max(longest_run_by_bucket[run_bucket], run_len)
            run_bucket = bucket
            run_len = 1
    if run_bucket is not None:
        longest_run_by_bucket[run_bucket] = max(longest_run_by_bucket[run_bucket], run_len)

    best_bucket = max(
        grouped_spacings,
        key=lambda bucket: (len(grouped_spacings[bucket]), longest_run_by_bucket[bucket]),
    )
    best_values = grouped_spacings[best_bucket]
    return sum(best_values) / len(best_values)
