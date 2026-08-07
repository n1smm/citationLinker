import  re
from    enum            import Enum 
from    enum            import Enum 

# tipi
class Bib_types(Enum):
    SURNAME = 0
    NAME = 1
    TITLE = 2
    YEAR = 3
    SEPARATOR = 4
    EXTRA_CHAR = 5
    IGNORE = 6
    OTHER_AUTHORS = 7

# globalni regexi
year_search_pattern = re.compile(r'\d{4}[a-zA-Z]?')
year_span_pattern = re.compile(r'\d{4} {0,2}[-–—]{1,2} {0,2}\d{4}')

# validatorji
# za preverjanje imena,priimka,naslova, all - ali morajo vse besede imeti veliko zacetnico ali samo prva)
# malo prostora za cca 20% besed niso kapitalizirane
def is_capitalized(text, all=False):
    text = text.strip()
    if not text or not text[0] or not text[0].isupper():
        return False

    if not all:
        return text[0].isupper()

    tokens = text.split()
    upper_count = 0
    for tok in tokens:
        if tok.strip()[0].isupper():
            upper_count += 1
    if upper_count / len(tokens) >= 0.8:
        return True
    return False

# iskanje leta ali razpona npr 1028a ali 1999-2002
def is_year_or_span(text):
    text = text.strip()
    if bool(year_span_pattern.search(text)):
        return "YEAR_SPAN"
    elif bool(year_search_pattern.search(text)):
        return "YEAR"
    return "IGNORE"

# preveri ce se text ujema z moznimi separatorji ali extra karakterji/ separatorji
def is_separator_or_char(text, char_list=[","]):
    text = text.strip()
    for char in char_list:
        if text == char:
            return True
    return False

# poisci separator ali extra_char
def find_separator_char(text, char_list=[","]):
    text = text.strip()
    idx = -1

    for char in char_list:
        idx = text.find(char)
        if idx != -1:
            return idx

    return idx


def is_word_boundary(text, start, end):
    """True when the match at text[start:end] is surrounded by non-word characters."""
    before_ok = start == 0 or not (text[start - 1].isalnum() or text[start - 1] == '_')
    after_ok  = end >= len(text) or not (text[end].isalnum() or text[end] == '_')
    return before_ok and after_ok


def normalize_structure_type(raw_type):
    if not isinstance(raw_type, str):
        return ""
    normalized = raw_type.strip().replace("-", "_").replace(" ", "_").upper()
    aliases = {
        "SURNAME": "SURNAME",
        "NAME": "NAME",
        "TITLE": "TITLE",
        "YEAR": "YEAR",
        "SEPARATOR": "SEPARATOR",
        "EXTRA_CHAR": "EXTRA_CHAR",
        "EXTRACHAR": "EXTRA_CHAR",
        "OTHER_AUTHORS": "OTHER_AUTHORS",
        "OTHERS": "OTHER_AUTHORS",
        "IGNORE": "IGNORE",
    }
    return aliases.get(normalized, normalized)


def normalize_options(raw_options):
    if isinstance(raw_options, list):
        # opt.strip() or opt: navadne opcije obrezemo (" , " -> ","), a opcijo
        # iz samih presledkov ohranimo (" " ostane " "), da deluje presledek kot separator.
        return [opt.strip() or opt for opt in raw_options if isinstance(opt, str) and opt]
    if isinstance(raw_options, str):
        if "|" in raw_options:
            return [opt.strip() for opt in raw_options.split("|") if opt.strip()]
        return [opt.strip() for opt in raw_options.split(",") if opt.strip()]
    return []


def parse_bool(raw_value, default=False):
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        value = raw_value.strip().lower()
        if value in ("true", "1", "yes"):
            return True
        if value in ("false", "0", "no"):
            return False
    return default

def dedupe_keep_order(values):
    seen = set()
    out = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out
