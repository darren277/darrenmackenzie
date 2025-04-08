""""""


# TEST PAGINATION:
# curl -X GET https://api.darrenmackenzie.com/articles_list?limit=10&cursor=0&tags=python

import requests
import json
import datetime
import time


url = 'https://www.darrenmackenzie.com'
url2 = "https://www.darrenmackenzie.com/?page=2&limit=9&lb=0&ub=1704589199999&newestTimestamp=1704937800000"

def cache_check(url):
    start_time = time.time()
    response = requests.get(url)
    response_headers = response.headers
    x_cache = response_headers.get('x-cache')
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
    print(f"x-cache: {x_cache}")
    print(f"Response Headers: {response_headers}")
    return x_cache

result = cache_check(url)
print(result)

result = cache_check(url2)
print(result)

quit(34)


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

