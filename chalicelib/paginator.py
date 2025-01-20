from decimal import Decimal
import json

class Paginator:
    def __init__(
        self,
        current_page: int = 1,
        min_created: int = None,
        max_created: int = None,
        page_size: int = 10,
        order: str = "desc"
    ):
        """
        :param current_page: 1-based page number (for display)
        :param min_created: the smallest 'created' on this page (descending)
        :param max_created: the largest 'created' on this page (descending)
        :param page_size: how many items per page
        :param order: "asc" or "desc"
        """
        self.current_page = current_page
        self.min_created = min_created
        self.max_created = max_created
        self.page_size = page_size
        self.order = order.lower()

    @classmethod
    def from_query_params(cls, qp: dict) -> "Paginator":
        """
        Factory that reads query params (strings) and returns a Paginator object.
        """
        # Try to parse out the paginationState param if you want to store it all in JSON,
        # or parse individual params: current_page, min_created, max_created, etc.
        
        # Example: parse each param individually
        current_page = int(qp.get("page", "1"))
        page_size = int(qp.get("limit", "10"))
        min_created = qp.get("minCreated")
        max_created = qp.get("maxCreated")
        order = qp.get("order", "desc")

        # Convert to int if present
        if min_created is not None:
            min_created = int(min_created)
        if max_created is not None:
            max_created = int(max_created)

        return cls(
            current_page=current_page,
            min_created=min_created,
            max_created=max_created,
            page_size=page_size,
            order=order
        )

    def to_query_params(self) -> dict:
        """
        Serialize the paginator fields back into a dict for query params.
        """
        d = {
            "page": str(self.current_page),
            "limit": str(self.page_size),
            "order": self.order
        }
        if self.min_created is not None:
            d["minCreated"] = str(self.min_created)
        if self.max_created is not None:
            d["maxCreated"] = str(self.max_created)
        return d

    def build_query_kwargs(self, table_name: str, tags=None):
        """
        Build the DynamoDB query arguments for the *current* page
        based on min_created, max_created, order, etc.
        
        For descending order ("desc"):
          - If we have no min/max, default to "created < now".
          - If we do have minCreated and maxCreated, we might do a BETWEEN or < or > logic, etc.

        This is just an example. You can get more advanced with "BETWEEN" or multiple bounds.
        """

        # We'll do a simple descending example:
        #  - If no max_created: treat as first page => created < current time
        #  - If max_created is present: created < max_created
        #  - We'll set ScanIndexForward=False for descending
        #  - We'll optionally handle tags

        import boto3
        from boto3.dynamodb.conditions import Key, Attr
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)

        expression_values = {":type_of_article": "blog"}
        key_condition = "type_of_article = :type_of_article"
        
        # Example: If we have max_created, we do "AND created < :maxVal"
        # for the next chunk in descending order
        if self.max_created:
            key_condition += " AND created < :maxVal"
            expression_values[":maxVal"] = Decimal(self.max_created)
        else:
            # If no max_created, let's assume "created < now"
            import time
            now_millis = int(time.time() * 1000)
            key_condition += " AND created < :maxVal"
            expression_values[":maxVal"] = Decimal(now_millis)

        kwargs = {
            "KeyConditionExpression": key_condition,
            "ExpressionAttributeValues": expression_values,
            "ScanIndexForward": False,  # descending
            "Limit": self.page_size
        }

        if tags:
            # Filter by first tag for demonstration
            # (In production, consider a GSI if you want to query by tag at scale)
            kwargs["FilterExpression"] = "contains(tags, :tagVal)"
            kwargs["ExpressionAttributeValues"][":tagVal"] = tags[0]

        return table, kwargs

    def update_bounds_from_items(self, items: list):
        """
        After retrieving items from DynamoDB in descending order, 
        update self.min_created and self.max_created so we can 
        build 'next page' or 'previous page' links.
        
        Typically the item with the largest 'created' is items[0] in descending order.
        The item with the smallest 'created' is items[-1].
        """
        if not items:
            return

        # largest is first if descending
        self.max_created = items[0]["created"]
        # smallest is last
        self.min_created = items[-1]["created"]

    def next_page(self):
        """
        Return a *new* Paginator object representing the next page 
        (i.e., older items in descending order).
        
        For descending order, "next page" usually means "created < minCreated" if you do single-bound queries.
        But if you're storing the bounding in max_created, you might shift it, etc.
        
        Here, we assume the next page’s max_created = self.min_created 
        (i.e. "pull anything older than the current page's oldest item").
        """
        p = Paginator(
            current_page=self.current_page + 1,
            page_size=self.page_size,
            order=self.order
        )
        # If we want "older than min_created," store that as "max_created" in the next Paginator
        p.max_created = self.min_created
        return p

    def prev_page(self):
        """
        Return a *new* Paginator object representing the previous page 
        (i.e., newer items in descending order).
        
        For single-bound queries, "previous page" means "created > max_created" or a bounded approach.
        But let's keep it simple and say we just store the previous bound in a stack or you pass it in from memory.
        """
        p = Paginator(
            current_page=self.current_page - 1,
            page_size=self.page_size,
            order=self.order
        )
        # If we want "newer than max_created," we might store that as some field. 
        # But for single-bound, we only have "max_created" as a 'ceiling'.
        # 
        # We *could* do a separate field in the Paginator for "minVal" vs. "maxVal", etc.
        # For demonstration, let's just say we do "created > self.max_created."
        # That might need a different KeyCondition or a second boundary in build_query_kwargs.
        # 
        # In a real scenario, you might store more state or do a more advanced approach.
        # 
        # This is just to illustrate the idea:
        p.newer_than = self.max_created  # you'd have to handle this in build_query_kwargs
        return p
