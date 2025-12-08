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
    color = config['COLOR'][0].lower()
    if color in color_names:
        idx = color_names.index(color)
        config['STROKE'] = colors[idx]
    else:
        config['STROKE'] = colors[3]
    
#load moznosti iz .config file-a v config strukturo
def config_load():
    with open('./.config') as file:
        for line in file:
            if '=' in line and not line.strip().startswith('#'):
                if "ARTICLE_BREAKS" in line:
                    key, value = line.strip().split('=', 1)
                    tuples = []
                    items = value.split(',')
                    for item in items:
                        item = item.strip().replace('"', '')
                        if config["OFFSET"][0] and "+" in config["OFFSET"][0]:
                            offset = int(config["OFFSET"][0][1:])
                        elif config["OFFSET"][0] and "-" in config["OFFSET"][0]:
                            offset = int(config["OFFSET"][0])
                        else:
                            offset = 0
                        numbers = tuple(map(lambda x: int(x) -1 + offset, item.split(':')))
                        tuples.append(numbers)
                    config[key] = {i: t for i, t in enumerate(tuples)}
                else:
                    key, value = line.strip().split('=', 1)
                    config[key] = [item.strip().strip('"') for item in value.split(',')]
    config_color()
    if 'SPECIAL_CASE' not in config:
        config['SPECIAL_CASE'] = ['nav. d.']
    if 'ANNOT_TYPE' not in config:
        config['ANNOT_TYPE'] = ['underline']
    if  'BIBLIOGRAPHY_DELIMITER' not in config:
        config['BIBLIOGRAPHY_DELIMITER'] = ['Literatura']
    if  'SOFT_YEAR' not in config:
        config['SOFT_YEAR'] = ['False']
    print("config: ")
    print(config)
