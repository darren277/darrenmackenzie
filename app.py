""""""
import datetime
from chalice import Chalice, Response
import boto3 as boto3
from jinja2 import Environment, FileSystemLoader, BaseLoader
import markdown

from chalicelib.animation import animation_page_handler, load_img_handler
from chalicelib.articles import articles_list_handler
from chalicelib.caching import brotli_compress, create_response_headers, create_compressed_response
from chalicelib.main import build_paginator_from_query_params, get_menu_items, get_s3_template, get_website_data, \
    query_articles, build_pagination_urls, determine_page_status
from chalicelib.payments import stripe_webhook_handler, checkout_session_handler
from chalicelib.utils import datetime_filter, url_to_descriptive, icon_to_descriptive

DEBUG = True
LOCAL = True




def debug(current_request):
    print("[DEBUG] Requested Context:", current_request.context)
    print("[DEBUG] Query Parameters:", current_request.query_params)
    print("[DEBUG] Path Parameters:", current_request.uri_params)
    print("[DEBUG] Request Method:", current_request.method)
    # Log headers for debugging
    #print("[DEBUG] Headers:", current_request.headers)



app = Chalice(app_name="darrenmackenzie")

app.api.binary_types.extend([
    'application/javascript',
    'application/json',
    'text/css',
    'text/html',
    'application/xml'
])


#DEFAULT_PAGE_LIMIT = 10
#DEFAULT_PAGE_LIMIT = 3
#DEFAULT_PAGE_LIMIT = 9
DEFAULT_PAGE_LIMIT = 30

import os
cwd = os.path.dirname(__file__)
from os.path import join

env = Environment(loader=FileSystemLoader(join(cwd, 'chalicelib', 'frontend'), encoding='utf8'))

s3_env = Environment(loader=BaseLoader())


env.filters['datetime'] = datetime_filter
s3_env.filters['datetime'] = datetime_filter

env.filters['url_to_descriptive'] = url_to_descriptive
s3_env.filters['url_to_descriptive'] = url_to_descriptive

env.filters['icon_to_descriptive'] = icon_to_descriptive
s3_env.filters['icon_to_descriptive'] = icon_to_descriptive


"""
    MAIN ENDPOINT
"""



@app.route('/')
def script_template():
    """Handle the main website endpoint."""
    if DEBUG:
        debug(app.current_request)

    query_params = app.current_request.query_params or {}

    threejs_drawings = ['data']
    threejs_drawing = query_params.get('threejs_drawing', None)
    if threejs_drawing:
        threejs_drawings = [threejs_drawing]
    
    try:
        # Get menu items and parse query parameters
        menu = get_menu_items()
        tags_param = query_params.get('tags')
        tags = tags_param.split(',') if tags_param else None
        
        # Build paginator
        try:
            paginator = build_paginator_from_query_params(query_params)
        except Exception as e:
            print("Error building paginator:", e)
            return Response(str(e), status_code=400)
        
        # Get template from S3 and website data from DynamoDB
        template = get_s3_template(s3_env, os.environ['BUCKET_NAME'], local=LOCAL)
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
            'threejs_drawings': threejs_drawings
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




# paginated article fetching...
@app.route('/articles_list', methods=['GET'])
def articles_list():
    limit = int(app.current_request.query_params.get('limit', 10))
    cursor = int(app.current_request.query_params.get('cursor', datetime.datetime.now().timestamp() * 1_000))
    tags = app.current_request.query_params.get('tags', None)

    if LOCAL:
        return [
            dict(
                tags=['aws', 'python', 'lambda'],
                icons=[],
                title='Lambda Layers',
                slug='lambda-layers',
                created=1672790400000,
                description='Using Lambda layers can help you to reduce the size of your Lambda function deployment package. This is especially useful when you have a lot of dependencies.',
                thumbnail='',
            ),
            dict(
                tags=['aws', 'python', 'lambda'],
                icons=[],
                title='Lambda Layers 2',
                slug='lambda-layers-2',
                created=1672790400000,
                description='This is a story all about how my life got flipped turned upside down. Now I\'d like to take a minute so just site right there...',
                thumbnail='',
            ),
            dict(
                tags=['aws', 'python', 'lambda'],
                icons=[],
                title='Lambda Layers 3',
                slug='lambda-layers-3',
                created=1672790400000,
                description='This is a story lambda layers and how they got flipped turned upside down. Now I\'d like to take a minute so just site right there...',
                thumbnail='',
            ),
        ]
    return articles_list_handler(limit, cursor, tags)


"""
    JAVASCRIPT, JSON, AND CSS ENDPOINTS
"""
# Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource at https://darrenmackenzie-chalice-bucket.s3.us-east-1.amazonaws.com/scripts/main.js. (Reason: CORS header ‘Access-Control-Allow-Origin’ missing). Status code: 200.
@app.route('/scripts/threejs/main.js')
def serve_js():
    s3 = boto3.resource('s3')
    js_content = s3.Object(os.environ['BUCKET_NAME'], 'scripts/threejs/main.js').get()["Body"].read().decode('utf-8')

    compressed_js = brotli_compress(js_content.encode('utf-8'))
    
    return Response(
        body=compressed_js,
        headers=create_response_headers('application/javascript', compressed_js),
        status_code=200
    )

@app.route('/scripts/threejs/config/{filename}')
def serve_config(filename):
    s3 = boto3.resource('s3')
    js_content = s3.Object(os.environ['BUCKET_NAME'], f'scripts/threejs/config/{filename}').get()["Body"].read().decode('utf-8')

    compressed_js = brotli_compress(js_content.encode('utf-8'))

    return Response(
        body=compressed_js,
        headers=create_response_headers('application/javascript', compressed_js),
        status_code=200
    )

@app.route('/scripts/threejs/drawing/{filename}')
def serve_drawing(filename):
    s3 = boto3.resource('s3')
    js_content = s3.Object(os.environ['BUCKET_NAME'], f'scripts/threejs/drawing/{filename}').get()["Body"].read().decode('utf-8')

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

@app.route('/data/{filename}')
def serve_data(filename):
    if filename == 'data.json' or filename == 'music.json':
        s3 = boto3.resource('s3')
        json_content = s3.Object(os.environ['BUCKET_NAME'], f'data/{filename}').get()["Body"].read().decode('utf-8')

        compressed_json = brotli_compress(json_content.encode('utf-8'))

        return Response(
            body=compressed_json,
            headers=create_response_headers('application/json', compressed_json),
            status_code=200
        )
    else:
        # return 404...
        json_content = {'error': 'File not found'}
        compressed_json = brotli_compress(json_content)

        return Response(
            body=compressed_json,
            headers={'Content-Type': 'application/json'},
            status_code=404
        )

@app.route('/style.css')
def serve_css():
    s3 = boto3.resource('s3')
    if LOCAL:
        css_content = open(join(cwd, 'templates', 'style.css'), 'r').read()
    else:
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
    if DEBUG:
        debug(app.current_request)
    
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
    article_data = article_table.get_item(Key={'type_of_article': section, "slug": article}).get('Item')

    if DEBUG:
        print("[DEBUG] Section", section)
        print("[DEBUG] Article Slug", article)
        print("[DEBUG] Article Table", os.environ['ARTICLE_TABLE'])
        print("[DEBUG] Article:", article_data)
    
    if article_data:
        if LOCAL:
            full_article_html_string = open(join(cwd, 'templates', 'article.html'), 'r').read()
        else:
            full_article_html_string = s3.Object(os.environ['BUCKET_NAME'], 'frontend/article.html').get()["Body"].read().decode('utf-8')
        full_article_html = s3_env.from_string(full_article_html_string).render(section=section, article=article_data, menu=non_index_menu)
        
        md_content = article_data['body']

        html_content = markdown.markdown(md_content, extensions=["fenced_code", "codehilite", "tables", "toc"])

        full_article_html = full_article_html.replace('___ARTICLE___', html_content)

        compressed_html = brotli_compress(full_article_html.encode('utf-8'))

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
    return checkout_session_handler()

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = app.current_request.raw_body
    sig_header = app.current_request.headers.get('Stripe-Signature', '')
    return stripe_webhook_handler(payload, sig_header)


@app.route('/load_img', methods=['GET'])
def load_img():
    img_url = app.current_request.query_params.get('img_url', None)
    return load_img_handler(img_url)


@app.route('/animation', methods=['GET'])
def animation():
    animation_name = app.current_request.query_params.get('animation_name', None)
    background_image_url = app.current_request.query_params.get('background_image_url', None)

    show_path = app.current_request.query_params.get('show_path', None)
    show_path_bool = show_path == 'true'

    dot_size = app.current_request.query_params.get('dot_size', None)
    dot_size = int(dot_size) if dot_size else None

    dot_color = app.current_request.query_params.get('dot_color', None)

    image_top_padding = app.current_request.query_params.get('top_padding', None)
    image_bottom_padding = app.current_request.query_params.get('bottom_padding', None)

    return animation_page_handler(animation_name, background_image_url, show_path_bool, dot_size, dot_color, image_top_padding, image_bottom_padding)


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