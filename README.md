# darrenmackenzie

## How to Use

1. `. venv/Scripts/activate`.
2. `chalice deploy`.

## Performance

### Brotli

This application uses Brotli to compress responses.

### Caching

#### CloudFront

It is currently returning `Miss from cloudfront` for all requests. I'm still not sure why exactly. However, API Gateway level caching seems to be working at least.

#### API Gateway

Needs to be enabled from the web UI at the moment. See image below:

![API Gateway Cache](APIGatewayCaching.png)
