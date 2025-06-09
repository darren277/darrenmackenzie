""""""
import datetime
import os

import boto3


def add_article_to_v2(unique_id: int, content: str, tags: [str], removed: int = 0, description: str = '', slug: str = '',
                      title: str = '', url: str = '', thumbnail: str = ''):
    dynamodb = boto3.resource('dynamodb')
    articles = dynamodb.Table(os.environ['ARTICLES_V2_TABLE'])
    tag_index = dynamodb.Table(os.environ['TAG_INDEX_TABLE'])

    doc = {
        'content': content,
        'tags': tags,
        'removed': removed,
        'createdAt': int(datetime.datetime.now().timestamp() * 1000),  # milliseconds
        'updatedAt': int(datetime.datetime.now().timestamp() * 1000),  # milliseconds
        'description': description,
        'slug': slug,
        'title': title,
        'url': url,
        'thumbnail': thumbnail
    }

    doc['PK'] = 'ARTICLE'
    doc['SK'] = unique_id
    articles.put_item(Item=doc)

    for tag in doc.get('tags', []):
        tag_index.put_item(Item={'tag': tag, 'uniqueId': unique_id, 'removed': doc.get('removed', 0)})
