""""""
from decimal import Decimal

import boto3

from chalicelib.paginator import Paginator
from chalicelib.utils import build_url

DEFAULT_PAGE_LIMIT = 30


def get_menu_items():
    """Return a list of menu items for the website."""
    return [
        dict(title='Home', url='/'),
        dict(title='About', url='#about'),
        dict(title='Blog', url='#blogarticles'),
        # dict(title='Contact', url='#contact')
    ]


def get_s3_template(s3_env, bucket_name, template_name: str = 'frontend/index.html'):
    """Retrieve and process the HTML template from S3."""
    s3 = boto3.resource('s3')
    myString = s3.Object(bucket_name, template_name).get()["Body"].read().decode('utf-8').replace('__THREEJS_VERSION__', '0.172.0')
    return s3_env.from_string(myString)


def get_website_data(table_name):
    """Retrieve website data from DynamoDB."""
    db = boto3.resource('dynamodb')
    table = db.Table(table_name)
    return table.get_item(Key={'section': 'website_data'})['Item']


def build_paginator_from_query_params(query_params, default_page_limit=DEFAULT_PAGE_LIMIT):
    """Build a paginator from query parameters."""
    paginator = Paginator.from_query_params(query_params)
    paginator.page_size = int(query_params.get('limit', default_page_limit))
    return paginator


def query_articles(table_name, paginator, tags=None):
    """Query articles from DynamoDB with pagination."""
    db = boto3.resource('dynamodb')
    article_list_table = db.Table(table_name)
    kwargs = paginator.build_query_kwargs(tags=tags)

    response = article_list_table.query(**kwargs)
    page_of_articles = response["Items"]

    paginator.update_bounds_from_items(page_of_articles)

    return page_of_articles


def build_pagination_urls(paginator, page_of_articles, base_url, tags_param=None):
    """Build URLs for next and previous pages."""
    next_page_url = None
    prev_page_url = None

    # Decide if there's a "next page"
    if len(page_of_articles) == paginator.page_size:
        # There's a next page
        next_p = paginator.next_page()
        next_query_params = next_p.to_query_params()
        # If we have tags, we can add them back
        if tags_param:
            next_query_params["tags"] = tags_param
        # Construct next page URL
        next_page_url = build_url(base_url, next_query_params)

    # Decide if there's a "previous page"
    if paginator.current_page > 1 and page_of_articles:
        prev_p = paginator.prev_page()
        prev_query_params = prev_p.to_query_params()
        if tags_param:
            prev_query_params["tags"] = tags_param
        prev_page_url = build_url(base_url, prev_query_params)

    return next_page_url, prev_page_url


def determine_page_status(page_of_articles, query_params):
    """Determine if this is the first page and get the newest timestamp."""
    if page_of_articles:
        maxCreated = max([article['created'] for article in page_of_articles])
    else:
        maxCreated = 0

    if not query_params:
        # this is page 1...
        first_page = True
        newest_timestamp = maxCreated
    else:
        first_page = False
        newest_timestamp = query_params.get('newestTimestamp', maxCreated)

    vals = [(str(article['created']), str(Decimal(newest_timestamp))) for article in page_of_articles]
    print('vals:', vals)
    does_current_page_include_newest_timestamp = any([v[0] == v[1] for v in vals])

    return first_page or does_current_page_include_newest_timestamp, newest_timestamp
