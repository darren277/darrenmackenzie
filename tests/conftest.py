import os
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_s3_resource():
    """Fixture for mocking S3 resource."""
    with patch('boto3.resource') as mock_resource:
        # Set up the mock response structure
        mock_s3 = MagicMock()
        mock_obj = MagicMock()
        mock_body = MagicMock()
        
        # Link them together
        mock_resource.return_value = mock_s3
        mock_s3.Object.return_value = mock_obj
        mock_obj.get.return_value = {"Body": mock_body}
        mock_body.read.return_value = b"<html>__THREEJS_VERSION__</html>"
        
        yield mock_resource, mock_s3, mock_obj, mock_body

@pytest.fixture
def mock_dynamo_resource():
    """Fixture for mocking DynamoDB resource."""
    with patch('boto3.resource') as mock_resource:
        # Create the mock table and response
        mock_dynamo = MagicMock()
        mock_table = MagicMock()
        
        # Link them together
        mock_resource.return_value = mock_dynamo
        mock_dynamo.Table.return_value = mock_table
        
        # Default response for get_item
        mock_table.get_item.return_value = {
            'Item': {
                'section': 'website_data',
                'services': [{'name': 'Service 1'}],
                'social': [{'platform': 'Twitter'}],
                'projects': [{'title': 'Project 1'}]
            }
        }
        
        # Default response for query
        mock_table.query.return_value = {
            'Items': [
                {'id': '1', 'title': 'Article 1', 'created': 100},
                {'id': '2', 'title': 'Article 2', 'created': 200}
            ]
        }
        
        yield mock_resource, mock_dynamo, mock_table

@pytest.fixture
def mock_paginator():
    """Fixture for mocking Paginator class."""
    with patch('Paginator.from_query_params') as mock_from_params:
        # Create the mock paginator
        paginator = MagicMock()
        mock_from_params.return_value = paginator
        
        # Set up default behavior
        paginator.page_size = 10
        paginator.current_page = 1
        
        # Set up next_page and prev_page
        next_page = MagicMock()
        prev_page = MagicMock()
        paginator.next_page.return_value = next_page
        paginator.prev_page.return_value = prev_page
        
        # Set up query params
        next_page.to_query_params.return_value = {'cursor': 'next123', 'limit': '10'}
        prev_page.to_query_params.return_value = {'cursor': 'prev123', 'limit': '10'}
        
        # Set up build_query_kwargs
        paginator.build_query_kwargs.return_value = {
            'IndexName': 'by_date',
            'KeyConditionExpression': 'pk = :pk',
            'ExpressionAttributeValues': {':pk': 'ARTICLE'},
            'Limit': 10,
            'ScanIndexForward': False
        }
        
        yield mock_from_params, paginator, next_page, prev_page

@pytest.fixture
def mock_build_url():
    """Fixture for mocking build_url function."""
    with patch('build_url') as mock_url:
        # Default behavior
        mock_url.side_effect = lambda base, params: f"{base}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        yield mock_url

@pytest.fixture
def mock_app_request():
    """Fixture for mocking app.current_request."""
    with patch('app.current_request') as mock_request:
        # Default query params
        mock_request.query_params = {'limit': '10'}
        yield mock_request

@pytest.fixture
def mock_environment():
    """Fixture for setting up environment variables."""
    # Store original env vars
    original_env = {}
    test_vars = {
        'BUCKET_NAME': 'test-bucket',
        'HOME_TABLE': 'test-home-table',
        'ARTICLE_LIST_TABLE': 'test-article-table'
    }
    
    # Save original values and set test values
    for key, value in test_vars.items():
        if key in os.environ:
            original_env[key] = os.environ[key]
        os.environ[key] = value
    
    yield
    
    # Restore original values
    for key in test_vars:
        if key in original_env:
            os.environ[key] = original_env[key]
        else:
            del os.environ[key]

# This lets you run the tests with coverage reporting
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
