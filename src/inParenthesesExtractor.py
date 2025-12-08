import re
from configLoad import config


#spremeni tokne nazaj v originalni text, samo del ki potrebuje (znotraj ali tudi zunaj oklepajev)
def unite_tokens_to_text(inbound_text, only_parenthesis, start_idx):

    delimiter =  chr(40) #oklepaj
    if only_parenthesis:
        start = inbound_text.find(delimiter)
        end = inbound_text.find(")", start) + 1
        if end == 0:
            end = len(inbound_text)
    else:
        start = start_idx
        end = inbound_text.find(")", start) + 1
    in_string = inbound_text[start:end] if end > start else ''
    # if "Strich" in inbound_text and "išin" in inbound_text:
    #     print("in string text: ", in_string)
    #     print("inbound text", inbound_text)
    return (in_string)



# preveri ce obstaja moznost da bi bila vsebina oklepaja ali pred oklepajem lahko referenca in jo shrani v zacasni slovar (hashmatrico) temp_refs
def reference_checker(inbound_text, temp_refs):
    delimiter =  chr(40) #oklepaj
    parentheses_break = inbound_text.split(delimiter)
    before_tokens = parentheses_break[0].split() if parentheses_break[0] else None
    in_tokens = parentheses_break[1].split() if len(parentheses_break) > 1 and parentheses_break[1] else None

    #ali se navezuje na prejsnjo referenco
    if len(parentheses_break) > 1 and parentheses_break[1] and any(case in parentheses_break[1] for case in config['SPECIAL_CASE']):
        ref_text = unite_tokens_to_text(inbound_text, True, 0)
        temp_refs.append({"text": ref_text, "outside_name": False, "check_prev": True})
        return True

    # regex iskanje kakrsnekoli 4mestne stevilke z mozno crko na koncu kjerkoli v oklepaju
    year_search_pattern = re.compile(r'\b\d{4}[a-zA-Z]?\b')
    name_inside = False
    if not in_tokens:
        return False
    if not any(year_search_pattern.search(token.strip('.,;:')) for token in in_tokens):
        return False
    #glej za besede z veliko zacetnico v oklepaju
    if any(token[0].isupper() for token in in_tokens):
        name_inside = True
        ref_text = unite_tokens_to_text(inbound_text, True, 0)
        temp_refs.append({"text": ref_text, "outside_name": False, "check_prev": False})
        return True

    #ce ni besed z veliko zacetnico v oklepajih, poglej zunaj oklepajev
    if not name_inside:
        if before_tokens:
            if not any(token[0].isupper() for token in before_tokens):
                return False
            for i, token in enumerate(before_tokens):
                if token[0].isupper():
                    before_tokens = before_tokens[i:]
                    break
            initial_idx = inbound_text.find(before_tokens[0])
            ref_text = unite_tokens_to_text(inbound_text, False, initial_idx)
            temp_refs.append({"text": ref_text, "outside_name": True, "check_prev": False})
            return True
        else:
            return False
    return False

        
# pregleda vse oklepaje na trenutni strani, vrne nazaj slovar vseh referenc {text: string, outside_name: bool, check_prev: bool} in ce je ime zunaj ali znotraj oklepaja
def check_in_parentheses(text):
    tokens = text.split()
    start_parenthesis = 0
    end_parenthesis = 0
    temp_refs = []
    for i, token in enumerate(tokens):
        if "(" in token:
            #vazami 4 tokne pred oklepaji za dodatno preverjanje
            start = max(0, i - 4)
            #ce je v teh 4ih notri ( ali ) ga izkljuci
            for k in range(i - 1, start -1, -1):
                if "(" in tokens[k] or ")" in tokens[k]:
                     start = k + 1
                     break
            inbound_tokens = tokens[start:i]
            j = i
            #dodaj se tokne v oklepaju
            while j < len(tokens):
                inbound_tokens.append(tokens[j])
                if ")" in tokens[j]:
                    break
                j += 1
            inbound_text = ' '.join(inbound_tokens)
            reference_checker(inbound_text, temp_refs)
    return temp_refs

