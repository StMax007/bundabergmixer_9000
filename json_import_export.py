import json

# with open('cocktail_data_new.json') as json_file:
#     data = json.load(json_file)

# maximum_anzahl = 2
# for i in data['Drinks']:
#     print(i)

# if 'Orangensaft' in data['Bottles']:
#     del data['Bottles']['Orangensaft']

# for i in range(1, len(data['Drinks']['Caipirinia']) + 1):
#     print(data['Drinks']['Caipirinia']['Bottle'+str(i)])

# data['Bottles']['Orangensaft'] = {'Valve': 1}




# print(data)

# with open('cocktail_data_new.json', 'w', encoding='utf-8') as f:
#     json.dump(data, f, ensure_ascii=False, indent=4)

import collections
with open('cocktail_data.json') as json_file:
    json_data = json.load(json_file)
d = collections.OrderedDict([('a', 1), ('c', 3), ('b', 2)])
d2 = collections.OrderedDict([('__C__', v) if k == 'c' else (k, v) for k, v in d.items()])
print(d2)
