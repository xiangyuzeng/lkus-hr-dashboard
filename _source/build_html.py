import json
import re

with open('/home/claude/dashboard/data.json','r',encoding='utf-8') as f:
    data_json = f.read()

with open('/home/claude/dashboard/template.html','r',encoding='utf-8') as f:
    template = f.read()

html = template.replace('/*__DATA_PLACEHOLDER__*/', f'const DATA = {data_json};')

with open('/home/claude/dashboard/index.html','w',encoding='utf-8') as f:
    f.write(html)
print('Built', len(html), 'bytes')
