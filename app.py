import datetime
from decimal import Decimal
from typing import List
from chalice import Chalice, Response
import brotli
import base64
import hashlib
import json
from os import path
import boto3 as boto3
from jinja2 import Environment, FileSystemLoader, BaseLoader
import stripe

from chalicelib.paginator import Paginator


# Cache for 24 hours
CACHE_CONTROL_ONE_DAY = 'public, s-maxage=86400, max-age=86400'

# Cache for 1 week
CACHE_CONTROL_ONE_WEEK = 'public, s-maxage=604800, max-age=604800'

# Cache for 1 hour
CACHE_CONTROL_ONE_HOUR = 'public, s-maxage=3600, max-age=3600'

# Cache for 1 minute
CACHE_CONTROL_ONE_MINUTE = 'public, s-maxage=60, max-age=60'


print('paginator', Paginator)

def brotli_compress(data):
    return brotli.compress(data)

def create_response_headers(content_type: str, content: str):
    try:
        etag_value = hashlib.md5(content).hexdigest()
    except TypeError:
        etag_value = hashlib.md5(content.encode('utf-8')).hexdigest()

    last_modified = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')

    if content_type == 'text/html' or content_type == 'text/html; charset=UTF-8':
        #cache_control = CACHE_CONTROL_ONE_DAY
        cache_control = CACHE_CONTROL_ONE_MINUTE
    elif content_type == 'application/json':
        #cache_control = CACHE_CONTROL_ONE_HOUR
        cache_control = CACHE_CONTROL_ONE_MINUTE
    elif content_type in ['text/css', 'application/javascript']:
        cache_control = CACHE_CONTROL_ONE_WEEK
    else:
        #cache_control = CACHE_CONTROL_ONE_DAY
        cache_control = CACHE_CONTROL_ONE_MINUTE
    
    return {
        'Content-Type': content_type,
        'Content-Encoding': 'br',
        'Cache-Control': cache_control,
        'ETag': etag_value,
        'Last-Modified': last_modified
    }


app = Chalice(app_name="darrenmackenzie")

app.api.binary_types.extend([
    'application/javascript',
    'application/json',
    'text/css',
    'text/html',
    'application/xml'
])

# import from AWS Secrets Manager
import os
import json

def get_secret(secret_name: str):
    region_name = "us-east-1"

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    get_secret_value_response = client.get_secret_value(
        SecretId=secret_name
    )
    secret = get_secret_value_response['SecretString']
    return json.loads(secret)

stripe.api_key = os.environ.get('STRIPE_RESTRICTED_KEY', get_secret('STRIPE_RESTRICTED_KEY')['STRIPE_RESTRICTED_KEY'])
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', get_secret('STRIPE_WEBHOOK_SECRET')['STRIPE_WEBHOOK_SECRET'])

#DEFAULT_PAGE_LIMIT = 10
#DEFAULT_PAGE_LIMIT = 3
#DEFAULT_PAGE_LIMIT = 9
DEFAULT_PAGE_LIMIT = 30

import os
cwd = os.path.dirname(__file__)
from os.path import join

env = Environment(loader=FileSystemLoader(join(cwd, 'chalicelib', 'frontend'), encoding='utf8'))

s3_env = Environment(loader=BaseLoader())


def datetime_filter(value, format='%b %d, %Y'):
    v = int(value) / 1_000.0
    ts = datetime.datetime.fromtimestamp(v)
    return ts.strftime(format)


env.filters['datetime'] = datetime_filter
s3_env.filters['datetime'] = datetime_filter


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

"""
    MAIN ENDPOINT
"""

def get_menu_items():
    """Return a list of menu items for the website."""
    return [
        dict(title='Home', url='/'),
        dict(title='About', url='#about'),
        dict(title='Blog', url='#blogarticles'),
        # dict(title='Contact', url='#contact')
    ]

def get_s3_template(bucket_name, template_name: str = 'frontend/index.html'):
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

def create_compressed_response(html_content):
    """Create a compressed HTTP response."""
    compressed_html = brotli_compress(html_content.encode('utf-8'))
    
    return Response(
        body=compressed_html,
        headers=create_response_headers('text/html; charset=UTF-8', html_content),
        status_code=200
    )

@app.route('/')
def script_template():
    """Handle the main website endpoint."""
    try:
        # Get menu items and parse query parameters
        menu = get_menu_items()
        query_params = app.current_request.query_params or {}
        tags_param = query_params.get('tags')
        tags = tags_param.split(',') if tags_param else None
        
        # Build paginator
        try:
            paginator = build_paginator_from_query_params(query_params)
        except Exception as e:
            print("Error building paginator:", e)
            return Response(str(e), status_code=400)
        
        # Get template from S3 and website data from DynamoDB
        template = get_s3_template(os.environ['BUCKET_NAME'])
        website_data = get_website_data(os.environ['HOME_TABLE'])
        
        # Query articles
        try:
            page_of_articles = query_articles(os.environ['ARTICLE_LIST_TABLE'], paginator, tags)
        except Exception as e:
            print("Error querying DynamoDB:", e)
            return Response(str(e), status_code=500)
        
        # Build pagination URLs
        try:
            next_page_url, prev_page_url = build_pagination_urls(
                paginator, page_of_articles, "https://www.darrenmackenzie.com/", tags_param
            )
        except Exception as e:
            print("Error building pagination URLs:", e)
            return Response(str(e), status_code=500)
        
        # Determine page status
        try:
            is_first_page, newest_timestamp = determine_page_status(page_of_articles, query_params)
        except Exception as e:
            print("Error getting newest timestamp:", e)
            return Response(str(e), status_code=500)
        
        # Render template
        template_data = {
            'social': website_data['social'],
            'articles': page_of_articles,
            'menu': menu,
            'nextPageUrl': next_page_url,
            'prevPageUrl': prev_page_url,
            'firstPage': is_first_page,
            'newestTimestamp': newest_timestamp,
        }
        html_content = template.render(**template_data)
        
        # Create and return response
        return create_compressed_response(html_content)
    
    except Exception as e:
        print(f"Unexpected error in script_template: {e}")
        return Response(str(e), status_code=500)


@app.route('/index.html')
def index():
    # redirect to `/`
    return Response(body='', headers={'Location': 'https://www.darrenmackenzie.com'}, status_code=301)


"""
    ARTICLES LIST
"""
def get_articles_list(limit: int, cursor: int, tags: List[str], newer_than=None, older_than=None):
    ## Backward pagination (like “previous page”) is inherently awkward in DynamoDB. Often you do an additional query with reversed ordering or you simply remember the entire “previous” set of items in the client.
    db = boto3.resource('dynamodb')
    article_table = db.Table(os.environ['ARTICLE_LIST_TABLE'])

    if newer_than:
        if tags:
            response = article_table.query(KeyConditionExpression='type_of_article = :type_of_article AND created > :val', FilterExpression='contains(tags, :tag)', ExpressionAttributeValues={':type_of_article': 'blog', ':tag': tags[0], ':val': Decimal(newer_than)}, Limit=limit, ScanIndexForward=False)
        else:
            response = article_table.query(KeyConditionExpression='type_of_article = :type_of_article AND created > :val', ExpressionAttributeValues={':type_of_article': 'blog', ':val': Decimal(newer_than)}, Limit=limit, ScanIndexForward=False)
    elif older_than:
        if tags:
            response = article_table.query(KeyConditionExpression='type_of_article = :type_of_article AND created < :val', FilterExpression='contains(tags, :tag)', ExpressionAttributeValues={':type_of_article': 'blog', ':tag': tags[0], ':val': Decimal(older_than)}, Limit=limit, ScanIndexForward=False)
        else:
            response = article_table.query(KeyConditionExpression='type_of_article = :type_of_article AND created < :val', ExpressionAttributeValues={':type_of_article': 'blog', ':val': Decimal(older_than)}, Limit=limit, ScanIndexForward=False)
    else:
        if tags:
            tags = tags.split(',')
            # Only handles one tag for now...
            response = article_table.query(KeyConditionExpression='type_of_article = :type_of_article AND created < :date', FilterExpression='contains(tags, :tag)', ExpressionAttributeValues={':type_of_article': 'blog', ':tag': tags[0], ':date': Decimal(cursor)}, Limit=limit, ScanIndexForward=False)
        else:
            response = article_table.query(KeyConditionExpression='type_of_article = :type_of_article AND created < :date', ExpressionAttributeValues={':type_of_article': 'blog', ':date': Decimal(cursor)}, Limit=limit, ScanIndexForward=False)
    #return sorted(response['Items'], key=lambda x: x['created'])
    return response['Items']


# paginated article fetching...
@app.route('/articles_list', methods=['GET'])
def articles_list():
    limit = int(app.current_request.query_params.get('limit', 10))
    cursor = int(app.current_request.query_params.get('cursor', datetime.datetime.now().timestamp() * 1_000))
    tags = app.current_request.query_params.get('tags', None)

    response_data = get_articles_list(limit, cursor, tags)
    json_data = json.dumps(response_data)
    compressed_json = brotli.compress(json_data.encode('utf-8'))

    return Response(
        body=compressed_json,
        headers=create_response_headers('application/json', compressed_json),
        status_code=200
    )


"""
    JAVASCRIPT, JSON, AND CSS ENDPOINTS
"""
# Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource at https://darrenmackenzie-chalice-bucket.s3.us-east-1.amazonaws.com/scripts/main.js. (Reason: CORS header ‘Access-Control-Allow-Origin’ missing). Status code: 200.
@app.route('/scripts/main.js')
def serve_js():
    s3 = boto3.resource('s3')
    js_content = s3.Object(os.environ['BUCKET_NAME'], 'scripts/main.js').get()["Body"].read().decode('utf-8')

    compressed_js = brotli_compress(js_content.encode('utf-8'))
    
    return Response(
        body=compressed_js,
        headers=create_response_headers('application/javascript', compressed_js),
        status_code=200
    )

@app.route('/scripts/helvetiker_regular.typeface.json')
def serve_font():
    s3 = boto3.resource('s3')
    json_content = s3.Object(os.environ['BUCKET_NAME'], 'scripts/helvetiker_regular.typeface.json').get()["Body"].read().decode('utf-8')

    compressed_json = brotli_compress(json_content.encode('utf-8'))

    return Response(
        body=compressed_json,
        headers=create_response_headers('application/json', compressed_json),
        status_code=200
    )

@app.route('/data/data.json')
def serve_data():
    s3 = boto3.resource('s3')
    json_content = s3.Object(os.environ['BUCKET_NAME'], 'data/data.json').get()["Body"].read().decode('utf-8')

    compressed_json = brotli_compress(json_content.encode('utf-8'))

    return Response(
        body=compressed_json,
        headers=create_response_headers('application/json', compressed_json),
        status_code=200
    )

@app.route('/style.css')
def serve_css():
    s3 = boto3.resource('s3')
    css_content = s3.Object(os.environ['BUCKET_NAME'], 'frontend/style.css').get()["Body"].read().decode('utf-8')

    compressed_css = brotli_compress(css_content.encode('utf-8'))

    return Response(
        body=compressed_css,
        headers=create_response_headers('text/css', compressed_css),
        status_code=200
    )


"""
    CONTACT FORM
"""
@app.route('/contact', methods=['POST'], content_types=['application/x-www-form-urlencoded'])
def contact_form():
    import uuid
    import time
    from urllib.parse import parse_qs
    db = boto3.resource('dynamodb')
    table = db.Table(os.environ['CONTACT_TABLE'])
    data = parse_qs(app.current_request.raw_body.decode('utf-8'))
    timestamp = int(time.time() * 1000)
    item = {'id': str(uuid.uuid1()), 'email': data['email'], 'message': data['message'], 'createdAt': timestamp, 'updatedAt': timestamp}
    res = table.put_item(Item=item)
    print(res)
    return Response(body='', headers={'Location': 'https://www.darrenmackenzie.com'}, status_code=301)


"""
    INDIVIDUAL PAGES
"""
@app.route('/{section}/{article}')
def articles(section, article):
    s3 = boto3.resource('s3')
    website_menu = [
        dict(title='Home', url='#'),
        dict(title='About', url='#about'),
        dict(title='Blog', url='#blogarticles'),
        # dict(title='Contact', url='#contact')
    ]
    non_index_menu = [dict(title=item['title'], url=f"/index.html{item['url']}") for item in website_menu]
    if section not in ['services', 'work', 'blog']:
        html_content = s3_env.from_string(s3.Object(os.environ['BUCKET_NAME'], 'frontend/404.html').get()["Body"].read().decode('utf-8')).render(menu=non_index_menu)

        compressed_html = brotli_compress(html_content.encode('utf-8'))

        return Response(
            body=compressed_html,
            headers=create_response_headers('text/html; charset=UTF-8', compressed_html),
            status_code=404
        )
    
    db = boto3.resource('dynamodb')
    article_table = db.Table(os.environ['ARTICLE_TABLE'])
    article = article_table.get_item(Key={'type_of_article': section, "slug": article}).get('Item')

    if article:
        html_content = s3_env.from_string(s3.Object(os.environ['BUCKET_NAME'], 'frontend/article.html').get()["Body"].read().decode('utf-8')).render(section=section, article=article, menu=non_index_menu)

        compressed_html = brotli_compress(html_content.encode('utf-8'))

        return Response(
            body=compressed_html,
            headers=create_response_headers('text/html; charset=UTF-8', compressed_html),
            status_code=200
        )
    else:
        html_content = s3_env.from_string(s3.Object(os.environ['BUCKET_NAME'], 'frontend/404.html').get()["Body"].read().decode('utf-8')).render(menu=non_index_menu)

        compressed_html = brotli_compress(html_content.encode('utf-8'))

        return Response(
            body=compressed_html,
            headers=create_response_headers('text/html; charset=UTF-8', compressed_html),
            status_code=404
        )


"""
    STRIPE CHECKOUT
"""
@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """
    Creates a Stripe Checkout Session and returns the session ID
    """
    # You might parse the request body if you need dynamic prices.
    # For example, if you have multiple products or amounts:
    # data = app.current_request.json_body
    # price_id = data['price_id']

    # For demonstration, let’s just create a session with a fixed price:
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        mode='payment',
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'unit_amount': 1000,  # $10.00
                'product_data': {
                    'name': 'Sample Product'
                },
            },
            'quantity': 1,
        }],
        success_url='https://www.darrenmackenzie.com/success',  # Where to redirect on success
        cancel_url='https://www.darrenmackenzie.com/cancel'     # Where to redirect on cancel
    )

    return {'sessionId': session.id}

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    import stripe
    import json
    from chalice import BadRequestError

    payload = app.current_request.raw_body
    sig_header = app.current_request.headers.get('Stripe-Signature', '')
    endpoint_secret = STRIPE_WEBHOOK_SECRET

    # Verify the signature
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        # Invalid payload
        raise BadRequestError("Invalid payload")
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        raise BadRequestError("Invalid signature")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # For example, retrieve the session details or line items
        # Do something with successful payment
        print("Payment successful for session: ", session['id'])

    # Return a 200 response to acknowledge receipt of the event
    return {}


ANIMATIONS_DICT = {
    'my_animation': {
        'title': 'My Animation',
        'animation_type': 'default',
        'path': 'M 50,250 C 150,-100 450,400 550,50',
        'steps': [
            {'_id': 'text0', 'text': 'Start here.'},
            {'_id': 'text1', 'text': 'Stop off here.'},
            {'_id': 'text2', 'text': 'Visit here.'},
            {'_id': 'text3', 'text': "You've reached your destination!"}
        ]
    },
    'special_path': {
        'title': 'Special Path',
        'animation_type': 'anchor_points',
        'path': """
        M 104.00,192.00
           C 104.00,192.00 1424.00,220.00 1424.00,220.00
             1424.00,220.00 1356.00,880.00 1356.00,880.00
             1356.00,880.00 2300.00,196.00 2300.00,196.00
             2300.00,196.00 2296.00,796.00 2296.00,796.00
             2296.00,796.00 2996.00,276.00 2996.00,276.00
             2996.00,276.00 3748.00,1052.00 3748.00,1052.00
             3748.00,1052.00 4204.00,244.00 4204.00,244.00
             4204.00,244.00 4248.00,1560.00 4248.00,1560.00
             4248.00,1560.00 140.00,980.00 140.00,980.00
             140.00,980.00 200.00,1576.00 200.00,1576.00
             200.00,1576.00 1276.00,1440.00 1276.00,1440.00
             1276.00,1440.00 1392.00,2084.00 1392.00,2084.00
""",
        'steps': [
            {'_id': 'text0', 'text': 'A'},
            {'_id': 'text1', 'text': 'B'},
            {'_id': 'text2', 'text': 'C'},
            {'_id': 'text3', 'text': 'D'},
            {'_id': 'text4', 'text': 'E'},
            {'_id': 'text5', 'text': 'F'},
            {'_id': 'text6', 'text': 'G'},
            {'_id': 'text7', 'text': 'H'},
            {'_id': 'text8', 'text': 'I'},
            {'_id': 'text9', 'text': 'J'},
            {'_id': 'text10', 'text': 'K'},
            {'_id': 'text11', 'text': 'L'},
            {'_id': 'text12', 'text': 'M'},
            {'_id': 'text13', 'text': 'N'}
        ]
    }
}

@app.route('/load_img', methods=['GET'])
def load_img():
    img_url = app.current_request.query_params.get('img_url', None)

    if not img_url:
        return Response(body='Image URL required.', status_code=400)
    
    if not img_url.startswith('static/'):
        return Response(body='Image URL must start with `static/`.', status_code=400)
    
    s3 = boto3.resource('s3')

    try:
        presigned_url = s3.meta.client.generate_presigned_url('get_object', Params={'Bucket': os.environ['BUCKET_NAME'], 'Key': img_url}, ExpiresIn=3600)
    except Exception as e:
        return Response(body=str(e), status_code=404)
    
    return Response(
        body=json.dumps({'signedUrl': presigned_url}),
        headers={'Content-Type': 'application/json'},
        status_code=200
    )


@app.route('/animation', methods=['GET'])
def animation():
    animation_name = app.current_request.query_params.get('animation_name', None)
    background_image_url = app.current_request.query_params.get('background_image_url', None)

    if not animation_name:
        return Response(body='Path (`animation_name`) required.', status_code=400)
    
    animation_data = ANIMATIONS_DICT.get(animation_name, None)

    path = animation_data.get('path', None) if animation_data else None

    if not path:
        return Response(body=f'Animation name (`{animation_name}`) not found.', status_code=404)
    
    steps = animation_data.get('steps', None)

    template = get_s3_template(os.environ['BUCKET_NAME'], template_name='frontend/animation.html')

    template_data = {
        'workflow_path': path,
        'steps': steps,
        'title': animation_data.get('title', 'Animation'),
        'animation_type': animation_data.get('animation_type', 'default')
    }

    if background_image_url:
        template_data.update({'background_image_url': background_image_url})

        image_top_padding = app.current_request.query_params.get('top_padding', None)
        image_bottom_padding = app.current_request.query_params.get('bottom_padding', None)

        if image_top_padding:
            template_data.update({'top_padding': image_top_padding})
        
        if image_bottom_padding:
            template_data.update({'bottom_padding': image_bottom_padding})

    html_content = template.render(**template_data)
    
    return create_compressed_response(html_content)


@app.route('/sitemap.xml')
def sitemap():
    s3 = boto3.resource('s3')
    myString = s3.Object(os.environ['BUCKET_NAME'], 'sitemap.xml').get()["Body"].read().decode('utf-8')
    return Response(myString, headers={'Content-Type': 'application/xml'}, status_code=200)

'''
sitemap.xml:
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <sitemap>
        <loc>https://www.darrenmackenzie.com/blog/lambda-layers</loc>
        <lastmod>2024-01-02T00:00:00+00:00</lastmod>
    </sitemap>
</sitemapindex>
'''