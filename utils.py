""""""


# TEST PAGINATION:
# curl -X GET https://api.darrenmackenzie.com/articles_list?limit=10&cursor=0&tags=python

import requests
import json
import datetime

url = 'https://www.darrenmackenzie.com/articles_list?limit=10'


cursor = '1704330000001'
#url = f'https://www.darrenmackenzie.com/articles_list?limit=10&cursor={cursor}'

tags = 'aws'
#url = f'https://www.darrenmackenzie.com/articles_list?limit=10&cursor={cursor}&tags={tags}'

response = requests.get(url)

result = response.json()

print("LENGTH:", len(result))

for i in result:
    #print(type(i), i)
    print(i['created'], i['title'], i['slug'], i['tags'])
    created = i['created']
    # 1672790400000
    # convert to human readable...
    print(datetime.datetime.fromtimestamp(int(created) / 1000.0))

    print('---')

