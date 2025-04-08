""""""
import datetime
from decimal import Decimal


def datetime_filter(value, format='%b %d, %Y'):
    v = int(value) / 1_000.0
    ts = datetime.datetime.fromtimestamp(v)
    return ts.strftime(format)

def url_to_descriptive(url):
    """
    Convert a url to a descriptive string.
    """
    return url.split('/')[-1].replace('-', ' ').replace('_', ' ')

def icon_to_descriptive(icon):
    if 'linkedin' in icon:
        return 'My LinkedIn profile'
    elif 'github' in icon:
        return 'My GitHub profile'
    else:
        return 'My social media profile'

def test_filter():
    print(datetime_filter(1704330000000))
    # as Decimal...
    print(datetime_filter(Decimal('1704330000000')))
    # as string...
    print(datetime_filter('1704330000000'))
    # as float...
    print(datetime_filter(1704330000000.0))

#test_filter()


def build_url(base, query_params: dict) -> str:
    """
    Utility to build something like:
    base?key1=val1&key2=val2...
    """
    from urllib.parse import urlencode
    return base + "?" + urlencode(query_params)
