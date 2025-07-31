""""""
import json

from chalice import Chalice, Response
import boto3 as boto3
from jinja2 import Environment, FileSystemLoader, BaseLoader
import markdown

from chalicelib.animation import animation_page_handler, load_img_handler
from chalicelib.paginator_v2 import _unb64, list_articles
from chalicelib.threejs_dict import ANIMATIONS_DICT
from chalicelib.caching import brotli_compress, create_response_headers, create_compressed_response
from chalicelib.main import get_menu_items, get_s3_template, get_website_data
from chalicelib.payments import stripe_webhook_handler, checkout_session_handler
from chalicelib.threejs_helpers import populate_importmaps, grouped_nav_items
from chalicelib.utils import datetime_filter, url_to_descriptive, icon_to_descriptive

DEBUG = True
LOCAL = False
THREEJS_VERSION = '0.169.0'




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
    'application/xml',
    'image/x-icon'
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


def create_threejs_data(animation: str, data_selected: str, fullscreen: bool = False, navbar: bool = False):
    viz = ANIMATIONS_DICT.get(animation, ANIMATIONS_DICT['multiaxis'])
    print('viz', viz, 'multiaxis', ANIMATIONS_DICT)

    threejs_version = viz.get('threejs_version', THREEJS_VERSION)

    # TODO: Too many imports by default, need to fix this.
    importmap = populate_importmaps(animation, threejs_version)

    threejs_template_data = dict(
        threejs_version=THREEJS_VERSION,
        threejs_drawings=viz,
        data_selected=data_selected,
        importmap=json.dumps(importmap, indent=4),
        fullscreen=fullscreen,
    )

    if navbar:
        nav_item_ordering = ['Special', 'Educational', 'Quantitative', 'Spatial', 'World Building', 'Experimental',
                             'Component', 'Attribution', 'Work in Progress', 'Local']
        ordered_grouped_nav_items = grouped_nav_items(nav_item_ordering)
        threejs_template_data['grouped_nav_items'] = ordered_grouped_nav_items
    else:
        threejs_template_data['grouped_nav_items'] = dict()

    return threejs_template_data


def fetch_paginated(after, before, tag, threejs_template_data, article_type: str = 'ARTICLE', page_name: str = 'Blog'):
    try:
        # Get menu items and parse query parameters
        menu = get_menu_items()

        # Get template from S3 and website data from DynamoDB
        template = get_s3_template(s3_env, os.environ['BUCKET_NAME'], local=LOCAL)
        website_data = get_website_data(os.environ['HOME_TABLE'])

        # Query articles
        try:
            if before:
                direction = 'newer'
                cursor = before
            else:
                direction = 'older'
                cursor = after

            items, next_key, prev_key = list_articles(
                tag=tag,
                start_key=cursor,
                full_articles=False,
                direction=direction,
                article_type=article_type,
            )

            print(f"[DEBUG] Direction: {direction}, Tag: {tag}, After: {after}, Before: {before}, Cursor: {cursor}, Number of items: {len(items)}")
        except Exception as e:
            print("Error querying DynamoDB:", e)
            return Response(str(e), status_code=500)

        print('[DEBUG] Queried articles:', len(items), items)

        print('prev_key', prev_key)
        print('next_key', next_key)

        # Render template
        template_data = {
            'social': website_data['social'],
            'articles': items,
            'menu': menu,
            'prev_key': prev_key,
            'next_key': next_key,
        }
        html_content = template.render(**template_data, **threejs_template_data, page_name=page_name)

        # Create and return response
        return create_compressed_response(html_content, skip_caching=True)

    except Exception as e:
        print(f"Unexpected error in script_template: {e}")
        return Response(str(e), status_code=500)

@app.route('/')
def index():
    """Handle the main website endpoint."""
    if DEBUG:
        debug(app.current_request)

    query_params = app.current_request.query_params or {}

    after = _unb64(query_params.get("after"))
    before = _unb64(query_params.get("before"))

    tag = query_params.get('tag') if query_params else None

    animation = query_params.get('animation', 'multiaxis') if query_params else 'multiaxis'
    data_selected = query_params.get('data_selected', 'data') if query_params else 'data'

    threejs_template_data = create_threejs_data(animation, data_selected)
    
    return fetch_paginated(after, before, tag, threejs_template_data)


@app.route('/index.html')
def index_html():
    # redirect to `/`
    return Response(body='', headers={'Location': 'https://www.darrenmackenzie.com'}, status_code=301)


@app.route('/projects')
def projects():
    """Handle the main website endpoint."""
    if DEBUG:
        debug(app.current_request)

    query_params = app.current_request.query_params or {}

    after = _unb64(query_params.get("after"))
    before = _unb64(query_params.get("before"))

    tag = query_params.get('tag') if query_params else None

    animation = query_params.get('animation', 'multiaxis') if query_params else 'multiaxis'
    data_selected = query_params.get('data_selected', 'data') if query_params else 'data'

    threejs_template_data = create_threejs_data(animation, data_selected)

    return fetch_paginated(after, before, tag, threejs_template_data, article_type='PROJECT', page_name='Projects')


@app.route('/work')
def work():
    """Handle the main website endpoint."""
    if DEBUG:
        debug(app.current_request)

    query_params = app.current_request.query_params or {}

    after = _unb64(query_params.get("after"))
    before = _unb64(query_params.get("before"))

    tag = query_params.get('tag') if query_params else None

    animation = query_params.get('animation', 'multiaxis') if query_params else 'multiaxis'
    data_selected = query_params.get('data_selected', 'data') if query_params else 'data'

    threejs_template_data = create_threejs_data(animation, data_selected)

    return fetch_paginated(after, before, tag, threejs_template_data, article_type='WORK', page_name='Past Work')

def serve_threejs_helper(animation: str = 'multiaxis', query_params: dict = None, fullscreen: bool = False):
    print('ABOUT TO SERVE THREEJS ANIMATION:', animation)
    s3 = boto3.resource('s3')

    if LOCAL:
        template_string = open(join(cwd, 'templates', 'threejs.html'), 'r').read()
    else:
        template_string = s3.Object(os.environ['BUCKET_NAME'], 'frontend/threejs.html').get()["Body"].read().decode('utf-8')

    animation = animation.replace('_fullscreen', '')
    viz = ANIMATIONS_DICT.get(animation, ANIMATIONS_DICT['multiaxis'])
    print('viz:', animation, viz)
    # data_selected_query_param = request.args.get('data_selected')
    data_selected_query_param = query_params.get('data_selected', None) if query_params else None
    data_selected = data_selected_query_param if data_selected_query_param else viz.get('data_sources', [None])[0] if len(viz.get('data_sources', [])) > 0 else None
    print('data_selected:', data_selected)

    threejs_template_data = create_threejs_data(animation, data_selected, navbar=not fullscreen, fullscreen=fullscreen)

    html_content = s3_env.from_string(template_string).render(**threejs_template_data)

    return create_compressed_response(html_content, skip_caching=True)

l = [
    'adventure1','adventure2','buildings','cards','cayley','clustering','data','experimental_1','experimental','familytree',
    'force','force3d','forest','math','music','network','periodic','philpapers','resume', 'infographics', 'neuralnetworks', 'mlchooser',
    'anatomy'
]

@app.route('/threejs/{animation}')
def serve_threejs(animation):
    query_params = app.current_request.query_params
    fullscreen = True if animation.endswith('_fullscreen') or animation == 'resume' else False
    if animation == 'resume':
        query_params = dict(data_selected='resume')
        animation = 'adventure'

    # TODO: TIDY THIS ALL UP BEFORE PUSH.
    if fullscreen and not query_params:
        #if query_params['data_selected'] not in l:
        #    print(f"WARNING: Data selected '{query_params['data_selected']}' is not in the predefined list {l}. Using 'data' instead.")
        query_params = dict(data_selected='data')

    return serve_threejs_helper(animation, query_params, fullscreen=fullscreen)


@app.route('/scripts/bundled/{path+}', methods=['GET'])
def bundled_fallback_to_s3():
    path = app.current_request.uri_params['path+'] if LOCAL else app.current_request.uri_params['path']
    print("FALLBACK STATIC FILE ROUTER (bundled):", path)
    bucket_url = f"https://{os.environ['BUCKET_NAME']}.s3.amazonaws.com/scripts/bundled/{path}"
    return Response(body='', status_code=302, headers={'Location': bucket_url, 'Content-Type': 'text/plain'})

# @app.route('/threejs/imagery/{optional_prefix+}/{path+}', methods=['GET'])
# Only one variable part in path allowed when deployed...
@app.route('/threejs/imagery/{path+}', methods=['GET'])
def imagery_fallback_to_s3():
    path = app.current_request.uri_params['path+'] if LOCAL else app.current_request.uri_params['path']
    if 'optional_prefix+' in app.current_request.uri_params:
        optional_prefix = app.current_request.uri_params['optional_prefix+']
        path = f"{optional_prefix}/{path}"
    else:
        optional_prefix = ''
    print("FALLBACK STATIC FILE ROUTER (imagery):", path)
    bucket_url = f"https://{os.environ['BUCKET_NAME']}.s3.amazonaws.com/scripts/threejs/imagery/{path}"
    return Response(body='', status_code=302, headers={'Location': bucket_url, 'Content-Type': 'text/plain'})

@app.route('/threejs/textures/{path+}', methods=['GET'])
def textures_fallback_to_s3():
    path = app.current_request.uri_params['path+'] if LOCAL else app.current_request.uri_params['path']
    print("FALLBACK STATIC FILE ROUTER (textures):", path)
    bucket_url = f"https://{os.environ['BUCKET_NAME']}.s3.amazonaws.com/scripts/threejs/textures/{path}"
    return Response(body='', status_code=302, headers={'Location': bucket_url, 'Content-Type': 'text/plain'})

@app.route('/threejs/config/{path+}', methods=['GET'])
def config_fallback_to_s3():
    path = app.current_request.uri_params['path+'] if LOCAL else app.current_request.uri_params['path']
    print("FALLBACK STATIC FILE ROUTER (drawing):", path)
    bucket_url = f"https://{os.environ['BUCKET_NAME']}.s3.amazonaws.com/scripts/threejs/config/{path}?v=1"
    return Response(body='', status_code=302, headers={'Location': bucket_url, 'Content-Type': 'text/plain'})

@app.route('/threejs/drawing/{path+}', methods=['GET'])
def drawing_fallback_to_s3():
    path = app.current_request.uri_params['path+'] if LOCAL else app.current_request.uri_params['path']
    print("FALLBACK STATIC FILE ROUTER (drawing):", path)
    bucket_url = f"https://{os.environ['BUCKET_NAME']}.s3.amazonaws.com/scripts/threejs/drawing/{path}"
    return Response(body='', status_code=302, headers={'Location': bucket_url, 'Content-Type': 'text/plain'})

@app.route('/threejs/data/{path+}', methods=['GET'])
def data_fallback_to_s3():
    path = app.current_request.uri_params['path+'] if LOCAL else app.current_request.uri_params['path']
    print("FALLBACK STATIC FILE ROUTER (data):", path)
    bucket_url = f"https://{os.environ['BUCKET_NAME']}.s3.amazonaws.com/scripts/threejs/data/{path}?v=1"
    return Response(body='', status_code=302, headers={'Location': bucket_url, 'Content-Type': 'text/plain'})


"""
    JAVASCRIPT, JSON, AND CSS ENDPOINTS
"""
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

@app.route('/static/styles/caption-labels.css')
def serve_css():
    s3 = boto3.resource('s3')
    css_content = s3.Object(os.environ['BUCKET_NAME'], 'frontend/caption-labels.css').get()["Body"].read().decode('utf-8')

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

SECTIONS_DICT = {
    'articles': 'ARTICLE',
    'blog': 'ARTICLE',
    'projects': 'PROJECT',
    'work': 'WORK',
    'services': 'SERVICE',
}

@app.route('/{section}/{article}')
def articles(section, article):
    if DEBUG:
        debug(app.current_request)

    if section == 'threejs':
        return serve_threejs(article)

    s3 = boto3.resource('s3')
    website_menu = get_menu_items()
    non_index_menu = [dict(title=item['title'], url=f"/index.html{item['url']}") for item in website_menu]
    if section not in ['services', 'work', 'blog', 'projects', 'articles']:
        html_content = s3_env.from_string(s3.Object(os.environ['BUCKET_NAME'], 'frontend/404.html').get()["Body"].read().decode('utf-8')).render(menu=non_index_menu)

        compressed_html = brotli_compress(html_content.encode('utf-8'))

        return Response(
            body=compressed_html,
            headers=create_response_headers('text/html; charset=UTF-8', compressed_html),
            status_code=404
        )

    db = boto3.resource('dynamodb')
    article_table = db.Table(os.environ['ARTICLES_V2_TABLE'])

    pk = SECTIONS_DICT.get(section, None)
    sk = article.split('-')[0] if '-' in article else None

    try: sk = int(sk)
    except ValueError: sk = None

    if not pk or not sk:
        html_content = s3_env.from_string(
            s3.Object(os.environ['BUCKET_NAME'], 'frontend/404.html').get()["Body"].read().decode('utf-8')).render(
            menu=non_index_menu)
        compressed_html = brotli_compress(html_content.encode('utf-8'))
        return Response(
            body=compressed_html,
            headers=create_response_headers('text/html; charset=UTF-8', compressed_html),
            status_code=404
        )

    print("[DEBUG] Fetching article with PK:", pk, "and SK:", sk)
    article_data = article_table.get_item(Key={'PK': pk, 'SK': sk}).get('Item', None)

    if DEBUG:
        print(f"[DEBUG] PK: {pk}. SK: {sk}.")
        print("[DEBUG] Section", section)
        print("[DEBUG] Article Slug", article)
        print("[DEBUG] Article Table", os.environ['ARTICLES_V2_TABLE'])
        print("[DEBUG] Article:", article_data)

    if article_data:
        if LOCAL:
            full_article_html_string = open(join(cwd, 'templates', 'article.html'), 'r').read()
        else:
            full_article_html_string = s3.Object(os.environ['BUCKET_NAME'], 'frontend/article.html').get()["Body"].read().decode('utf-8')
        full_article_html = s3_env.from_string(full_article_html_string).render(section=section, article=article_data, menu=non_index_menu)

        md_content = article_data['body']

        html_content = markdown.markdown(md_content, extensions=["fenced_code", "codehilite", "tables", "toc", "md_mermaid"])

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

@app.route('/favicon.ico')
def favicon():
    s3 = boto3.resource('s3')
    favicon_content = s3.Object(os.environ['BUCKET_NAME'], 'frontend/favicon.ico').get()["Body"].read()

    compressed_favicon = brotli_compress(favicon_content)

    try:
        return Response(
            body=compressed_favicon,
            headers=create_response_headers('image/x-icon', compressed_favicon),
            status_code=200
        )
    except Exception as e:
        print(f"Error serving favicon: {e}")
        return Response(body='Error serving favicon', status_code=500)

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