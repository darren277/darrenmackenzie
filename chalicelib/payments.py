""""""
# import from AWS Secrets Manager
import os
import json

import boto3
import stripe


def get_secret(secret_name: str):
    region_name = "us-east-1"

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    get_secret_value_response = client.get_secret_value(
        SecretId=secret_name
    )
    secret = get_secret_value_response['SecretString']
    return json.loads(secret)

stripe.api_key = os.environ.get('STRIPE_RESTRICTED_KEY', get_secret('STRIPE_RESTRICTED_KEY')['STRIPE_RESTRICTED_KEY'])
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', get_secret('STRIPE_WEBHOOK_SECRET')['STRIPE_WEBHOOK_SECRET'])


def checkout_session_handler():
    """
        Creates a Stripe Checkout Session and returns the session ID
        """
    # You might parse the request body if you need dynamic prices.
    # For example, if you have multiple products or amounts:
    # data = app.current_request.json_body
    # price_id = data['price_id']

    # For demonstration, let’s just create a session with a fixed price:
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        mode='payment',
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'unit_amount': 1000,  # $10.00
                'product_data': {
                    'name': 'Sample Product'
                },
            },
            'quantity': 1,
        }],
        success_url='https://www.darrenmackenzie.com/success',  # Where to redirect on success
        cancel_url='https://www.darrenmackenzie.com/cancel'  # Where to redirect on cancel
    )

    return {'sessionId': session.id}


def stripe_webhook_handler(payload, sig_header):
    import stripe
    import json
    from chalice import BadRequestError

    endpoint_secret = STRIPE_WEBHOOK_SECRET

    # Verify the signature
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        # Invalid payload
        raise BadRequestError("Invalid payload")
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        raise BadRequestError("Invalid signature")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # For example, retrieve the session details or line items
        # Do something with successful payment
        print("Payment successful for session: ", session['id'])

    # Return a 200 response to acknowledge receipt of the event
    return {}
