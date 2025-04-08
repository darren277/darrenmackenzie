""""""
import json
import os
from typing import List

import boto3
import brotli
from chalice import Response

from chalicelib.caching import create_response_headers

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


def articles_list_handler(limit, cursor, tags):
    response_data = get_articles_list(limit, cursor, tags)
    json_data = json.dumps(response_data)
    compressed_json = brotli.compress(json_data.encode('utf-8'))

    return Response(
        body=compressed_json,
        headers=create_response_headers('application/json', compressed_json),
        status_code=200
    )
