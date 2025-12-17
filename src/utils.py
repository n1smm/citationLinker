import re

# ce je letnica na primer 1999-2002 naredi array/list z letnicami od do
def years_span_parser(years_token, years):
    year_search_pattern = re.compile(r'\d{4}');
    years_span_pattern = re.compile(r'\d{4} {0,2}[-–—]{1,2} {0,2}\d{4}')
    match = years_span_pattern.search(years_token)
    if not match:
        return years
    year_span_token = match.group()
    # print(f"years_token in func: {years_token}, year_token_span: {year_span_token}")
    found_years = [int(year) for year in year_search_pattern.findall(year_span_token)]
    if len(found_years) == 2 and (found_years[0] < found_years[1]):
        year_array = list(range(found_years[0], found_years[1] + 1))
    else:
        return years

    # if len(year_array) > 15:
    #     return years
    years = [str(year) for year in year_array]
    return (years)

# doda eno leto prej in po letnici, za soft match (ce so napake)
# magic_value = "yyy"/"xxx"
def soft_year_expand(year, magic_value):
    if year == magic_value:
        return [magic_value]
    year_search_pattern = re.compile(r'\d{4}');
    match = year_search_pattern.search(year)
    if not match:
        return [magic_value]
    year_num = int(match.group()) 
    year_list = list(range(year_num -1, year_num + 2))
    return [str(year) for year in year_list]


# primerjanje dveh razlicnih razponov let. ce je en razpon povsem znotraj drugega (100% prekrivanje)
def year_span_match(span1, span2):
    year_search_pattern = re.compile(r'\d{4}');
    span1_array = [int(year) for year in year_search_pattern.findall(span1)]
    span2_array = [int(year) for year in year_search_pattern.findall(span2)]
    if len(span1_array) != 2 or len(span2_array) != 2:
        return False
    if span1_array[0] >= span2_array[0] and span1_array[1] <= span2_array[1]:
        return True
    if span1_array[0] <= span2_array[0] and span1_array[1] >= span2_array[1]:
        return True

    return False


# preprost sort (ce bi ga bilo treba razsiriti v prihodnosti) - vrne letnice brez dvojnikov
def years_sort(years):
    return sorted(set(years))

            
# 0 - normalizirati (brez whitespace)
# 1 - vstavi whitespace spredaj
# -1 - vstavi whitespace zadaj
# -2 - zamenja vse cudne za navaden '
def normalize_apostrophe(text, normalize):
    # text = re.sub(r"[`’]", "'", text)
    if normalize == 0:
        return re.sub(r"\s*['’`]\s*", "'", text)
    elif normalize > 0:
        return re.sub(r"['’`]", " '", text)
    elif normalize == -1:
        return re.sub(r"['’`]", "' ", text)
    else:
        return re.sub(r"['’`]", "'", text)


# isto kot zgornja funkcija 
def normalize_hyphen(text):
    return re.sub(r"\s{0,2}[-–—‒―−]\s{0,2}", "", text)

# doda v others alternativne moznosti imena (zaobide obklikovalne napake/razlike)
# ce je vec imen, ce je ' znotraj imena; ce je ime bilo prelomljeno
def alternative_names_concat(text):
    others = []
    if not text or len(text) <= 1:
        return others
    #ce je ' v textu
    if re.search(r" ['’`]|['’`] ", text):
    # if " '" in text or "' " in text:
        if "haen" in text:
            print("###")
            print("haen with ' space")
        text = normalize_apostrophe(text, 0)
        tokens = text.split()
        others.extend([t for t in tokens if "'" in t])
    elif re.search(r"['’`]", text):
    # elif "'" in text:
        if "haen" in text:
            print("###")
            print("haen with '")
        tokens = text.split()
        for t in tokens:
            if re.search(r"['’`]", t):
                others.append(normalize_apostrophe(t, -1))
                others.append(normalize_apostrophe(t, 1))
                others.append(normalize_apostrophe(t, -2))

    # ce je ime bilo prelomljeno
    if re.search(f"[-–—‒―−]", text):
        text = normalize_hyphen(text)

    # ce je vec imen
    tokens = [t for t in text.split() if t and t[0].isupper()]
    if tokens and len(tokens) > 1:
        others.extend([t for t in tokens if t and t[0].isupper()])

    if "haen" in text:
        print(f" haen text: {text}")
        print(others)
        print("---")

    return others
