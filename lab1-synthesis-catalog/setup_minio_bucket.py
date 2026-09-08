import json
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin123",
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)

BUCKET = "synthesis-media"

existing = [b["Name"] for b in s3.list_buckets()["Buckets"]]
if BUCKET not in existing:
    s3.create_bucket(Bucket=BUCKET)
    print(f"Bucket '{BUCKET}' создан")
else:
    print(f"Bucket '{BUCKET}' уже существует")

policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{BUCKET}/*"],
        }
    ],
}

s3.put_bucket_policy(Bucket=BUCKET, Policy=json.dumps(policy))
print("Публичный доступ на чтение (GetObject) выставлен")
