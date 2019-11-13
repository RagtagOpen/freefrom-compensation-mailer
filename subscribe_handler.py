#! /usr/bin/env python3

import json
import os
import sys

import requests

MAILCHIMP_API_KEY = os.getenv("MAILCHIMP_API_KEY")
MAILCHIMP_AUDIENCE_ID = os.getenv("MAILCHIMP_AUDIENCE_ID")

assert (
    MAILCHIMP_API_KEY is not None
), "Please set the MAILCHIMP_API_KEY environment variable"
assert (
    MAILCHIMP_AUDIENCE_ID is not None
), "Please set the MAILCHIMP_AUDIENCE_ID environment variable"

MAILCHIMP_DC = MAILCHIMP_API_KEY.split("-")[-1]


def referrer_is_allowed(referrer):
    allowed_referrers = os.getenv("ALLOWED_REFERRERS", "").split("|")
    referrer = (referrer or "").strip()
    allowed = False
    for allowed_referrer in allowed_referrers:
        if referrer.startswith(allowed_referrer):
            allowed = True
            break
    return allowed


def subscribe(email_address: str) -> dict:
    response = requests.post(
        (
            f"https://{MAILCHIMP_DC}.api.mailchimp.com/3.0/lists/"
            f"{MAILCHIMP_AUDIENCE_ID}/members/"
        ),
        json={"email_address": email_address, "status": "subscribed"},
        auth=("", MAILCHIMP_API_KEY),
    )
    status_code = response.status_code
    status_text = "UNKNOWN"
    if response.status_code == 200:
        status_text = "NEWLY_SUBSCRIBED"
    elif response.status_code == 400:
        # we don't want to throw an error if someone signs up multiple times,
        # so we switch the status code back to 200
        status_text = "ALREADY_SUBSCRIBED"
        status_code = 200
    return {"body": json.dumps({"status": status_text}), "statusCode": status_code}


def lambda_handler(event: dict, context: object) -> dict:
    headers = event.get("headers", {})
    referrer = headers.get("referer") or headers.get("Referer")
    if not referrer_is_allowed(referrer):
        return {
            "body": json.dumps({"status": "NOT_AUTHORIZED", "referrer": referrer}),
            "statusCode": 403,
        }
    body = json.loads(event.get("body", "{}"))
    return subscribe(body["email"])


# for testing on the command line
if __name__ == "__main__":
    print(subscribe(sys.argv[1]))
