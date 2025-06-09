""""""
import datetime
import hashlib

import brotli
from chalice import Response

APP_NAME = 'darrenmackenzie'


# Cache for 24 hours
CACHE_CONTROL_ONE_DAY = 'public, s-maxage=86400, max-age=86400'

# Cache for 1 week
CACHE_CONTROL_ONE_WEEK = 'public, s-maxage=604800, max-age=604800'

# Cache for 1 hour
CACHE_CONTROL_ONE_HOUR = 'public, s-maxage=3600, max-age=3600'

# Cache for 1 minute
CACHE_CONTROL_ONE_MINUTE = 'public, s-maxage=60, max-age=60'


def load_cache_control_params():
    """
    Load cache control parameters from AWS Parameter Store.
    Returns a dictionary with cache control settings for different content types.
    """
    import boto3
    from botocore.exceptions import ClientError

    # Initialize parameter store client
    ssm = boto3.client('ssm')

    # Define parameter names (you can prefix these with your application name if needed)
    param_names = [
        f'/{APP_NAME}_cache-control-duration-html',
        f'/{APP_NAME}_cache-control-duration-css-and-js',
        f'/{APP_NAME}_cache-control-duration-json',
        f'/{APP_NAME}_cache-control-duration-fallback'
    ]

    param_names_conversion_dict = {
        f'/{APP_NAME}_cache-control-duration-html': 'HTML_CACHE_CONTROL_DURATION',
        f'/{APP_NAME}_cache-control-duration-css-and-js': 'CSS_AND_JS_CACHE_CONTROL_DURATION',
        f'/{APP_NAME}_cache-control-duration-json': 'JSON_CACHE_CONTROL_DURATION',
        f'/{APP_NAME}_cache-control-duration-fallback': 'FALLBACK_CACHE_CONTROL_DURATION'
    }

    # Initialize result dictionary with defaults
    params = {
        'HTML_CACHE_CONTROL_DURATION': 'DAY',
        'CSS_AND_JS_CACHE_CONTROL_DURATION': 'WEEK',
        'JSON_CACHE_CONTROL_DURATION': 'HOUR',
        'FALLBACK_CACHE_CONTROL_DURATION': 'MINUTE'
    }

    try:
        # Get parameters in a single API call (more efficient)
        response = ssm.get_parameters(
            Names=param_names,
            WithDecryption=False  # Set to True if your parameters are encrypted
        )

        # Process found parameters
        for param in response['Parameters']:
            param_name = param['Name']
            param_value = param['Value']

            # Update the params dictionary with the value
            if param_name in param_names_conversion_dict:
                params[param_names_conversion_dict[param_name]] = param_value
                print(f"Loaded parameter: {param_name} = {param_value}")
            else:
                print(f"Warning: Unexpected parameter name {param_name} found.")

        # Log missing parameters if any
        if response['InvalidParameters']:
            print(f"Warning: Could not find these parameters: {response['InvalidParameters']}")

    except ClientError as e:
        print(f"Error accessing Parameter Store: {e}")
        # Continue with defaults if there's an error

    return params


cache_control_values_dict = dict(
    DAY=CACHE_CONTROL_ONE_DAY,
    WEEK=CACHE_CONTROL_ONE_WEEK,
    HOUR=CACHE_CONTROL_ONE_HOUR,
    MINUTE=CACHE_CONTROL_ONE_MINUTE
)

cache_control_params = load_cache_control_params()

CACHE_CONTROL_DICT = dict(
    HTML_CACHE_CONTROL_DURATION=cache_control_values_dict.get(
        cache_control_params.get('HTML_CACHE_CONTROL_DURATION', 'DAY'), CACHE_CONTROL_ONE_MINUTE),
    CSS_AND_JS_CACHE_CONTROL_DURATION=cache_control_values_dict.get(
        cache_control_params.get('CSS_AND_JS_CACHE_CONTROL_DURATION', 'WEEK'), CACHE_CONTROL_ONE_MINUTE),
    JSON_CACHE_CONTROL_DURATION=cache_control_values_dict.get(
        cache_control_params.get('JSON_CACHE_CONTROL_DURATION', 'HOUR'), CACHE_CONTROL_ONE_MINUTE),
    FALLBACK_CACHE_CONTROL_DURATION=cache_control_values_dict.get(
        cache_control_params.get('FALLBACK_CACHE_CONTROL_DURATION', 'MINUTE'), CACHE_CONTROL_ONE_MINUTE)
)

print("DEBUGGING CACHE CONTROL PARAMS:", cache_control_params, CACHE_CONTROL_DICT)


def brotli_compress(data):
    return brotli.compress(data)


def create_response_headers(content_type: str, content: str):
    try:
        etag_value = hashlib.md5(content).hexdigest()
    except TypeError:
        etag_value = hashlib.md5(content.encode('utf-8')).hexdigest()

    last_modified = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')

    if content_type == 'text/html' or content_type == 'text/html; charset=UTF-8':
        cache_control = CACHE_CONTROL_DICT['HTML_CACHE_CONTROL_DURATION']
    elif content_type == 'application/json':
        cache_control = CACHE_CONTROL_DICT['JSON_CACHE_CONTROL_DURATION']
    elif content_type in ['text/css', 'application/javascript']:
        cache_control = CACHE_CONTROL_DICT['CSS_AND_JS_CACHE_CONTROL_DURATION']
    else:
        cache_control = CACHE_CONTROL_DICT['FALLBACK_CACHE_CONTROL_DURATION']

    return {
        'Content-Type': content_type,
        'Content-Encoding': 'br',
        'Cache-Control': cache_control,
        'ETag': etag_value,
        'Last-Modified': last_modified
    }


def create_compressed_response(html_content, skip_caching=False):
    """Create a compressed HTTP response."""
    # NOTE that caching fucks with pagination, so we will be disabling it in the case of the home page endpoint.

    compressed_html = brotli_compress(html_content.encode('utf-8'))

    headers = create_response_headers('text/html; charset=UTF-8', html_content) if not skip_caching else {
        'Content-Type': 'text/html; charset=UTF-8',
        'Content-Encoding': 'br',
        'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '0'
    }

    return Response(
        body=compressed_html,
        headers=headers,
        status_code=200
    )
