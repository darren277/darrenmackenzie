from decimal import Decimal
import time

class Paginator:
    def __init__(
        self,
        current_page=1,
        page_size=5,
        lower_bound=0,       # the smallest 'created' we allow (for descending, oldest possible)
        upper_bound=None,    # the largest 'created' we allow (for descending, newest possible)
    ):
        """
        :param current_page: which page number (1-based)
        :param page_size: items per page
        :param lower_bound: items cannot be smaller than this in 'created'
        :param upper_bound: items cannot be larger than this in 'created'
        """
        self.current_page = current_page
        self.page_size = page_size

        # If upper_bound not given, set it to "now" in milliseconds
        if upper_bound is None:
            upper_bound = int(time.time() * 1000)

        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

        self.initial_upper_bound = upper_bound  # store the "original" upper bound

        # Once we query, we will fill these in:
        self.page_min_created = None  # the smallest 'created' in the current result
        self.page_max_created = None  # the largest 'created' in the current result

    @classmethod
    def from_query_params(cls, qp: dict) -> "Paginator":
        """
        Construct a Paginator from query params. 
        We expect e.g. ?page=2&limit=5&lb=1000&ub=2000
        If not provided, we use defaults.
        """
        page = int(qp.get('page', '1'))
        limit = int(qp.get('limit', '5'))

        lb = qp.get('lb', '0')
        ub = qp.get('ub')  # if not present, we do 'None'

        if lb.isdigit():
            lb = int(lb)
        else:
            lb = 0

        if ub is not None and ub.isdigit():
            ub = int(ub)
        else:
            ub = None  # will default to now

        return cls(
            current_page=page,
            page_size=limit,
            lower_bound=lb,
            upper_bound=ub
        )

    def to_query_params(self) -> dict:
        """
        Convert this Paginator's state back to a dict for building a query string.
        """
        d = {
            "page": str(self.current_page),
            "limit": str(self.page_size),
            "lb": str(self.lower_bound),
            "ub": str(self.upper_bound)
        }
        return d

    def build_query_kwargs(self, tags=None):
        """
        Create the arguments for a DynamoDB Query in descending order with a 'BETWEEN' condition:
          created BETWEEN :lb AND :ub
        We'll do 'ScanIndexForward=False' to get items from largest to smallest.
        """
        key_condition = "type_of_article = :t AND created BETWEEN :lb AND :ub"
        expr_vals = {
            ":t": "blog",
            ":lb": Decimal(self.lower_bound),
            ":ub": Decimal(self.upper_bound),
        }

        kwargs = {
            "KeyConditionExpression": key_condition,
            "ExpressionAttributeValues": expr_vals,
            "ScanIndexForward": False,
            "Limit": self.page_size
        }

        if tags:
            # Filter by first tag for demonstration
            # (In production, consider a GSI if you want to query by tag at scale)
            kwargs["FilterExpression"] = "contains(tags, :tagVal)"
            kwargs["ExpressionAttributeValues"][":tagVal"] = tags[0]

        return kwargs

    def update_bounds_from_items(self, items: list):
        """
        After we retrieve items (descending), the item at index 0 has the largest 'created',
        and the item at index -1 has the smallest 'created'. We'll store those in
        self.page_max_created and self.page_min_created for easy reference.
        """
        if not items:
            return

        self.page_max_created = items[0]["created"]
        self.page_min_created = items[-1]["created"]

    def next_page(self):
        """
        Return a new Paginator for the "next page" (older items).
        In descending order, "next page" means 'upper_bound' becomes (current page's min_created - 1).
        So we exclude any items >= the smallest item on the current page.
        """
        p = Paginator(
            current_page=self.current_page + 1,
            page_size=self.page_size,
            lower_bound=self.lower_bound,
            upper_bound=self.page_min_created - 1
        )
        return p

    def prev_page(self):
        """
        Return a new Paginator for the "previous page" (newer items).
        In descending order, "previous page" means 'lower_bound' becomes (current page's max_created + 1).
        So we exclude any items <= the largest item on the current page.
        """
        if self.page_max_created is None:
            raise ValueError("Cannot get previous page without first querying items")
        p = Paginator(
            current_page=self.current_page - 1,
            page_size=self.page_size,
            lower_bound=self.page_max_created + 1,
            #upper_bound=self.upper_bound
            upper_bound=self.initial_upper_bound  # reset to original upper bound
        )
        return p
