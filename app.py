import datetime
from decimal import Decimal
from typing import List
from chalice import Chalice, Response
import brotli
import base64
import json
from os import path
import boto3 as boto3
from jinja2 import Environment, FileSystemLoader, BaseLoader
import stripe

from chalicelib.paginator import Paginator

print('paginator', Paginator)

def brotli_compress(data):
    return base64.b64encode(brotli.compress(data.encode())).decode()


app = Chalice(app_name="darrenmackenzie")

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
DEFAULT_PAGE_LIMIT = 9

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


@app.route('/')
def script_template():
    menu = [
        dict(title='Home', url='#'),
        dict(title='About', url='#about'),
        dict(title='Services', url='#services'),
        dict(title='Work', url='#work'),
        dict(title='Blog', url='#blogarticles'),
        # dict(title='Contact', url='#contact')
    ]
    s3 = boto3.resource('s3')
    myString = s3.Object(os.environ['BUCKET_NAME'], 'frontend/index.html').get()["Body"].read().decode('utf-8').replace('__THREEJS_VERSION__', '0.172.0')
    template = s3_env.from_string(myString)

    db = boto3.resource('dynamodb')
    table = db.Table(os.environ['HOME_TABLE'])
    ## data = app.current_request.json_body
    website_data = table.get_item(Key={'section': 'website_data'})['Item']

    query_params = app.current_request.query_params or {}
    tags_param = query_params.get('tags')

    # Build paginator from query params
    try:
        paginator = Paginator.from_query_params(query_params)
        paginator.page_size = int(query_params.get('limit', DEFAULT_PAGE_LIMIT))
    except Exception as e:
        print("Error building paginator:", e)
        return Response(str(e), status_code=400)


    # We'll only handle 1 tag for now:
    tags = tags_param.split(',') if tags_param else None

    # Build the query arguments using the paginator
    try:
        article_table_name = os.environ['ARTICLE_LIST_TABLE']
        article_list_table = db.Table(article_table_name)
        kwargs = paginator.build_query_kwargs(tags=tags)
    except Exception as e:
        print("Error building query arguments:", e)
        return Response(str(e), status_code=400)

    # Execute the query
    try:
        response = article_list_table.query(**kwargs)
        page_of_articles = response["Items"]
    except Exception as e:
        print("Error querying DynamoDB:", e)
        return Response(str(e), status_code=500)

    # Update paginator bounds from these items
    try:
        paginator.update_bounds_from_items(page_of_articles)
    except Exception as e:
        print("Error updating paginator bounds:", e)
        return Response(str(e), status_code=500)

    # Decide if there's a "next page"
    # If we got 'Limit' items, assume there's possibly more. 
    # In practice you might check if 'LastEvaluatedKey' is present.
    try:
        if len(page_of_articles) == paginator.page_size:
            # There's a next page
            next_p = paginator.next_page()
            next_query_params = next_p.to_query_params()
            # If we have tags, we can add them back
            if tags_param:
                next_query_params["tags"] = tags_param
            # Construct next page URL
            next_page_url = build_url("https://www.darrenmackenzie.com/", next_query_params)
        else:
            next_page_url = None
    except Exception as e:
        print("Error building next page URL:", e)
        return Response(str(e), status_code=500)

    # Decide if there's a "previous page"
    # We might say if paginator.current_page > 1, we do a previous
    try:
        if paginator.current_page > 1 and page_of_articles:
            try:
                prev_p = paginator.prev_page()
            except Exception as e:
                print("Error getting prev page:", e)
                return Response(str(e), status_code=500)
            prev_query_params = prev_p.to_query_params()
            if tags_param:
                prev_query_params["tags"] = tags_param
            prev_page_url = build_url("https://www.darrenmackenzie.com/", prev_query_params)
        else:
            prev_page_url = None
    except Exception as e:
        print("Error building prev page URL:", e)
        return Response(str(e), status_code=500)
    
    try:
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
    except Exception as e:
        print("Error getting newest timestamp:", e)
        return Response(str(e), status_code=500)
    
    html_content = template.render(
        services=website_data['services'],
        social=website_data['social'],
        projects=website_data['projects'],
        articles=page_of_articles,
        menu=menu,
        nextPageUrl=next_page_url,
        prevPageUrl=prev_page_url,
        firstPage=first_page or does_current_page_include_newest_timestamp,
        newestTimestamp=newest_timestamp,
    )

    compressed_html = brotli_compress(html_content.encode('utf-8'))
    
    return Response(
        body=compressed_html,
        headers={'Content-Type': 'text/html; charset=UTF-8', 'Content-Encoding': 'br'},
        status_code=200
    )

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
        headers={
            'Content-Type': 'application/json',
            'Content-Encoding': 'br'
        },
        status_code=200
    )

# Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource at https://darrenmackenzie-chalice-bucket.s3.us-east-1.amazonaws.com/scripts/main.js. (Reason: CORS header ‘Access-Control-Allow-Origin’ missing). Status code: 200.
@app.route('/scripts/main.js')
def serve_js():
    s3 = boto3.resource('s3')
    js_content = s3.Object(os.environ['BUCKET_NAME'], 'scripts/main.js').get()["Body"].read().decode('utf-8')

    compressed_js = brotli_compress(js_content.encode('utf-8'))
    
    return Response(
        body=compressed_js,
        headers={'Content-Type': 'application/javascript', 'Content-Encoding': 'br'},
        status_code=200
    )

@app.route('/scripts/helvetiker_regular.typeface.json')
def serve_font():
    s3 = boto3.resource('s3')
    json_content = s3.Object(os.environ['BUCKET_NAME'], 'scripts/helvetiker_regular.typeface.json').get()["Body"].read().decode('utf-8')

    compressed_json = brotli_compress(json_content.encode('utf-8'))

    return Response(
        body=compressed_json,
        headers={'Content-Type': 'application/json', 'Content-Encoding': 'br'},
        status_code=200
    )

@app.route('/data/data.json')
def serve_data():
    s3 = boto3.resource('s3')
    json_content = s3.Object(os.environ['BUCKET_NAME'], 'data/data.json').get()["Body"].read().decode('utf-8')

    compressed_json = brotli_compress(json_content.encode('utf-8'))

    return Response(
        body=compressed_json,
        headers={'Content-Type': 'application/json', 'Content-Encoding': 'br'},
        status_code=200
    )

@app.route('/style.css')
def serve_css():
    s3 = boto3.resource('s3')
    css_content = s3.Object(os.environ['BUCKET_NAME'], 'frontend/style.css').get()["Body"].read().decode('utf-8')

    compressed_css = brotli_compress(css_content.encode('utf-8'))

    return Response(
        body=compressed_css,
        headers={'Content-Type': 'text/css', 'Content-Encoding': 'br'},
        status_code=200
    )

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


@app.route('/{section}/{article}')
def articles(section, article):
    s3 = boto3.resource('s3')
    website_menu = [
        dict(title='Home', url='#'),
        dict(title='About', url='#about'),
        dict(title='Services', url='#services'),
        dict(title='Work', url='#work'),
        dict(title='Blog', url='#blogarticles'),
        # dict(title='Contact', url='#contact')
    ]
    non_index_menu = [dict(title=item['title'], url=f"/index.html{item['url']}") for item in website_menu]
    if section not in ['services', 'work', 'blog']:
        html_content = s3_env.from_string(s3.Object(os.environ['BUCKET_NAME'], 'frontend/404.html').get()["Body"].read().decode('utf-8')).render(menu=non_index_menu)

        compressed_html = brotli_compress(html_content.encode('utf-8'))

        return Response(
            body=compressed_html,
            headers={'Content-Type': 'text/html; charset=UTF-8', 'Content-Encoding': 'br'},
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
            headers={'Content-Type': 'text/html; charset=UTF-8', 'Content-Encoding': 'br'},
            status_code=200
        )
    else:
        html_content = s3_env.from_string(s3.Object(os.environ['BUCKET_NAME'], 'frontend/404.html').get()["Body"].read().decode('utf-8')).render(menu=non_index_menu)

        compressed_html = brotli_compress(html_content.encode('utf-8'))

        return Response(
            body=compressed_html,
            headers={'Content-Type': 'text/html; charset=UTF-8', 'Content-Encoding': 'br'},
            status_code=404
        )

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