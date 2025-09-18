#shranjene moznosti iz .config file-a
config = {}

#dodaj color stroke v config
def config_color():
    colors = [
            (0, 0, 0),        # Black
            (1, 1, 1),        # White
            (0.5, 0.5, 0.5),  # Grey
            (0, 0, 1),        # Blue
            (1, 0, 0),        # Red
            ]
    color_names = ['black', 'white', 'gray', 'blue', 'red']
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
                key, value = line.strip().split('=', 1)
                config[key] = [item.strip().strip('"') for item in value.split(',')]
    config_color()
    if 'SPECIAL_CASE' not in config:
        config['SPECIAL_CASE'] = ['nav. d.']
    if 'ANNOT_TYPE' not in config:
        config['ANNOT_TYPE'] = ['underline']
    if  'BIBLIOGRAPHY_DELIMITER' not in config:
        config['BIBLIOGRAPHY_DELIMITER'] = ['Literatura']
