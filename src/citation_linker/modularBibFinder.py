
import  pymupdf
import  re
from    .utils              import years_span_parser, alternative_names_concat
from    .configLoad         import config
from    .appLogger          import get_logger
from    .lineSpacing        import find_common_line_spacing, is_empty_line
from    .modularBibUtils    import (
                                    year_search_pattern,
                                    year_span_pattern,
                                    is_capitalized,
                                    is_year_or_span,
                                    is_separator_or_char,
                                    find_separator_char,
                                    is_word_boundary,
                                    normalize_structure_type,
                                    normalize_options,
                                    parse_bool,
                                    dedupe_keep_order
                                    )
                                    


logger = get_logger()


### poglej vrstice  - ce ima vrstica priimek, ime, leto vzemi ves tekst do naslednjega moznega zacetka elementa, oz konca tektsta
### parser je sestavljen iz FE: npr <priimek> <separator:<,>> <ime> <separator:<,>> <extra char:<(,">> <leto> <extra char:<),">>
### kako je razdeljeno ko je vec avtorjev
### ko imamo ves teks, posljemo v tokenizer da razdeli dele, 
r"""
bib_structures = [
    [
        {"type": "Surname"},
        {"type": "separator", "options": [","]},
        {"type": "Name"},
        {"type": "separator", "options": [":,", "::,"]},
        {"type": "extra_char", "value": "("}, ### extra char bi moral biti zmeraj v parih (oklepajni char?)
        {"type": "Year"},
        {"type": "extra_char", "value": ")"},
        {"type": "separator", "options": ["::"]},
        {"type": "Title"},
        {"type": "separator", "options": ["."]},
        {"type": "ignore"}
    ],
    # ... more structures
]

#other option

 compiled_schema = {
   "name": "default_style",
   "elements": [
     {"type": "SURNAME",   "required": True,  "validator": is_capitalized_word},
     {"type": "SEPARATOR", "required": True,  "matcher": one_of([",", ";"])},
     {"type": "NAME",      "required": True,  "validator": is_capitalized_name},
     {"type": "EXTRA_CHAR","required": False, "matcher": one_of(["(", '"', "'"])},
     {"type": "YEAR",      "required": True,  "regex": re.compile(r"\d{4}[a-zA-Z]?")},
     {"type": "EXTRA_CHAR","required": False, "matcher": paired_closer},  # ) or " or '
     {"type": "SEPARATOR", "required": False, "matcher": one_of([":", ".", "—"])},
     {"type": "TITLE",     "required": True,  "validator": is_title_start_upper},
     {"type": "IGNORE",    "required": False}
   ]
 }
"""

def _find_separator_in_text(text, option):
    """Find first occurrence of option in text, respecting word boundaries for word-like separators."""
    if not re.search(r'\w', option):
        return text.find(option)
    pos = 0
    while pos < len(text):
        found = text.find(option, pos)
        if found == -1:
            return -1
        if is_word_boundary(text, found, found + len(option)):
            return found
        pos = found + 1
    return -1


def find_separator_outside_wrappers(text, separator_options, wrapper_options=None):
    text = text.strip()
    if not text:
        return -1, ""

    separator_options = [opt for opt in (separator_options or []) if isinstance(opt, str) and opt]
    if not separator_options:
        return -1, ""
    separator_options = sorted(separator_options, key=len, reverse=True)

    wrapper_chars = {
        opt for opt in (wrapper_options or [])
        if isinstance(opt, str) and len(opt) == 1
    }
    paired_wrappers = {"(": ")", "[": "]", "{": "}", "<": ">"}
    symmetric_wrappers = {char for char in wrapper_chars if paired_wrappers.get(char) == char}
    for quote_char in ('"', "'"):
        if quote_char in wrapper_chars:
            symmetric_wrappers.add(quote_char)

    idx = 0
    stack = []
    while idx < len(text):
        curr_char = text[idx]

        if curr_char in symmetric_wrappers:
            if stack and stack[-1] == curr_char:
                stack.pop()
            else:
                stack.append(curr_char)
            idx += 1
            continue

        if stack and curr_char == stack[-1]:
            stack.pop()
            idx += 1
            continue

        if curr_char in wrapper_chars and curr_char in paired_wrappers:
            stack.append(paired_wrappers[curr_char])
            idx += 1
            continue

        if not stack:
            for option in separator_options:
                if text.startswith(option, idx):
                    if re.search(r'\w', option) and not is_word_boundary(text, idx, idx + len(option)):
                        logger.debug(
                            f"  find_separator: word-sep {repr(option)} at idx={idx} "
                            f"NOT at word boundary in {repr(text[:60])}, skipping"
                        )
                        continue
                    return idx, option
        idx += 1

    return -1, ""

        
def validator_selector(text, typ_element):
    typ = (typ_element.get("TYPE") or typ_element.get("type") or "IGNORE").upper()
    if typ == "SURNAME" and is_capitalized(text, all=True):
        return "SURNAME"

    if typ == "NAME" and is_capitalized(text, all=True):
        return "NAME"

    elif typ == "TITLE" and is_capitalized(text, all=False):
        return "TITLE"

    elif typ == "EXTRA_CHAR" and is_separator_or_char(text, typ_element.get("OPTIONS") or typ_element.get("options", "")):
        return "EXTRA_CHAR"

    elif typ == "YEAR":
        return is_year_or_span(text)

    elif typ == "SEPARATOR" and is_separator_or_char(text, typ_element.get("OPTIONS") or typ_element.get("options", "")):
        return "SEPARATOR"

    elif typ == "OTHER_AUTHORS" and text.strip():
        return "OTHER_AUTHORS"

    else:
        return "IGNORE"

# preveri ce je naslednji token pravilen glede na bib structure
def _next_expected_type_looks_valid(text, remaining_struct):
    probe = text.strip()
    if not probe:
        return False

    for elem in remaining_struct:
        if not isinstance(elem, dict):
            continue
        typ = (elem.get("type") or elem.get("TYPE") or "").upper()
        if not typ:
            continue

        if typ == "SEPARATOR":
            options = sorted(elem.get("options") or elem.get("OPTIONS") or [","], key=len, reverse=True)
            matched = False
            for opt in options:
                if probe.startswith(opt):
                    probe = probe[len(opt):].strip()
                    matched = True
                    break
            if matched:
                continue
            continue

        if typ == "EXTRA_CHAR":
            options = sorted(elem.get("options") or elem.get("OPTIONS") or [], key=len, reverse=True)
            if not options:
                continue
            for opt in options:
                if probe.startswith(opt):
                    probe = probe[len(opt):].strip()
                    break
            else:
                return False
            continue

        if typ == "YEAR":
            return bool(re.match(r"^\d{4}[a-zA-Z]?\b", probe) or re.match(r"^\d{4}\s{0,2}[-–—]{1,2}\s{0,2}\d{4}", probe))

        if typ in ("SURNAME", "NAME", "TITLE"):
            return bool(probe and probe[0].isupper())

        if typ == "OTHER_AUTHORS":
            return bool(probe)

        if typ == "IGNORE":
            return True

    return bool(probe)


def _separator_candidates_outside_wrappers(text, separator_options, wrapper_options=None):
    text = text.strip()
    options = [opt for opt in (separator_options or []) if isinstance(opt, str) and opt]
    if not text or not options:
        return []
    options = sorted(options, key=len, reverse=True)

    wrapper_chars = {
        opt for opt in (wrapper_options or [])
        if isinstance(opt, str) and len(opt) == 1
    }
    paired_wrappers = {"(": ")", "[": "]", "{": "}", "<": ">"}
    symmetric_wrappers = {char for char in wrapper_chars if paired_wrappers.get(char) == char}
    for quote_char in ('"', "'"):
        if quote_char in wrapper_chars:
            symmetric_wrappers.add(quote_char)

    idx = 0
    stack = []
    matches = []
    while idx < len(text):
        curr_char = text[idx]

        if curr_char in symmetric_wrappers:
            if stack and stack[-1] == curr_char:
                stack.pop()
            else:
                stack.append(curr_char)
            idx += 1
            continue

        if stack and curr_char == stack[-1]:
            stack.pop()
            idx += 1
            continue

        if curr_char in wrapper_chars and curr_char in paired_wrappers:
            stack.append(paired_wrappers[curr_char])
            idx += 1
            continue

        if not stack:
            for option in options:
                if text.startswith(option, idx):
                    matches.append((idx, option))
                    break
        idx += 1
    return matches


def _extract_other_authors_segment(curr_text, other_elem, separator_options, wrapper_options, remaining_struct):
    text = curr_text.strip()
    if not text:
        return "", ""

    candidates = _separator_candidates_outside_wrappers(text, separator_options, wrapper_options)
    if not candidates:
        return text, ""

    expected_types_ahead = any(
        isinstance(elem, dict) and (elem.get("type") or elem.get("TYPE") or "").upper() not in ("SEPARATOR", "IGNORE")
        for elem in remaining_struct
    )
    if not expected_types_ahead:
        return text, ""

    other_options = normalize_options(other_elem.get("options") or other_elem.get("OPTIONS") or ["and", "in", ","])
    other_options_lc = {opt.lower() for opt in other_options}
    sep_options_lc = {opt.lower() for opt in (separator_options or [])}
    shared_separator = bool(other_options_lc & sep_options_lc)

    if not shared_separator:
        split_idx, used_option = candidates[0]
        return text[:split_idx].strip(), text[split_idx + len(used_option):].strip()

    for split_idx, used_option in candidates:
        left = text[:split_idx].strip()
        right = text[split_idx + len(used_option):].strip()
        if not left or not right:
            continue
        if _next_expected_type_looks_valid(right, remaining_struct):
            return left, right

    for elem in remaining_struct:
        if not isinstance(elem, dict):
            continue
        typ = (elem.get("type") or elem.get("TYPE") or "").upper()
        if typ == "YEAR":
            year_match = re.search(r"\d{4}[a-zA-Z]?\b", text)
            if year_match and year_match.start() > 0:
                left = text[:year_match.start()].strip(" \t\n\r,;:.")
                right = text[year_match.start():].strip()
                if left and right:
                    return left, right
            break
        if typ not in ("SEPARATOR", "EXTRA_CHAR", "IGNORE"):
            break

    split_idx, used_option = candidates[-1]
    return text[:split_idx].strip(), text[split_idx + len(used_option):].strip()



# tokenizira pravilno avtor tokne
def _extract_other_author_values(text, options=None):
    if not text:
        return []
    work_text = " ".join(text.split()).strip(" \t\n\r,;:.")
    if not work_text:
        return []

    options = normalize_options(options or ["and", "in", ","])
    punctuation_separators = [opt for opt in options if re.fullmatch(r"[^\w\s]+", opt or "")]
    word_separators = [re.escape(opt) for opt in options if opt and re.search(r"\w", opt)]

    split_text = work_text
    for punct in punctuation_separators:
        split_text = split_text.replace(punct, ",")
    if word_separators:
        split_text = re.sub(rf"\s+(?:{'|'.join(word_separators)})\s+", ",", split_text, flags=re.IGNORECASE)

    chunks = [chunk.strip(" \t\n\r,;:.()[]{}") for chunk in split_text.split(",")]
    full_names = []
    for chunk in chunks:
        if not chunk:
            continue
        cleaned = re.sub(r"\(\s*(?:ur\.?|ed\.?|eds\.?|editor(?:s)?|edited by)\s*\)", " ", chunk, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:ur\.?|ed\.?|eds\.?|editor(?:s)?|edited by)\b\.?", " ", cleaned, flags=re.IGNORECASE)
        cleaned = " ".join(cleaned.split()).strip(" \t\n\r,;:.()[]{}")
        if cleaned and any(token and token[0].isupper() for token in cleaned.split()):
            full_names.append(cleaned)

    values = []
    values.extend(full_names)
    for full_name in full_names:
        values.extend(alternative_names_concat(full_name))
        for token in full_name.split():
            token = token.strip(" \t\n\r,;:.()[]{}")
            if token and token[0].isupper():
                values.append(token)
    return dedupe_keep_order(values)


def normalize_bib_structures(raw_bib_structures):
    # Supports both dict and flat-string elements.
    # Flat-string example for configurable co-authors:
    #   OTHER_AUTHORS:required=False:options=,|and|in
    if not isinstance(raw_bib_structures, list) or not raw_bib_structures:
        return []

    if all(isinstance(struct, list) for struct in raw_bib_structures):
        candidate_structures = raw_bib_structures
    elif all(isinstance(elem, dict) for elem in raw_bib_structures):
        candidate_structures = [raw_bib_structures]
    else:
        candidate_structures = [raw_bib_structures]

    normalized_structures = []
    for raw_struct in candidate_structures:
        if not isinstance(raw_struct, list):
            continue
        normalized_struct = []
        for raw_elem in raw_struct:
            if isinstance(raw_elem, dict):
                typ = normalize_structure_type(raw_elem.get("type") or raw_elem.get("TYPE"))
                if not typ:
                    continue
                elem = {"type": typ}
                if "required" in raw_elem or "REQUIRED" in raw_elem:
                    elem["required"] = parse_bool(raw_elem.get("required") if "required" in raw_elem else raw_elem.get("REQUIRED"), True)
                if typ in ("SEPARATOR", "EXTRA_CHAR", "OTHER_AUTHORS"):
                    options = normalize_options(raw_elem.get("options") or raw_elem.get("OPTIONS"))
                    if typ == "SEPARATOR" and not options:
                        options = [","]
                    if typ == "OTHER_AUTHORS" and not options:
                        options = [",", "and", "in"]
                    elem["options"] = options
                normalized_struct.append(elem)
                continue

            if not isinstance(raw_elem, str):
                continue
            token = raw_elem.strip()
            if not token:
                continue

            if re.fullmatch(r"[^\w\s]+", token):
                if normalized_struct and normalized_struct[-1].get("type") in ("SEPARATOR", "EXTRA_CHAR"):
                    prev_options = normalized_struct[-1].setdefault("options", [])
                    if token not in prev_options:
                        prev_options.append(token)
                continue

            parts = [part.strip() for part in token.split(":") if part.strip()]
            raw_type = parts[0] if parts else ""
            typ = normalize_structure_type(raw_type)
            if not typ:
                continue

            elem = {"type": typ}
            legacy_options = []
            for meta in parts[1:]:
                if "=" not in meta:
                    legacy_options.append(meta)
                    continue
                key, value = [part.strip() for part in meta.split("=", 1)]
                key_upper = key.upper()
                if key_upper == "REQUIRED":
                    elem["required"] = parse_bool(value, True)
                elif key_upper == "OPTIONS":
                    elem["options"] = normalize_options(value)

            if typ in ("SEPARATOR", "EXTRA_CHAR", "OTHER_AUTHORS"):
                options = elem.get("options", [])
                if not options and legacy_options:
                    options = normalize_options("|".join(legacy_options))
                if typ == "SEPARATOR" and not options:
                    options = [","]
                if typ == "OTHER_AUTHORS" and not options:
                    options = [",", "and", "in"]
                elem["options"] = options
            normalized_struct.append(elem)

        if normalized_struct:
            normalized_structures.append(normalized_struct)

    return normalized_structures




##pogleda kaj je prvi token, in gleda do separatorja
## morata biti vsaj dva matcha
#def is_valid_type(token, bib_structure):
#    pass


def line_has_author(line_text):
    bib_structures = normalize_bib_structures(config.get("BIB_STRUCTURE", ""))
    if not bib_structures:
        logger.debug(f"line_has_author: no bib_structures configured, returning False")
        return False
    orig_line_text = line_text.strip()

    for struct_idx, struct in enumerate(bib_structures):
        if not isinstance(struct, list):
            continue
        hits = 0
        separators_found = 0
        line_text = orig_line_text
        for typ_element in struct:
            if not isinstance(typ_element, dict):
                continue
            typ = (typ_element.get("type") or typ_element.get("TYPE") or "").upper()
            # Only count a SURNAME/NAME/TITLE hit when the text has actually been
            # advanced past at least one separator (prevents false positives on plain
            # capitalized words like "Literatura" that have no commas/colons).
            if (typ in ("SURNAME", "NAME", "TITLE")
                and line_text and line_text[0].isupper()):
                if typ == "SURNAME" or separators_found > 0:
                    hits += 1

            elif typ in ("SEPARATOR", "EXTRA_CHAR"):
                options = typ_element.get("OPTIONS") or typ_element.get("options") or [","]
                options = sorted(options, key=len, reverse=True)

                cut_idx = -1
                used_option = None
                for opt in options:
                    pos = _find_separator_in_text(line_text, opt)
                    if pos != -1:
                        cut_idx = pos
                        used_option = opt
                        break
                if cut_idx == -1:
                    continue
                separators_found += 1
                line_text = line_text[cut_idx + len(used_option):].strip()

            elif typ == "YEAR":
                if year_search_pattern.search(line_text):
                    hits += 1
            if hits >= 2:
                logger.debug(f"line_has_author [struct {struct_idx}]: TRUE for: {repr(orig_line_text[:60])}")
                return True
        logger.debug(f"line_has_author [struct {struct_idx}]: hits={hits}, separators_found={separators_found}, remaining_text={repr(line_text[:40])}")
    logger.debug(f"line_has_author: FALSE for: {repr(orig_line_text[:60])}")
    return False


def content_token_sorting(text, typ_elements, n=1):
    tokens = []

    curr_text = text
    if not typ_elements:
        return tokens
    if n == 1:
        valid_type = validator_selector(text, typ_elements[0])
        tokens.append({
            "text": text.strip(),
            "type": valid_type
            })
        logger.debug(f"  content_token_sorting n=1: text={repr(text[:40])} → type={valid_type}")
        return tokens

    elif n > 1:
        logger.debug(f"  content_token_sorting n={n}: text={repr(curr_text[:40])}, types={[e.get('type') for e in typ_elements]}")
        for elem in typ_elements[:]:
            if len(curr_text) < 1:
                return tokens
            typ = elem.get("type", "").upper()
            if not typ:
                typ = (elem.get("TYPE") or "").upper()

            if typ == "EXTRA_CHAR":
                # normalize_bib_structures stores "options" in lowercase; uppercase
                # OPTIONS was a typo that always fell back to [""], causing find("")
                # to return 0 and silently strip the first char of curr_text.
                extra_options = elem.get("options") or elem.get("OPTIONS") or []
                if not extra_options:
                    continue
                char_idx = find_separator_char(curr_text, extra_options)
                if char_idx == -1:
                    continue
                # curr_text = curr_text[char_idx:]
                if char_idx + 1 < len(curr_text):
                    curr_text =  curr_text[:char_idx] + curr_text[char_idx+1:]
                    typ_elements.remove(elem)
                else:
                    curr_text = ""
                    typ_elements.remove(elem)
        if curr_text and curr_text[0] and len(typ_elements) == 1:
            tokens += content_token_sorting(curr_text, typ_elements, len(typ_elements))
        elif curr_text and len(typ_elements) == 2:
            # NAME/SURNAME/TITLE/OTHER_AUTHORS + YEAR pair left after stripping EXTRA_CHARs:
            # find the year in the remaining text and split around it
            type_pairs = [(e, (e.get("type") or e.get("TYPE") or "").upper()) for e in typ_elements]
            year_elem = next((e for e, t in type_pairs if t == "YEAR"), None)
            name_elem = next((e for e, t in type_pairs if t in ("NAME", "SURNAME", "TITLE", "OTHER_AUTHORS")), None)
            logger.debug(f"  content_token_sorting n=2 pair: year_elem={year_elem is not None}, name_elem={name_elem is not None}, types={[t for _,t in type_pairs]}")
            if year_elem and name_elem:
                year_match = year_search_pattern.search(curr_text)
                if year_match:
                    name_text = curr_text[:year_match.start()].strip(" \t\n\r,;:.()")
                    year_text = year_match.group()
                    if name_text:
                        tokens.append({"text": name_text, "type": validator_selector(name_text, name_elem)})
                    tokens.append({"text": year_text, "type": "YEAR"})
            elif name_elem and not year_elem:
                name_text = curr_text.strip(" \t\n\r,;:.()")
                if name_text:
                    tokens.append({"text": name_text, "type": validator_selector(name_text, name_elem)})
            else:
                logger.debug(f"  content_token_sorting n=2: UNHANDLED pair {[t for _,t in type_pairs]} — no tokens produced for text={repr(curr_text[:40])}")
        return tokens

    return tokens

# primerja vse moznosti v token bank in izbere najboljso
def stronger_match(token_bank):
    # Prefer structurally valid bibliography parses (surname + year/year-span)
    # over noisy token-rich parses that miss core fields.
    winner_tokens = token_bank[0] if token_bank else []
    winner_score = (-1, -1, -1, -1, -1)

    for tkns in token_bank:
        token_types = {(tkn.get("type") or "").upper() for tkn in tkns if isinstance(tkn, dict)}
        has_surname = "SURNAME" in token_types
        has_year = "YEAR" in token_types or "YEAR_SPAN" in token_types
        has_name = "NAME" in token_types
        has_other_authors = "OTHER_AUTHORS" in token_types or "OTHERS" in token_types

        score = (
            1 if (has_surname and has_year) else 0,
            1 if has_surname else 0,
            1 if has_year else 0,
            1 if has_name else 0,
            len(tkns) + (1 if has_other_authors else 0),
        )
        if score > winner_score:
            winner_score = score
            winner_tokens = tkns

    return winner_tokens

# naredi dict z vsemi info od bib entry
def create_bib_entry(tokens):
    bib_entry = {
        "surname": "yyy",
        "name":"yyy",
        "year":"yyy",
        "others": [],
        "years": [],
        "year_span": "yyy"
    }
    for tkn in tokens:
        typ = tkn.get("type")
        text = tkn.get("text")
        if typ == "SURNAME":
            bib_entry["surname"] = text or "yyy"
        elif typ == "NAME":
            bib_entry["name"] = text or "yyy"
        # TODO check ce je yearspan ali mora potem tudi prva letnica iz span biti v year
        elif typ == "YEAR":
            year_match = year_search_pattern.search(text or "")
            year_token = year_match.group() if year_match else (text or "yyy")
            bib_entry["year"] = year_token
            bib_entry["years"].append(year_token)
        elif typ == "YEAR_SPAN":
            span_match = year_span_pattern.search(text or "")
            span_token = span_match.group() if span_match else (text or "yyy")
            bib_entry["year_span"] = span_token
            # razsiri leta iz razpona (mora biti zmeraj zapolnjen years da debugUtils ne crasha)
            if span_token and span_token != "yyy":
                bib_entry["years"] = years_span_parser(span_token, bib_entry["years"])
        elif typ in ("OTHERS", "OTHER_AUTHORS"):
            other_options = tkn.get("options") or []
            if typ == "OTHER_AUTHORS":
                bib_entry["others"].extend(_extract_other_author_values(text, other_options))
            elif text:
                bib_entry["others"].append(text)
        # Add more types as needed
    bib_entry["others"] = dedupe_keep_order(bib_entry["others"])
    if not bib_entry["others"]:
        bib_entry["others"] = ["yyy"]
    # zagotovi da years nikoli ni prazen (debugUtils dostopa years[0] brez guarda)
    if not bib_entry["years"]:
        bib_entry["years"] = ["yyy"]
    return bib_entry


#Preveri, ali je razčlenjen bibliografski zapis veljaven.
#Kriteriji za veljaven zapis:
#- Mora imeti priimek (ne sme biti nadomestni znak "yyy")
#- Mora imeti leto ali obdobje let (ne sme biti nadomestni znak "yyy")
#Vrne True, če zapis prestane validacijo, sicer False (kar naj sproži ponovni poskus).
def _is_entry_valid(entry_result):
    if not isinstance(entry_result, dict):
        logger.debug(f"  _is_entry_valid: not a dict → False")
        return False

    surname = entry_result.get("surname", "yyy")
    year = entry_result.get("year", "yyy")
    year_span = entry_result.get("year_span", "yyy")

    has_valid_surname = surname and surname != "yyy"
    has_valid_year = (year and year != "yyy") or (year_span and year_span != "yyy")

    if not has_valid_surname:
        logger.debug(f"  _is_entry_valid: INVALID — surname missing/placeholder (surname={repr(surname)})")
    if not has_valid_year:
        logger.debug(f"  _is_entry_valid: INVALID — year missing/placeholder (year={repr(year)}, year_span={repr(year_span)})")
    if has_valid_surname and has_valid_year:
        logger.debug(f"  _is_entry_valid: VALID — surname={repr(surname)}, year={repr(year)}")

    return has_valid_surname and has_valid_year

# preverjanje in tokeniziranje raw text za mozen bib entry
def tokenize_author_entry(line_text):
    # Poenotimo presledke tudi tu, da neposredni klici (preview, testi) delujejo
    # enako kot pot prek extract_authors_modular — glej opombo pri branju vrstic.
    line_text = re.sub(r"\s", " ", line_text)
    valid_structures = normalize_bib_structures(config.get("BIB_STRUCTURE", ""))
    if not valid_structures:
        logger.debug(f"tokenize_author_entry: no valid structures configured")
        return create_bib_entry([])
    token_bank = [[] for _ in valid_structures]
    bib_entry = create_bib_entry([])

    logger.debug(f"tokenize_author_entry: input={repr(line_text[:80])}")

    for struct_idx, struct in enumerate(valid_structures):
        curr_text = line_text
        tokens = token_bank[struct_idx]
        segment_types = []
        wrapper_options = []

        for typ_element in struct:
            if not isinstance(typ_element, dict):
                continue
            typ = (typ_element.get("type") or typ_element.get("TYPE") or "").upper()
            if typ != "EXTRA_CHAR":
                continue
            options = typ_element.get("OPTIONS") or typ_element.get("options") or []
            if isinstance(options, str):
                options = [options]
            wrapper_options.extend([opt for opt in options if isinstance(opt, str) and opt.strip()])

        logger.debug(f"  struct {struct_idx}: types={[e.get('type') for e in struct if isinstance(e, dict)]}")

        for elem_idx, typ_element in enumerate(struct):
            if not isinstance(typ_element, dict):
                continue
            typ = (typ_element.get("type") or typ_element.get("TYPE") or "").upper()
            if typ == "SEPARATOR":
                options = typ_element.get("OPTIONS") or typ_element.get("options") or [","]
                options = sorted(options, key=len, reverse=True)

                remaining_struct = struct[elem_idx + 1:]
                if (len(segment_types) == 1
                    and (segment_types[0].get("type") or segment_types[0].get("TYPE") or "").upper() == "OTHER_AUTHORS"):
                    other_segment = segment_types[0]
                    other_text, remaining_text = _extract_other_authors_segment(
                        curr_text,
                        other_segment,
                        options,
                        wrapper_options,
                        remaining_struct,
                    )
                    logger.debug(f"    SEP{options} [OTHER_AUTHORS path]: other_text={repr(other_text[:40])}, remaining={repr(remaining_text[:40])}")
                    if other_text:
                        tokens.append({
                            "text": other_text.strip(),
                            "type": "OTHER_AUTHORS",
                            "options": other_segment.get("options") or other_segment.get("OPTIONS") or [],
                        })
                    curr_text = remaining_text
                    segment_types = []
                    continue

                separator_idx, used_option = find_separator_outside_wrappers(curr_text, options, wrapper_options)
                if separator_idx == -1:
                    logger.debug(f"    SEP{options}: NOT FOUND in curr_text={repr(curr_text[:50])}, accumulated_segs={[e.get('type') for e in segment_types]}")
                    continue
                curr_tokens_text = curr_text[:separator_idx]
                curr_text = curr_text[separator_idx + len(used_option):].strip()
                logger.debug(f"    SEP{options} at {separator_idx}: extracted={repr(curr_tokens_text[:40])}, remaining={repr(curr_text[:40])}, segs={[e.get('type') for e in segment_types]}")
                curr_tokens = content_token_sorting(curr_tokens_text, segment_types[:], len(segment_types))
                tokens.extend(curr_tokens)
                segment_types = []
                continue

            segment_types.append(typ_element)

        if segment_types and curr_text:
            logger.debug(f"  struct {struct_idx} tail: remaining_text={repr(curr_text[:50])}, segs={[e.get('type') for e in segment_types]}")
            if (len(segment_types) == 1
                and (segment_types[0].get("type") or segment_types[0].get("TYPE") or "").upper() == "OTHER_AUTHORS"):
                tokens.append({
                    "text": curr_text.strip(),
                    "type": "OTHER_AUTHORS",
                    "options": segment_types[0].get("options") or segment_types[0].get("OPTIONS") or [],
                })
            else:
                curr_tokens = content_token_sorting(curr_text, segment_types[:], len(segment_types))
                tokens.extend(curr_tokens)

        logger.debug(f"  struct {struct_idx} tokens: {[(t.get('type'), repr(t.get('text','')[:20])) for t in tokens]}")

    tokens = stronger_match(token_bank)
    bib_entry = create_bib_entry(tokens)
    logger.debug(f"tokenize_author_entry: result surname={repr(bib_entry.get('surname'))}, name={repr(bib_entry.get('name'))}, year={repr(bib_entry.get('year'))}")
    return bib_entry


# poisce in vrne list[dict] z vsemi informacijami glede avtorjev v bibliografiji
# stil bibliografije lahko doloci uporabnik (za razliko od extract_authors_from_pdf) nekaj v stilu:
# npr <priimek> <separator:<,>> <ime> <separator:<,>> <extra char:<(,">> <leto> <extra char:<),">>
def extract_authors_modular(doc, page_idx, delimiter, ctx=None, article_start_page=0):
    start_bib = False
    lines_info = []
    start_page_idx = page_idx
    common_line_spacing = find_common_line_spacing(doc, start_page_idx, delimiter)
    spacing_tolerance = 0.75

    logger.debug(f"extract_authors_modular: starting at page_idx={page_idx}, delimiter={repr(delimiter)}, common_line_spacing={common_line_spacing}")

    bib_structures = normalize_bib_structures(config.get("BIB_STRUCTURE", ""))
    logger.debug(f"extract_authors_modular: {len(bib_structures)} structure(s) loaded")
    for i, s in enumerate(bib_structures):
        logger.debug(f"  structure {i}: {[e.get('type') for e in s if isinstance(e, dict)]}")

    if ctx:
        ctx.common_line_spacing = common_line_spacing

    # Global line buffer: accumulate all lines from all pages for index-based processing
    all_lines_buffer = []

    # zbere vse strani
    #TODO odstrani header/footer
    temp_page_idx = page_idx
    while temp_page_idx < len(doc):
        page = doc[temp_page_idx]
        for block in page.get_text("dict")["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    # Span-e sestavimo brez vrinjenega presledka: PyMuPDF pogosto
                    # razbije eno besedo na več sosednjih span-ov (npr. "Viri" ->
                    # "V" + "iri"), dejanske presledke pa vrne kot lastne span-e.
                    # " ".join bi zato vrinil lažne presledke sredi besed ("V iri").
                    # Presledek vstavimo le ob dejanski vodoravni vrzeli med span-i
                    # (enako kot to naredi get_text("text") interno).
                    line_text = ""
                    prev_x1 = None
                    for span in line["spans"]:
                        span_text = span["text"]
                        x0, x1 = span["bbox"][0], span["bbox"][2]
                        if (prev_x1 is not None
                                and x0 - prev_x1 > 0.2 * span.get("size", 10)
                                and not line_text.endswith(" ")
                                and not span_text.startswith(" ")):
                            line_text += " "
                        line_text += span_text
                        prev_x1 = x1
                    # Poenotimo vse oblike presledka (\xa0, ozki NBSP ...) v ASCII
                    # presledek, da separator " " deluje tudi pri slovarskih PDF-jih.
                    line_text = re.sub(r"\s", " ", line_text)
                    line_rect = pymupdf.Rect(line["bbox"])
                    all_lines_buffer.append({
                        "text": line_text,
                        "rect": line_rect,
                        "page": temp_page_idx,
                        "y0": float(line_rect.y0),
                    })
        temp_page_idx += 1

    logger.debug(f"extract_authors_modular: {len(all_lines_buffer)} total lines buffered from page {page_idx} to {temp_page_idx-1}")

    # Second pass: parse entries with retry logic from collected lines
    bib_section_started = False
    current_line_idx = 0
    lines_checked_as_author = 0
    lines_failed_as_author = 0

    while current_line_idx < len(all_lines_buffer):
        line_data = all_lines_buffer[current_line_idx]
        line_text = line_data["text"]

        if ctx:
            ctx.page_in_article = (line_data["page"] - start_page_idx) + 1
            ctx.page_in_doc = article_start_page + line_data["page"] + 1

        if delimiter in line_text or bib_section_started:
            if not bib_section_started:
                logger.debug(f"extract_authors_modular: BIB DELIMITER found at line {current_line_idx}, page {line_data['page']}: {repr(line_text[:60])}")
            bib_section_started = True

            if line_has_author(line_text.strip()):
                lines_checked_as_author += 1
                entry_start_idx = current_line_idx
                entry_lines_indices = [entry_start_idx]
                author_entry_lines = line_text.strip()
                last_gathered_idx = entry_start_idx

                # zberi strani za ta vnos avtoja/dela
                next_idx = current_line_idx + 1
                while next_idx < len(all_lines_buffer):
                    next_line = all_lines_buffer[next_idx]
                    next_line_text = next_line["text"].strip()

                    # pregled ce je prazna vrstica (za prekinitev/zaljucek vnosa)
                    spacing_check = {
                        "last": all_lines_buffer[last_gathered_idx]["y0"],
                        "current": next_line["y0"],
                        "tolerance": spacing_tolerance,
                        "common_line_spacing": common_line_spacing,
                    }

                    # preverjanje ali se nadaljuje zbiranje vrstic ali ne
                    if line_has_author(next_line_text):
                        break
                    elif is_empty_line(spacing_check):
                        logger.debug(f"    entry accumulation stopped by empty-line spacing at line {next_idx}")
                        break
                    else:
                        # ce ni konec dodaj strani v zbirnik
                        author_entry_lines += " " + next_line_text
                        entry_lines_indices.append(next_idx)
                        last_gathered_idx = next_idx
                        next_idx += 1

                logger.debug(f"  ENTRY accumulated ({len(entry_lines_indices)} lines): {repr(author_entry_lines[:100])}")

                # parsing zbranih strani
                try:
                    entry_result = tokenize_author_entry(author_entry_lines)
                    entry_parsed_ok = _is_entry_valid(entry_result)
                except Exception as e:
                    logger.debug(f"Entry parsing exception at line {entry_start_idx}: {e}")
                    entry_parsed_ok = False

                if entry_parsed_ok:
                    entry_result.update({
                        "text": author_entry_lines,
                        "position": line_data["rect"],
                        "page": line_data["page"],
                    })
                    lines_info.append(entry_result)
                    logger.debug(f"  ENTRY ACCEPTED: surname={repr(entry_result.get('surname'))}, year={repr(entry_result.get('year'))}")
                    current_line_idx = entry_lines_indices[-1] + 1
                else:
                    lines_failed_as_author += 1
                    logger.debug(f"  ENTRY REJECTED: surname={repr(entry_result.get('surname'))}, year={repr(entry_result.get('year'))}")
                    # ce parsing ne uspe zacni ponovno zbiranje od naslednje vrstice po prvem
                    # line_has_author check
                    current_line_idx = entry_start_idx + 1

            else:
                # preverjanje line_has_author == false, premakni idx na naslednjo vrstico
                current_line_idx += 1

        else:
            # premakni na naslednjo stran dokler ne najde bib delimiter
            current_line_idx += 1

    logger.debug(f"extract_authors_modular: done. {len(lines_info)} entries accepted, {lines_failed_as_author} failed validation out of {lines_checked_as_author} line_has_author=True lines")

    if ctx:
        #debugger info
        ctx.page_in_article = None
        ctx.page_in_doc = article_start_page + 1
    return lines_info
