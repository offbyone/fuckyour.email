import base64
import email
import email.message
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Any, Generator

import bleach
import boto3
from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Page, Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

BUCKET_NAME = "mail.fuckyour.email"
PREFIX = "email/"


def inbox(request: HttpRequest) -> HttpResponse:
    context = {"emails": get_bucket_messages(request)}
    return render(request, "fye/inbox.html", context)


def message(request: HttpRequest, message_id: str) -> HttpResponse:
    if request.method == "GET":
        context = {"email": get_email(request, message_id)}
        return render(request, "fye/message.html", context)
    elif request.method == "DELETE":
        delete_email(request, message_id)
        return HttpResponse("")


@dataclass
class MessageEntry:
    message_id: str
    sender: str
    subject: str
    last_modified: datetime


@dataclass
class Message:
    entry: MessageEntry
    message: email.message.Message
    content: str


def get_email(request: HttpRequest, message_id: str) -> Message:
    s3_client = boto3.client(
        "s3",
    )
    response = s3_client.get_object(Bucket=BUCKET_NAME, Key=message_id)
    print(response)
    message_data = response["Body"].read()
    parsed = email.message_from_bytes(message_data)
    tags = format_tags(fetch_tags(s3_client, message_id))
    entry = MessageEntry(
        message_id=message_id,
        sender=tags["From"],
        subject=tags["Subject"],
        last_modified=response["LastModified"],
    )
    return Message(entry=entry, message=parsed, content=get_email_content(parsed))


def delete_email(request: HttpRequest, message_id: str) -> None:
    s3_client = boto3.client(
        "s3",
    )
    s3_client.delete_object(Bucket=BUCKET_NAME, Key=message_id)


def get_email_content(email_msg: email.message.Message) -> str:
    """
    Extracts and cleans the HTML or plain text content from an email message.

    :param email_msg: An email.message.Message object
    :return: Sanitized HTML or text content
    """
    content_type = email_msg.get_content_type()
    content = ""

    if email_msg.is_multipart():
        for part in email_msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                content = part.get_payload(decode=True).decode()
                break
            elif content_type == "text/html":
                content = part.get_payload(decode=True).decode()
                # Use bleach to clean and linkify the HTML content
                content = bleach.clean(content, strip=True)
                content = bleach.linkify(content)
                break
    else:
        content = email_msg.get_payload(decode=True).decode()
        if content_type == "text/html":
            content = bleach.clean(content, strip=True)
            content = bleach.linkify(content)

    return content


def get_bucket_messages(request: HttpRequest) -> list[MessageEntry]:
    return sorted(
        list(yield_bucket_messages(request)),
        key=lambda m: m.last_modified,
        reverse=True,
    )


def yield_bucket_messages(request: HttpRequest) -> Generator[MessageEntry, Any, Any]:
    s3_client = boto3.client(
        "s3",
    )
    paginator = s3_client.get_paginator("list_objects_v2")
    for response in paginator.paginate(Bucket=BUCKET_NAME, Prefix=PREFIX):
        for o in response["Contents"]:
            raw_tags = cache.get_or_set(
                o["Key"], partial(fetch_tags, s3_client, o["Key"])
            )
            tags = format_tags(raw_tags)

            m = MessageEntry(
                message_id=o["Key"],
                sender=tags["From"],
                subject=tags["Subject"],
                last_modified=o["LastModified"],
            )
            # print(tags)
            yield m


def subject_from_tags(tags):
    subject = tags.get("Subject", None)
    if not subject:
        return "No Subject"

    return base64.b64decode(subject).decode("utf-8")


def message_entry(s3_object, tags) -> MessageEntry:
    return MessageEntry(
        message_id=s3_object["Key"],
        sender=tags["From"],
        subject=tags["Subject"],
        last_modified=s3_object["LastModified"],
    )


def format_tags(tags):
    tag_dict = {k: v for k, v in tags.items() if k not in ("From", "Subject")}
    tag_dict["From"] = tags.get("From", "Unknown Sender")
    tag_dict["Subject"] = subject_from_tags(tags)
    return tag_dict


def fetch_tags(s3_client, key):
    resp = s3_client.get_object_tagging(Bucket=BUCKET_NAME, Key=key)
    if "TagSet" not in resp:
        return {}

    return dict([(t["Key"], t["Value"]) for t in resp["TagSet"]])
