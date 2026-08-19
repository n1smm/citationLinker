import  json
from    pathlib import Path


#shranjene moznosti iz .config file-a
config = {}

#dodaj color stroke v config
def config_color():
    colors = [
            (0, 0, 0),        # Black
            (1, 1, 1),        # White
            (0.5, 0.5, 0.5),  # Grey
            (0.7, 0.85, 1),        # Blue
            (1, 0, 0),        # Red
            (0, 0, 1),        # dark_blue
            ]
    color_names = ['black', 'white', 'gray', 'blue', 'red', 'dark_blue']
    if 'COLOR' not in config or not config['COLOR']:
        config['COLOR'] = ['black']
    color = config['COLOR'][0].lower()
    if color in color_names:
        idx = color_names.index(color)
        config['STROKE'] = colors[idx]
    else:
        config['STROKE'] = colors[3]
    
#load moznosti iz .config file-a v config strukturo
def config_load(config_path):
    with config_path.open("r", encoding='utf-8') as file:
        for line in file:
            if '=' in line and not line.strip().startswith('#'):
                if "ARTICLE_BREAKS" in line:
                    key, value = line.strip().split('=', 1)
                    tuples = []
                    items = value.split(',')
                    for item in items:
                        item = item.strip().replace('"', '')
                        offset = 0
                        if "OFFSET" in config and config["OFFSET"] and config["OFFSET"][0]:
                            try:
                                if "+" in config["OFFSET"][0]:
                                    offset = int(config["OFFSET"][0][1:])
                                elif "-" in config["OFFSET"][0]:
                                    offset = int(config["OFFSET"][0])
                            except (ValueError, TypeError):
                                print(f"Warning: Invalid OFFSET value '{config['OFFSET'][0]}' — using 0")
                        # Validate ARTICLE_BREAKS entry format (N:N)
                        parts = item.split(':')
                        if len(parts) != 2:
                            print(f"Warning: Skipping malformed ARTICLE_BREAKS entry '{item}' — expected 'start:end'")
                            continue
                        try:
                            numbers = tuple(int(x) - 1 + offset for x in parts)
                        except (ValueError, TypeError):
                            print(f"Warning: Skipping non-numeric ARTICLE_BREAKS entry '{item}'")
                            continue
                        tuples.append(numbers)
                    config[key] = {i: t for i, t in enumerate(tuples)}
                elif "BIB_STRUCTURE" in line:
                    key, value = line.strip().split('=', 1)
                    try:
                        config[key] = json.loads(value.strip())
                    except json.JSONDecodeError:
                        config[key] = []
                else:
                    key, value = line.strip().split('=', 1)
                    config[key] = [item.strip().strip('"') for item in value.split(',') if item.strip().strip('"')]
    config_color()
    if 'SPECIAL_CASE' not in config or not config['SPECIAL_CASE']:
        config['SPECIAL_CASE'] = []
    if 'SEARCH_EXCLUDE' not in config or not config['SEARCH_EXCLUDE']:
        config['SEARCH_EXCLUDE'] = []
    if 'ANNOT_TYPE' not in config or not config['ANNOT_TYPE']:
        config['ANNOT_TYPE'] = ['underline']
    if  'BIBLIOGRAPHY_DELIMITER' not in config or not config['BIBLIOGRAPHY_DELIMITER']:
        config['BIBLIOGRAPHY_DELIMITER'] = ['Literatura']
    if  'SOFT_YEAR' not in config or not config['SOFT_YEAR']:
        config['SOFT_YEAR'] = ['False']
    if 'DEEP_SEARCH' not in config or not config['DEEP_SEARCH']:
        config['DEEP_SEARCH'] = ['False']
    if  'DEBUG' not in config or not config['DEBUG']:
        config['DEBUG'] = ['False']
    if  'ALTERNATIVE_BIB' not in config or not config['ALTERNATIVE_BIB']:
        config['ALTERNATIVE_BIB'] = ['False']
    if 'LEGACY' not in config or not config['LEGACY']:
        config['LEGACY'] = ['False']
    if config.get("UI", ["False"])[0] == "True":
        from    citation_linker.appLogger import get_logger
        logger = get_logger()
        logger.debug(f"Configuration loaded: {config}")
