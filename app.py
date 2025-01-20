from chalice import Chalice, Response
import json
from os import path
import boto3 as boto3
from jinja2 import Environment, FileSystemLoader, BaseLoader
import stripe

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

import os
cwd = os.path.dirname(__file__)
from os.path import join

env = Environment(loader=FileSystemLoader(join(cwd, 'chalicelib', 'frontend'), encoding='utf8'))

s3_env = Environment(loader=BaseLoader())

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
    return Response(template.render(services=website_data['services'], social=website_data['social'], projects=website_data['projects'], articles=website_data['articles'], menu=menu), headers={'Content-Type': 'text/html; charset=UTF-8'}, status_code=200)

# Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource at https://darrenmackenzie-chalice-bucket.s3.us-east-1.amazonaws.com/scripts/main.js. (Reason: CORS header ‘Access-Control-Allow-Origin’ missing). Status code: 200.
@app.route('/scripts/main.js')
def serve_js():
    s3 = boto3.resource('s3')
    myString = s3.Object(os.environ['BUCKET_NAME'], 'scripts/main.js').get()["Body"].read().decode('utf-8')
    return Response(myString, headers={'Content-Type': 'text/javascript'}, status_code=200)

@app.route('/scripts/helvetiker_regular.typeface.json')
def serve_font():
    s3 = boto3.resource('s3')
    myString = s3.Object(os.environ['BUCKET_NAME'], 'scripts/helvetiker_regular.typeface.json').get()["Body"].read().decode('utf-8')
    return Response(myString, headers={'Content-Type': 'application/json'}, status_code=200)

@app.route('/data/data.json')
def serve_data():
    s3 = boto3.resource('s3')
    myString = s3.Object(os.environ['BUCKET_NAME'], 'data/data.json').get()["Body"].read().decode('utf-8')
    return Response(myString, headers={'Content-Type': 'application/json'}, status_code=200)

@app.route('/style.css')
def serve_css():
    s3 = boto3.resource('s3')
    myString = s3.Object(os.environ['BUCKET_NAME'], 'frontend/style.css').get()["Body"].read().decode('utf-8')
    return Response(myString, headers={'Content-Type': 'text/css'}, status_code=200)


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
    if section not in ['services', 'work', 'blog']: return Response(s3_env.from_string(s3.Object(os.environ['BUCKET_NAME'], 'frontend/404.html').get()["Body"].read().decode('utf-8')).render(menu=non_index_menu), headers={'Content-Type': 'text/html; charset=UTF-8'}, status_code=404)
    db = boto3.resource('dynamodb')
    article_table = db.Table(os.environ['ARTICLE_TABLE'])
    article = article_table.get_item(Key={'type_of_article': section, "slug": article}).get('Item')
    return Response(s3_env.from_string(s3.Object(os.environ['BUCKET_NAME'], 'frontend/article.html').get()["Body"].read().decode('utf-8')).render(section=section, article=article, menu=non_index_menu), headers={'Content-Type': 'text/html; charset=UTF-8'}, status_code=200) if article else Response(s3_env.from_string(s3.Object(os.environ['BUCKET_NAME'], 'frontend/404.html').get()["Body"].read().decode('utf-8')).render(menu=non_index_menu), headers={'Content-Type': 'text/html; charset=UTF-8'}, status_code=404)

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
