include .env

PARAMS={"EnableAcceptEncodingBrotli": true, "EnableAcceptEncodingGzip": true, "HeadersConfig": { "HeaderBehavior": "none" }, "CookiesConfig": { "CookieBehavior": "none" }, "QueryStringsConfig": { "QueryStringBehavior": "all" }}

cf-cache-policy:
	aws cloudfront create-cache-policy --cache-policy-config '{"Name": "ForwardAllQueryStringsPolicy", "DefaultTTL": 600, "MaxTTL": 86400, "MinTTL": 0, "ParametersInCacheKeyAndForwardedToOrigin": $(PARAMS)}'

cf-fwd-q-strings:
	aws cloudfront create-origin-request-policy --origin-request-policy-config '{"Name": "ForwardAllQueryStringsOriginPolicy", "HeadersConfig": { "HeaderBehavior": "none" }, "CookiesConfig": { "CookieBehavior": "none" }, "QueryStringsConfig": { "QueryStringBehavior": "all" }}'

cf-get-dist-id:
	aws cloudfront list-distributions --query "DistributionList.Items[*].[Id,DomainName]"


cf-get-dist-config:
	aws cloudfront get-distribution-config --id $(DISTRIBUTION_ID) > cf-config.json

cf-etag:
	aws cloudfront get-distribution-config --id $(DISTRIBUTION_ID) --query "ETag" --output text > etag.txt

cf-update:
	aws cloudfront update-distribution --id $(DISTRIBUTION_ID) --if-match $(ETAG) --distribution-config file://cf-config.json


cf-check:
	aws cloudfront get-distribution --id $(DISTRIBUTION_ID) --query "Distribution.DistributionConfig.DefaultCacheBehavior.CachePolicyId"


cf-check-policy:
	aws cloudfront get-cache-policy --id $(POLICY_ID)

cf-check-distribution:
	aws cloudfront get-distribution --id $(DISTRIBUTION_ID)


cf-invalidate-all:
	aws cloudfront create-invalidation --distribution-id $(DISTRIBUTION_ID) --paths "/*"


firehose-role:
	aws iam create-role --role-name FirehoseS3Role --assume-role-policy-document file://firehose-trust-policy.json

firehose:
	aws firehose create-delivery-stream --delivery-stream-name CloudFrontLogs --s3-destination-configuration file://s3-config.json

KINESIS_STREAM_CONFIG={"RoleARN": "arn:aws:iam::$(AWS_ACCOUNT_ID):role/$(FIREHOSE_ROLE)", "StreamARN": "arn:aws:kinesis:$(AWS_REGION):$(AWS_ACCOUNT_ID):stream/CloudFrontLogs"}

create-log:
	aws cloudfront create-realtime-log-config --name "CloudFrontRealTimeLog" --sampling-rate 100 --fields "timestamp" "c-ip" "cs-uri-stem" "sc-status" "x-edge-detailed-result-type" --end-points '[{"StreamType": "Kinesis", "KinesisStreamConfig": $(KINESIS_STREAM_CONFIG)}]'



test:
	pytest -v tests/ --cov=app
