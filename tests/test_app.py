import os
import json
import pytest
from unittest.mock import patch, MagicMock, Mock
from decimal import Decimal
from io import BytesIO

from app import get_menu_items, get_s3_template, get_website_data, build_paginator_from_query_params
from app import query_articles, build_pagination_urls, determine_page_status, create_compressed_response
from app import script_template


# For simplicity in this example, let's assume DEFAULT_PAGE_LIMIT is defined
DEFAULT_PAGE_LIMIT = 10

#########################################
# Test get_menu_items
#########################################
def test_get_menu_items():
    """Test that get_menu_items returns the expected menu structure."""
    menu = get_menu_items()
    
    # Verify structure
    assert isinstance(menu, list)
    assert len(menu) == 5  # Assuming 5 menu items based on the original code
    
    # Verify content
    expected_titles = ['Home', 'About', 'Services', 'Work', 'Blog']
    for i, item in enumerate(menu):
        assert item['title'] == expected_titles[i]
        assert 'url' in item

#########################################
# Test get_s3_template
#########################################
@patch('app.boto3')
@patch('app.s3_env')
def test_get_s3_template(mock_s3_env, mock_boto3):
    """Test retrieving and processing the HTML template from S3."""
    # Setup boto3 resource mock
    mock_s3 = MagicMock()
    mock_boto3.resource.return_value = mock_s3
    
    mock_object = MagicMock()
    mock_s3.Object.return_value = mock_object
    
    mock_body = MagicMock()
    mock_body.read.return_value = b"<html>__THREEJS_VERSION__</html>"
    mock_object.get.return_value = {"Body": mock_body}
    
    # Setup s3_env mock
    mock_template = MagicMock()
    mock_s3_env.from_string.return_value = mock_template
    
    # Call the function
    from app import get_s3_template
    result = get_s3_template('test-bucket')
    
    # Verify boto3 was called correctly
    mock_boto3.resource.assert_called_once_with('s3')
    mock_s3.Object.assert_called_once_with('test-bucket', 'frontend/index.html')
    mock_object.get.assert_called_once()
    
    # Verify s3_env was called correctly
    mock_s3_env.from_string.assert_called_once_with("<html>0.172.0</html>")
    
    # Verify result
    assert result == mock_template

#########################################
# Test get_website_data
#########################################
@patch('boto3.resource')
def test_get_website_data(mock_boto3_resource):
    """Test retrieving website data from DynamoDB."""
    # Setup mocks
    mock_dynamo = MagicMock()
    mock_boto3_resource.return_value = mock_dynamo
    
    mock_table = MagicMock()
    mock_dynamo.Table.return_value = mock_table
    
    expected_data = {
        'section': 'website_data',
        'services': [{'name': 'Service 1'}],
        'social': [{'platform': 'Twitter'}],
        'projects': [{'title': 'Project 1'}]
    }
    
    mock_table.get_item.return_value = {'Item': expected_data}
    
    # Call the function
    result = get_website_data('test-table')
    
    # Verify DynamoDB was called correctly
    mock_dynamo.Table.assert_called_once_with('test-table')
    mock_table.get_item.assert_called_once_with(Key={'section': 'website_data'})
    
    # Verify result
    assert result == expected_data

#########################################
# Test build_paginator_from_query_params
#########################################
def test_build_paginator_from_query_params():
    """Test building a paginator from query parameters."""
    # Setup mock
    mock_paginator = MagicMock()
    mock_paginator_class = MagicMock(return_value=mock_paginator)
    
    query_params = {'limit': '5', 'cursor': 'abc123'}
    
    with patch('Paginator.from_query_params', mock_paginator_class):
        result = build_paginator_from_query_params(query_params)
    
    # Verify Paginator was created correctly
    mock_paginator_class.assert_called_once_with(query_params)
    assert mock_paginator.page_size == 5
    assert result == mock_paginator

def test_build_paginator_from_query_params_default_limit():
    """Test building a paginator with default page limit."""
    # Setup mock
    mock_paginator = MagicMock()
    mock_paginator_class = MagicMock(return_value=mock_paginator)
    
    query_params = {'cursor': 'abc123'}  # No limit specified
    
    with patch('Paginator.from_query_params', mock_paginator_class):
        result = build_paginator_from_query_params(query_params)
    
    # Verify default limit was used
    mock_paginator_class.assert_called_once_with(query_params)
    assert mock_paginator.page_size == DEFAULT_PAGE_LIMIT
    assert result == mock_paginator

#########################################
# Test query_articles
#########################################
@patch('boto3.resource')
def test_query_articles(mock_boto3_resource):
    """Test querying articles from DynamoDB with pagination."""
    # Setup mocks
    mock_dynamo = MagicMock()
    mock_boto3_resource.return_value = mock_dynamo
    
    mock_table = MagicMock()
    mock_dynamo.Table.return_value = mock_table
    
    mock_paginator = MagicMock()
    mock_paginator.build_query_kwargs.return_value = {'IndexName': 'by_date', 'Limit': 10}
    
    expected_items = [{'id': '1', 'title': 'Article 1'}, {'id': '2', 'title': 'Article 2'}]
    mock_table.query.return_value = {"Items": expected_items}
    
    # Call the function
    result = query_articles('test-table', mock_paginator, tags=['tag1'])
    
    # Verify DynamoDB was called correctly
    mock_dynamo.Table.assert_called_once_with('test-table')
    mock_paginator.build_query_kwargs.assert_called_once_with(tags=['tag1'])
    mock_table.query.assert_called_once_with(IndexName='by_date', Limit=10)
    
    # Verify result
    assert result == expected_items
    mock_paginator.update_bounds_from_items.assert_called_once_with(expected_items)

#########################################
# Test build_pagination_urls
#########################################
def test_build_pagination_urls_with_next_and_prev():
    """Test building URLs for next and previous pages when both exist."""
    # Setup mocks
    mock_paginator = MagicMock()
    mock_paginator.page_size = 10
    mock_paginator.current_page = 2
    
    mock_next_paginator = MagicMock()
    mock_next_paginator.to_query_params.return_value = {'cursor': 'next123', 'limit': '10'}
    mock_paginator.next_page.return_value = mock_next_paginator
    
    mock_prev_paginator = MagicMock()
    mock_prev_paginator.to_query_params.return_value = {'cursor': 'prev123', 'limit': '10'}
    mock_paginator.prev_page.return_value = mock_prev_paginator
    
    page_of_articles = [{'id': i} for i in range(10)]  # 10 items = full page
    base_url = "https://example.com/"
    tags_param = "tag1,tag2"
    
    with patch('build_url') as mock_build_url:
        mock_build_url.side_effect = [
            "https://example.com/?cursor=next123&limit=10&tags=tag1,tag2",
            "https://example.com/?cursor=prev123&limit=10&tags=tag1,tag2"
        ]
        
        next_url, prev_url = build_pagination_urls(mock_paginator, page_of_articles, base_url, tags_param)
    
    # Verify results
    assert next_url == "https://example.com/?cursor=next123&limit=10&tags=tag1,tag2"
    assert prev_url == "https://example.com/?cursor=prev123&limit=10&tags=tag1,tag2"
    
    # Verify URL building
    assert mock_build_url.call_count == 2

def test_build_pagination_urls_no_next_page():
    """Test building URLs when there is no next page."""
    # Setup mocks
    mock_paginator = MagicMock()
    mock_paginator.page_size = 10
    mock_paginator.current_page = 2
    
    mock_prev_paginator = MagicMock()
    mock_prev_paginator.to_query_params.return_value = {'cursor': 'prev123', 'limit': '10'}
    mock_paginator.prev_page.return_value = mock_prev_paginator
    
    page_of_articles = [{'id': i} for i in range(5)]  # 5 items < page size, so no next page
    base_url = "https://example.com/"
    
    with patch('build_url') as mock_build_url:
        mock_build_url.return_value = "https://example.com/?cursor=prev123&limit=10"
        
        next_url, prev_url = build_pagination_urls(mock_paginator, page_of_articles, base_url)
    
    # Verify results
    assert next_url is None
    assert prev_url == "https://example.com/?cursor=prev123&limit=10"
    
    # Verify URL building was called only once (for prev)
    mock_build_url.assert_called_once()

def test_build_pagination_urls_no_prev_page():
    """Test building URLs when there is no previous page."""
    # Setup mocks
    mock_paginator = MagicMock()
    mock_paginator.page_size = 10
    mock_paginator.current_page = 1  # First page, so no prev
    
    mock_next_paginator = MagicMock()
    mock_next_paginator.to_query_params.return_value = {'cursor': 'next123', 'limit': '10'}
    mock_paginator.next_page.return_value = mock_next_paginator
    
    page_of_articles = [{'id': i} for i in range(10)]  # Full page
    base_url = "https://example.com/"
    
    with patch('build_url') as mock_build_url:
        mock_build_url.return_value = "https://example.com/?cursor=next123&limit=10"
        
        next_url, prev_url = build_pagination_urls(mock_paginator, page_of_articles, base_url)
    
    # Verify results
    assert next_url == "https://example.com/?cursor=next123&limit=10"
    assert prev_url is None
    
    # Verify mock usage
    mock_paginator.prev_page.assert_not_called()

#########################################
# Test determine_page_status
#########################################
def test_determine_page_status_first_page():
    """Test determining page status for first page."""
    page_of_articles = [
        {'created': 100},
        {'created': 200},
        {'created': 150}
    ]
    query_params = {}  # Empty for first page
    
    with patch('Decimal', lambda x: x):  # Mock Decimal to return input unchanged
        is_first_page, newest_timestamp = determine_page_status(page_of_articles, query_params)
    
    assert is_first_page is True
    assert newest_timestamp == 200  # Max value

def test_determine_page_status_with_newest_timestamp():
    """Test determining page status with a provided newest timestamp."""
    page_of_articles = [
        {'created': 100},
        {'created': 200},
        {'created': 300}
    ]
    query_params = {'newestTimestamp': 400}
    
    with patch('Decimal', lambda x: x):  # Mock Decimal to return input unchanged
        is_first_page, newest_timestamp = determine_page_status(page_of_articles, query_params)
    
    assert is_first_page is False  # Not first page
    assert newest_timestamp == 400  # From query params

def test_determine_page_status_includes_newest():
    """Test when current page includes the newest timestamp."""
    page_of_articles = [
        {'created': 100},
        {'created': 400},  # This matches the newest timestamp
        {'created': 300}
    ]
    query_params = {'newestTimestamp': 400}
    
    with patch('Decimal', lambda x: x):  # Mock Decimal to return input unchanged
        is_first_page, newest_timestamp = determine_page_status(page_of_articles, query_params)
    
    assert is_first_page is True  # Should be true because newest article is on this page
    assert newest_timestamp == 400

def test_determine_page_status_empty_articles():
    """Test determining page status with no articles."""
    page_of_articles = []
    query_params = {'cursor': 'abc123'}
    
    is_first_page, newest_timestamp = determine_page_status(page_of_articles, query_params)
    
    assert is_first_page is False
    assert newest_timestamp == 0

#########################################
# Test create_compressed_response
#########################################
def test_create_compressed_response():
    """Test creating a compressed HTTP response."""
    html_content = "<html><body>Test</body></html>"
    compressed_data = b"compressed-data"
    expected_headers = {"Content-Type": "text/html; charset=UTF-8", "Content-Encoding": "br"}
    
    with patch('brotli_compress', return_value=compressed_data) as mock_compress:
        with patch('create_response_headers', return_value=expected_headers) as mock_headers:
            response = create_compressed_response(html_content)
    
    # Verify compression
    mock_compress.assert_called_once_with(html_content.encode('utf-8'))
    mock_headers.assert_called_once_with('text/html; charset=UTF-8', html_content)
    
    # Verify response
    assert response.body == compressed_data
    assert response.headers == expected_headers
    assert response.status_code == 200

#########################################
# Test script_template (main function)
#########################################
@patch('app.current_request')
def test_script_template_success(mock_current_request):
    """Test the main endpoint function's happy path."""
    # Setup environment variables
    os.environ['BUCKET_NAME'] = 'test-bucket'
    os.environ['HOME_TABLE'] = 'test-home-table'
    os.environ['ARTICLE_LIST_TABLE'] = 'test-article-table'
    
    # Setup request mock
    mock_current_request.query_params = {'limit': '5', 'tags': 'tag1,tag2'}
    
    # Setup all the helper function mocks
    mock_menu = [{'title': 'Home', 'url': '#'}]
    mock_template = MagicMock()
    mock_template.render.return_value = "<html>Rendered</html>"
    mock_website_data = {'services': [], 'social': [], 'projects': []}
    mock_articles = [{'id': '1', 'title': 'Article 1', 'created': 100}]
    mock_response = MagicMock()
    
    with patch('get_menu_items', return_value=mock_menu) as mock_get_menu, \
         patch('build_paginator_from_query_params') as mock_build_paginator, \
         patch('get_s3_template', return_value=mock_template) as mock_get_template, \
         patch('get_website_data', return_value=mock_website_data) as mock_get_data, \
         patch('query_articles', return_value=mock_articles) as mock_query, \
         patch('build_pagination_urls', return_value=('next', 'prev')) as mock_build_urls, \
         patch('determine_page_status', return_value=(False, 100)) as mock_determine, \
         patch('create_compressed_response', return_value=mock_response) as mock_create_response:
        
        result = script_template()
    
    # Verify all helpers were called with correct arguments
    mock_get_menu.assert_called_once()
    mock_build_paginator.assert_called_once_with({'limit': '5', 'tags': 'tag1,tag2'})
    mock_get_template.assert_called_once_with('test-bucket')
    mock_get_data.assert_called_once_with('test-home-table')
    mock_query.assert_called_once()  # Args will vary based on paginator mock
    mock_build_urls.assert_called_once()  # Args will vary based on paginator mock
    mock_determine.assert_called_once_with(mock_articles, {'limit': '5', 'tags': 'tag1,tag2'})
    
    # Verify template rendering
    mock_template.render.assert_called_once()
    template_args = mock_template.render.call_args[1]
    assert template_args['services'] == []
    assert template_args['articles'] == mock_articles
    assert template_args['menu'] == mock_menu
    assert template_args['nextPageUrl'] == 'next'
    assert template_args['prevPageUrl'] == 'prev'
    assert template_args['firstPage'] is False
    assert template_args['newestTimestamp'] == 100
    
    # Verify response creation and return
    mock_create_response.assert_called_once_with("<html>Rendered</html>")
    assert result == mock_response

def test_script_template_paginator_error(mock_current_request):
    """Test handling of paginator errors."""
    # Setup request mock
    mock_current_request.query_params = {'invalid': 'value'}
    
    # Setup mock to raise an exception
    with patch('build_paginator_from_query_params', side_effect=Exception("Paginator error")) as mock_build:
        with patch('Response') as mock_response_class:
            mock_response = MagicMock()
            mock_response_class.return_value = mock_response
            
            result = script_template()
    
    # Verify error response
    mock_response_class.assert_called_once_with("Paginator error", status_code=400)
    assert result == mock_response

# Add more tests for other error paths in script_template
# (DynamoDB query errors, pagination URL building errors, etc.)
