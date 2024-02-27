import base64
import email
import logging
import os
import re
from dataclasses import dataclass
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr
from typing import Optional

import boto3
from botocore.exceptions import ClientError


@dataclass
class Config:
    region: str
    incoming_bucket: str
    email_key_prefix: Optional[str]


config = Config(
    region=os.environ["Region"],
    incoming_bucket=os.environ["MailS3Bucket"],
    email_key_prefix=os.environ["MailS3Prefix"],
)

client_s3 = boto3.client("s3")


def get_message_from_s3(message_id):
    if config.email_key_prefix:
        object_path = config.email_key_prefix + "/" + message_id
    else:
        object_path = message_id

    print(f"Getting object path: Bucket={config.incoming_bucket}, Key={object_path}")

    object_http_path = f"http://s3.console.aws.amazon.com/s3/object/{config.incoming_bucket}/{object_path}?region={config.region}"

    # Get the email object from the S3 bucket.
    object_s3 = client_s3.get_object(Bucket=config.incoming_bucket, Key=object_path)
    # Read the content of the message.
    file = object_s3["Body"].read()

    file_dict = {
        "file": file,
        "path": object_http_path,
        "bucket": config.incoming_bucket,
        "key": object_path,
    }

    return file_dict


def tag_object(file_dict):
    separator = ";"

    # Parse the email body.
    mailobject = email.message_from_string(file_dict["file"].decode("utf-8"))

    # Create a new subject line.
    subject = mailobject["Subject"]
    sender = mailobject["From"]
    sender = parseaddr(sender)[1]
    recipient = mailobject["To"]
    recipient = parseaddr(recipient)[1]

    tag_set = {
        "TagSet": [
            {
                "Key": "Subject",
                "Value": base64.b64encode(subject.encode("utf-8")).decode("utf-8"),
            },
            {"Key": "From", "Value": sender},
            {"Key": "To", "Value": recipient},
        ]
    }

    print(f"Tagging with {tag_set}")

    client_s3.put_object_tagging(
        Bucket=file_dict["bucket"], Key=file_dict["key"], Tagging=tag_set
    )

    return tag_set


def lambda_handler(event, context):
    # Get the unique ID of the message. This corresponds to the name of the file
    # in S3.
    message_id = event["Records"][0]["ses"]["mail"]["messageId"]
    print(f"Received message ID {message_id}")

    # Retrieve the file from the S3 bucket.
    file_dict = get_message_from_s3(message_id)

    # Tag the object
    result = tag_object(file_dict)

    print(result)
