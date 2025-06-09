""""""
import os
import json
import base64
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
import boto3
import functools


PAGE_SIZE = 6

# PK, SK, and url are reserved words so we alias them
expression_attribute_names = {'#PK': 'PK', '#SK': 'SK', '#url': 'url'}


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            # convert to int if it has no fractional part, otherwise float
            if o % 1 == 0:
                return int(o)
            return float(o)
        return super().default(o)


def _b64(x: dict | None) -> str | None:
    if not x:
        return None
    try:
        dumped = json.dumps(x, cls=DecimalEncoder)
        return base64.urlsafe_b64encode(dumped.encode()).decode()
    except Exception as e:
        print("Error encoding to base64:", e, x)
        return None


def _unb64(s: str | None) -> dict | None:
    try:
        return json.loads(base64.urlsafe_b64decode(s)) if s else None
    except Exception as e:
        print("Error decoding from base64:", e)
        return None

dynamodb = boto3.resource('dynamodb')

articles_db = dynamodb.Table(os.environ['ARTICLES_V2_TABLE'])
tag_index = dynamodb.Table(os.environ['TAG_INDEX_TABLE'])


def _encode_key(dynamo_key):
    # Dynamo keys are JSON‑serialisable already, but we may want to base64‑encode to keep the URL short / opaque.
    return dynamo_key



def _query_primary_feed(page_size: int, projection_expression: str, expression_attribute_names: dict or None = None, start_key=None):
    # one‑time check: does this table have the GSI?
    functools.lru_cache(maxsize=1)

    def _has_removed_index():
        idxs = articles_db.global_secondary_indexes or []
        return any(i['IndexName'] == 'removed-index' for i in idxs)

    kwargs = {
        'Limit': page_size,
        'ScanIndexForward': False         # newest first
    }

    if start_key:
        kwargs['ExclusiveStartKey'] = start_key

    if projection_expression:  # add only if supplied
        kwargs['ProjectionExpression'] = projection_expression
        # If you used aliases for reserved words, also pass:
        # kwargs['ExpressionAttributeNames'] = {'#t': 'title'}
        if expression_attribute_names:
            kwargs['ExpressionAttributeNames'] = expression_attribute_names

    if _has_removed_index():
        # Try the preferred plan: use the GSI
        resp = articles_db.query(
            IndexName='removed-index',
            #KeyConditionExpression=Key('removed').eq(0),
            KeyConditionExpression=Key('removed').eq(False),
            **kwargs
        )
    else:
        # GSI not present yet → fall back to base table + filter
        resp = articles_db.query(
            KeyConditionExpression=Key('PK').eq('ARTICLE'),
            FilterExpression=(Attr('removed').not_exists() | Attr('removed').eq(False)),
            **kwargs
        )

    return resp['Items'], resp.get('LastEvaluatedKey')



def tag_fetch(tag: str, start_key: dict = None, projection_expression: str = None):
    # 1) get page of IDs for this tag
    tag_kwargs = dict(
        KeyConditionExpression=Key('PK').eq(tag),
        FilterExpression=(Attr('removed').not_exists() | Attr('removed').eq(False)),
        Limit=PAGE_SIZE,
        ScanIndexForward=False
    )

    if start_key:
        tag_kwargs['ExclusiveStartKey'] = start_key

    try:
        resp = tag_index.query(**tag_kwargs)
        ids = [item['uniqueId'] for item in resp['Items']]
    except Exception as e:
        print("Error querying tag index:", e)
        ids = []

    # 2) batch‑get the full docs
    try:
        batch = dynamodb.batch_get_item(
            RequestItems={
                'Articles': {
                    'Keys': [{'PK': 'ARTICLE', 'SK': uid} for uid in ids],
                    'ProjectionExpression': projection_expression,
                    'ExpressionAttributeNames': expression_attribute_names
                }
            }
        )
        items = batch['Responses']['Articles']

        next_key = batch.get('LastEvaluatedKey')
        prev_key = _b64(start_key) if start_key else None
    except Exception as e:
        print("Error batch‑getting articles:", e)
        items = []
        next_key = None
        prev_key = None

    return items, _b64(next_key), prev_key


# same GSI or fallback logic as _query_primary_feed, but simplify:
# resp = articles.query(IndexName="removed-index", KeyConditionExpression=Key("removed").eq(0), **asc_kwargs, ProjectionExpression=projection_expression, ExpressionAttributeNames=expression_attribute_names)
# TODO: [LOW PRIORITY] Implement 'removed-index'.

def paginate_backwards(start_key, projection_expression):
    # 1) fetch everything **newer** than the cursor, but in ascending order
    asc_kwargs = {"Limit": PAGE_SIZE + 1, "ScanIndexForward": True}
    try:
        resp = articles_db.query(
            KeyConditionExpression=Key('PK').eq('ARTICLE') & Key('SK').gte(start_key['SK']),
            FilterExpression=(Attr('removed').not_exists() | Attr('removed').eq(False)),
            **asc_kwargs,
            ProjectionExpression=projection_expression,
            ExpressionAttributeNames=expression_attribute_names
        )

        # 2) reverse so newest‑first
        items = list(reversed(resp["Items"]))

        if len(items) > PAGE_SIZE:
            # If we got more than PAGE_SIZE, it means there are still newer articles
            items = items[:-1]

        print(f'[DEBUG] Page size: {PAGE_SIZE}, Items fetched: {len(items)}')

    except Exception as e:
        print("Error querying primary feed for newer articles:", e)
        return [], None, None

    next_key = _b64(start_key) if start_key else None
    prev_key = _b64(resp.get("LastEvaluatedKey"))

    return items, next_key, prev_key

def list_articles(tag: str = None, start_key: dict = None, full_articles: bool = True, direction: str = 'older'):
    """
    ?lastKey=...  → continue after this id
    ?tag=foo      → filter by tag
    """
    projection_expression = '#PK, #SK, content, tags, removed, date_created, description, slug, title, #url, thumbnail' \
        if full_articles else '#PK, #SK, tags, removed, date_created, description, slug, title, #url, thumbnail'

    if tag:
        return tag_fetch(tag=tag, start_key=start_key, projection_expression=projection_expression)
    else:
        # primary feed (not removed)
        try:
            if direction == "older":
                # standard "Older" pagination on descending SK
                items, raw_next = _query_primary_feed(PAGE_SIZE, projection_expression, expression_attribute_names, start_key=start_key)
                next_key = _b64(raw_next)
                prev_key = _b64(start_key) if start_key else None
                return items, next_key, prev_key
            else:  # direction == "newer"
                return paginate_backwards(start_key=start_key, projection_expression=projection_expression)
        except Exception as e:
            print("Error querying primary feed:", e)
            return [], None, None
