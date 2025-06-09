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
def index():
    """Handle the main website endpoint."""
    if DEBUG:
        debug(app.current_request)

    query_params = app.current_request.query_params or {}

    after = _unb64(query_params.get("after"))
    before = _unb64(query_params.get("before"))

    tag = query_params.get('tag') if query_params else None

    threejs_drawings = ['data']
    threejs_drawing = query_params.get('threejs_drawing', None)
    if threejs_drawing:
        threejs_drawings = [threejs_drawing]
    
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
                direction=direction
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
            'threejs_drawings': threejs_drawings
        }
        html_content = template.render(**template_data)
        
        # Create and return response
        return create_compressed_response(html_content, skip_caching=True)
    
    except Exception as e:
        print(f"Unexpected error in script_template: {e}")
        return Response(str(e), status_code=500)


@app.route('/index.html')
def index_html():
    # redirect to `/`
    return Response(body='', headers={'Location': 'https://www.darrenmackenzie.com'}, status_code=301)



@app.route('/threejs/<animation>')
def serve_threejs(animation):
    print('ABOUT TO SERVE THREEJS ANIMATION:', animation)
    s3 = boto3.resource('s3')

    if LOCAL:
        template_string = open(join(cwd, 'templates', 'threejs.html'), 'r').read()
    else:
        template_string = s3_env.from_string(s3.Object(os.environ['BUCKET_NAME'], 'frontend/threejs.html').get()["Body"].read().decode('utf-8'))

    viz = ANIMATIONS_DICT.get(animation, ANIMATIONS_DICT['multiaxis'])
    #data_selected_query_param = request.args.get('data_selected')
    data_selected_query_param = app.current_request.query_params.get('data_selected', None) if app.current_request.query_params else None
    data_selected = data_selected_query_param if data_selected_query_param else viz.get('data_sources', [None])[0] if len(viz.get('data_sources', [])) > 0 else None
    print('data_selected:', data_selected)

    threejs_version = viz.get('threejs_version', THREEJS_VERSION)
    importmap = populate_importmaps(animation, threejs_version)

    nav_item_ordering = ['Special', 'Educational', 'Quantitative', 'Spatial', 'World Building', 'Experimental', 'Component', 'Attribution', 'Work in Progress', 'Local']
    ordered_grouped_nav_items = grouped_nav_items(nav_item_ordering)

    html_content = s3_env.from_string(template_string).render(
        threejs_version=THREEJS_VERSION,
        threejs_drawings=viz,
        grouped_nav_items=ordered_grouped_nav_items,
        main_js_path='/threejs/scripts/main.js',
        data_selected=data_selected,
        importmap=json.dumps(importmap, indent=4),
    )
    compressed_html = brotli_compress(html_content.encode('utf-8'))

    return Response(
        body=compressed_html,
        headers=create_response_headers('text/html; charset=UTF-8', compressed_html),
        status_code=404
    )


"""
    JAVASCRIPT, JSON, AND CSS ENDPOINTS
"""
# Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource at https://darrenmackenzie-chalice-bucket.s3.us-east-1.amazonaws.com/scripts/main.js. (Reason: CORS header ‘Access-Control-Allow-Origin’ missing). Status code: 200.
@app.route('/threejs/scripts/main.js')
def serve_js():
    s3 = boto3.resource('s3')
    js_content = s3.Object(os.environ['BUCKET_NAME'], 'scripts/threejs/main.js').get()["Body"].read().decode('utf-8')

    compressed_js = brotli_compress(js_content.encode('utf-8'))
    
    return Response(
        body=compressed_js,
        headers=create_response_headers('application/javascript', compressed_js),
        status_code=200
    )

@app.route('/threejs/scripts/drawings.js')
def serve_js():
    s3 = boto3.resource('s3')
    js_content = s3.Object(os.environ['BUCKET_NAME'], 'scripts/threejs/drawings.js').get()["Body"].read().decode('utf-8')

    compressed_js = brotli_compress(js_content.encode('utf-8'))

    return Response(
        body=compressed_js,
        headers=create_response_headers('application/javascript', compressed_js),
        status_code=200
    )

@app.route('/threejs/scripts/config/{filename}')
def serve_config(filename):
    s3 = boto3.resource('s3')
    js_content = s3.Object(os.environ['BUCKET_NAME'], f'scripts/threejs/config/{filename}').get()["Body"].read().decode('utf-8')

    compressed_js = brotli_compress(js_content.encode('utf-8'))

    return Response(
        body=compressed_js,
        headers=create_response_headers('application/javascript', compressed_js),
        status_code=200
    )

@app.route('/threejs/scripts/drawing/adventure/{filename}')
def serve_adventure_drawing(filename):
    s3 = boto3.resource('s3')
    js_content = s3.Object(os.environ['BUCKET_NAME'], f'scripts/threejs/drawing/adventure/{filename}').get()["Body"].read().decode('utf-8')

    compressed_js = brotli_compress(js_content.encode('utf-8'))

    return Response(
        body=compressed_js,
        headers=create_response_headers('application/javascript', compressed_js),
        status_code=200
    )

@app.route('/threejs/scripts/drawing/library/{filename}')
def serve_library_drawing(filename):
    s3 = boto3.resource('s3')
    js_content = s3.Object(os.environ['BUCKET_NAME'], f'scripts/threejs/drawing/library/{filename}').get()["Body"].read().decode('utf-8')

    compressed_js = brotli_compress(js_content.encode('utf-8'))

    return Response(
        body=compressed_js,
        headers=create_response_headers('application/javascript', compressed_js),
        status_code=200
    )

@app.route('/threejs/scripts/drawing/{filename}')
def serve_drawing(filename):
    s3 = boto3.resource('s3')
    js_content = s3.Object(os.environ['BUCKET_NAME'], f'scripts/threejs/drawing/{filename}').get()["Body"].read().decode('utf-8')

    compressed_js = brotli_compress(js_content.encode('utf-8'))

    return Response(
        body=compressed_js,
        headers=create_response_headers('application/javascript', compressed_js),
        status_code=200
    )


@app.route('/threejs/scripts/helvetiker_regular.typeface.json')
def serve_font():
    s3 = boto3.resource('s3')
    json_content = s3.Object(os.environ['BUCKET_NAME'], 'scripts/helvetiker_regular.typeface.json').get()["Body"].read().decode('utf-8')

    compressed_json = brotli_compress(json_content.encode('utf-8'))

    return Response(
        body=compressed_json,
        headers=create_response_headers('application/json', compressed_json),
        status_code=200
    )

@app.route('/threejs/data/{filename}')
def serve_data(filename):
    if filename in [
        'data.json',
        'music.json',
        'cayley.json',
        'force.json',
        'adventure1.json',
        'adventure2.json',
        'experimental.json',
        'experimental_1.json',
        'cards.json',
        'clustering.json',
        'force3d.json',
        'philpapers.json',
        'math.json',
        'buildings.geojson',
        'periodic.json',
        'network.json',
        'familytree.json'
    ]:
        s3 = boto3.resource('s3')
        json_content = s3.Object(os.environ['BUCKET_NAME'], f'data/{filename}').get()["Body"].read().decode('utf-8')

        compressed_json = brotli_compress(json_content.encode('utf-8'))

        prefix = 'geo+' if filename.endswith('.geojson') else ''

        mimetype = f'application/{prefix}json'

        return Response(
            body=compressed_json,
            headers=create_response_headers(mimetype, compressed_json),
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


def serve_texture_helper(filename: str):
    print("[DEBUG] Serving texture:", filename)
    s3 = boto3.resource('s3')
    if filename.endswith('.jpg') or filename.endswith('.jpeg'):
        mimetype = 'image/jpeg'
    elif filename.endswith('.png'):
        mimetype = 'image/png'
    elif filename.endswith('.mp4'):
        mimetype = 'video/mp4'
    elif filename.endswith('.exr'):
        mimetype = 'image/vnd.radiance'
    else:
        return Response(body='Unsupported file type', status_code=400)

    try:
        image_content = s3.Object(os.environ['BUCKET_NAME'], f'textures/{filename}').get()["Body"].read()
    except:
        image_content = s3.Object(os.environ['BUCKET_NAME'], f'textures/Canestra_di_frutta_Caravaggio.jpg').get()["Body"].read()

    compressed_image = brotli_compress(image_content)

    return Response(
        body=compressed_image,
        headers=create_response_headers(mimetype, compressed_image),
        status_code=200
    )


# TODO: Something recursive like this: @app.route('/threejs/textures/{texture_path+}', methods=['GET'])
@app.route('/threejs/textures/cards/standard/{filename}')
def serve_cards_standard_texture(filename): return serve_texture_helper(f'cards/standard/{filename}')
@app.route('/threejs/textures/cards/{filename}')
def serve_cards_texture(filename): return serve_texture_helper(f'cards/{filename}')

@app.route('/threejs/textures/{filename}')
def serve_texture(filename): return serve_texture_helper(filename)





@app.route('/threejs/imagery/brain/ply/{filename}')
def serve_brain_ply_image(filename): return serve_image_helper(f'brain/ply/{filename}')
@app.route('/threejs/imagery/brain/obj/{filename}')
def serve_brain_obj_image(filename): return serve_image_helper(f'brain/obj/{filename}')
@app.route('/threejs/imagery/farm/{filename}')
def serve_farm_image(filename):
    if '%20' in filename: filename = filename.replace('%20', ' ')
    return serve_image_helper(f'farm/{filename}')
@app.route('/threejs/imagery/pdb/{filename}')
def serve_pdb_image(filename): return serve_image_helper(f'pdb/{filename}')
@app.route('/threejs/imagery/piano/piano-mp3/{filename}')
def serve_piano_mp3_image(filename): return serve_image_helper(f'piano/piano-mp3/{filename}')
@app.route('/threejs/imagery/piano/textures/{filename}')
def serve_piano_textures_image(filename): return serve_image_helper(f'piano/textures/{filename}')
@app.route('/threejs/imagery/piano/{filename}')
def serve_piano_image(filename): return serve_image_helper(f'piano/{filename}')
@app.route('/threejs/imagery/skibidi/{filename}')
def serve_skibidi_image(filename): return serve_image_helper(f'skibidi/{filename}')


@app.route('/threejs/imagery/{filename}')
def serve_image(filename):
    return serve_image_helper(filename)

def serve_image_helper(filename: str):
    s3 = boto3.resource('s3')
    if filename.endswith('.jpg') or filename.endswith('.jpeg'):
        mimetype = 'image/jpeg'
    elif filename.endswith('.png'):
        mimetype = 'image/png'
    elif filename.endswith('.svg'):
        mimetype = 'image/svg+xml'
    elif filename.endswith('.glb'):
        mimetype = 'model/gltf-binary'
    elif filename.endswith('.gltf'):
        mimetype = 'model/gltf+json'
    elif filename.endswith('.bin'):
        mimetype = 'model/gltf-binary'
    elif filename.endswith('.ply'):
        mimetype = 'model/ply'
    elif filename.endswith('.obj'):
        mimetype = 'model/obj'
    elif filename.endswith('.mp3'):
        mimetype = 'audio/mpeg'
    elif filename.endswith('.pdb'):
        mimetype = 'chemical/x-pdb'
    else:
        return Response(body='Unsupported file type', status_code=400)

    image_content = s3.Object(os.environ['BUCKET_NAME'], f'imagery/{filename}').get()["Body"].read()

    compressed_image = brotli_compress(image_content)

    return Response(
        body=compressed_image,
        headers=create_response_headers(mimetype, compressed_image),
        status_code=200
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
@app.route('/{section}/{article}')
def articles(section, article):
    if DEBUG:
        debug(app.current_request)

    if section == 'threejs':
        return serve_threejs(article)
    
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

@app.route('/favicon.ico')
def favicon():
    s3 = boto3.resource('s3')
    favicon_content = s3.Object(os.environ['BUCKET_NAME'], 'frontend/favicon.ico').get()["Body"].read()

    compressed_favicon = brotli_compress(favicon_content)

    return Response(
        body=compressed_favicon,
        headers=create_response_headers('image/x-icon', compressed_favicon),
        status_code=200
    )

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