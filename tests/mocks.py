"""
Mock implementations of dependencies for testing.
In a real project, you would import these from your actual code.
"""

class Paginator:
    """Mock implementation of Paginator class for testing."""
    
    @classmethod
    def from_query_params(cls, query_params):
        """Create a paginator from query parameters."""
        paginator = cls()
        paginator.query_params = query_params
        paginator.page_size = int(query_params.get('limit', 10))
        paginator.current_page = int(query_params.get('page', 1))
        return paginator
    
    def build_query_kwargs(self, tags=None):
        """Build kwargs for DynamoDB query."""
        kwargs = {
            'IndexName': 'by_date',
            'KeyConditionExpression': 'pk = :pk',
            'ExpressionAttributeValues': {':pk': 'ARTICLE'},
            'Limit': self.page_size,
            'ScanIndexForward': False  # descending order
        }
        
        # Add tag filtering if tags are provided
        if tags:
            kwargs['FilterExpression'] = 'contains(tags, :tag)'
            kwargs['ExpressionAttributeValues'][':tag'] = tags[0]
        
        return kwargs
    
    def update_bounds_from_items(self, items):
        """Update paginator bounds based on returned items."""
        if items:
            # In a real implementation, we'd update internal state
            self.last_evaluated_key = items[-1].get('id')
    
    def next_page(self):
        """Get paginator for next page."""
        next_paginator = Paginator()
        next_paginator.current_page = self.current_page + 1
        next_paginator.page_size = self.page_size
        return next_paginator
    
    def prev_page(self):
        """Get paginator for previous page."""
        if self.current_page <= 1:
            raise ValueError("No previous page")
        
        prev_paginator = Paginator()
        prev_paginator.current_page = self.current_page - 1
        prev_paginator.page_size = self.page_size
        return prev_paginator
    
    def to_query_params(self):
        """Convert paginator state to query parameters."""
        return {
            'page': str(self.current_page),
            'limit': str(self.page_size)
        }


def build_url(base_url, query_params):
    """
    Build a URL with query parameters.
    
    Args:
        base_url (str): Base URL
        query_params (dict): Query parameters
        
    Returns:
        str: URL with query parameters
    """
    if not query_params:
        return base_url
    
    params_str = '&'.join([f"{k}={v}" for k, v in query_params.items()])
    return f"{base_url}?{params_str}"


def create_response_headers(content_type, content):
    """
    Create response headers with appropriate content type and encoding.
    
    Args:
        content_type (str): Content type
        content (str): Content for which to create headers
        
    Returns:
        dict: Response headers
    """
    headers = {
        'Content-Type': content_type,
        'Content-Encoding': 'br'
    }
    
    return headers


def brotli_compress(data):
    """
    Mock implementation of brotli compression.
    
    Args:
        data (bytes): Data to compress
        
    Returns:
        bytes: Compressed data
    """
    # In a real implementation, this would use the brotli library
    return b"compressed-" + data
