from copy import deepcopy
import json
from pathlib import Path

pth = Path(__file__)
pth = pth.parent / "sample_data"
print(pth)
print(pth.exists())
pth1 = pth / "data_pr_2023-05-15.json"
pth2 = pth / "data_pr_2024-01-05.json"

datas = []
for filepath in (pth1, pth2):
    with open(filepath) as f_in:
        text = f_in.read()
    data = json.loads(text)
    datas.append(data)
    print(f'file {filepath.name}')
    print(f"  type(data['marks'])", type(data['marks']))
    print(f"  type(data['marks'][0])", type(data['marks'][0]))

fake = deepcopy(datas[0])
marks2 = datas[1]['marks']
fake['marks'].extend(marks2)

pth_out = pth2.parent / ("combined_" + str(pth1.name))
print(pth_out)
with open(pth_out, 'w') as file_out:
    json.dump(fake, file_out)




