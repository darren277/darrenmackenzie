""""""
import json
import os

import boto3
from chalice import Response

from chalicelib.caching import create_compressed_response
from chalicelib.main import get_s3_template


ANIMATIONS_DICT = {
    'my_animation': {
        'title': 'My Animation',
        'animation_type': 'default',
        'view_box': None,
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
        'view_box': '0 0 5118 3596',
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


def load_img_handler(img_url):
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


def animation_page_handler(animation_name, background_image_url, show_path_bool, dot_size, dot_color, image_top_padding, image_bottom_padding):
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
        'animation_type': animation_data.get('animation_type', 'default'),
        'show_path': show_path_bool
    }

    if dot_size:
        template_data.update({'dot_size': dot_size})

    if dot_color:
        template_data.update({'dot_color': dot_color})

    if animation_data.get('view_box', None):
        template_data.update({'view_box': animation_data['view_box']})

    if background_image_url:
        template_data.update({'background_image_url': background_image_url})

        if image_top_padding:
            template_data.update({'top_padding': image_top_padding})

        if image_bottom_padding:
            template_data.update({'bottom_padding': image_bottom_padding})

    html_content = template.render(**template_data)

    return create_compressed_response(html_content)
