from chalice import Chalice, Response
import json
from os import path
import boto3 as boto3
from jinja2 import Environment, FileSystemLoader, BaseLoader

app = Chalice(app_name="darrenmackenzie")

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
    myString = s3.Object(os.environ['BUCKET_NAME'], 'frontend/index.html').get()["Body"].read().decode('utf-8')
    template = s3_env.from_string(myString)
    db = boto3.resource('dynamodb')
    table = db.Table(os.environ['HOME_TABLE'])
    ## data = app.current_request.json_body
    website_data = table.get_item(Key={'section': 'website_data'})['Item']
    return Response(template.render(services=website_data['services'], social=website_data['social'], projects=website_data['projects'], articles=website_data['articles'], menu=menu), headers={'Content-Type': 'text/html; charset=UTF-8'}, status_code=200)


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


