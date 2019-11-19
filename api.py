#! /usr/bin/env python3

import json
import os
import re
import sys

import requests

MAILCHIMP_API_KEY = os.getenv("MAILCHIMP_API_KEY")
MAILCHIMP_AUDIENCE_ID = os.getenv("MAILCHIMP_AUDIENCE_ID")
MANDRILL_API_KEY = os.getenv("MANDRILL_API_KEY")
FREEFROM_API_ROOT = os.getenv("FREEFROM_API_ROOT")

assert (
    MAILCHIMP_API_KEY is not None
), "Please set the MAILCHIMP_API_KEY environment variable"
assert (
    MAILCHIMP_AUDIENCE_ID is not None
), "Please set the MAILCHIMP_AUDIENCE_ID environment variable"
assert (
    MANDRILL_API_KEY is not None
), "Please set the MANDRILL_API_KEY environment variable"

MAILCHIMP_DC = MAILCHIMP_API_KEY.split("-")[-1]

STATES = {
    "AK": "Alaska",
    "AL": "Alabama",
    "AR": "Arkansas",
    "AZ": "Arizona",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DC": "Washington, DC",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "IA": "Iowa",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "MA": "Massachusetts",
    "MD": "Maryland",
    "ME": "Maine",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MO": "Missouri",
    "MS": "Mississippi",
    "MT": "Montana",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "NE": "Nebraska",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NV": "Nevada",
    "NY": "New York",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VA": "Virginia",
    "VT": "Vermont",
    "WA": "Washington",
    "WI": "Wisconsin",
    "WV": "West Virginia",
    "WY": "Wyoming",
}


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


def send_results(email_address: str, mindset_id: int, state: str) -> dict:
    mindset_response = requests.get(f"{FREEFROM_API_ROOT}/mindsets/{mindset_id}")
    if not mindset_response.ok:
        return {
            "body": json.dumps(
                {"status": "UPSTREAM_API_ERROR", "error": "Mindset API failed"}
            ),
            "statusCode": 424,
        }
    mindset = mindset_response.json()
    categories_response = requests.get(f"{FREEFROM_API_ROOT}/resource_categories/")
    if not categories_response.ok:
        return {
            "body": json.dumps(
                {
                    "status": "UPSTREAM_API_ERROR",
                    "error": "Resource Categories API failed",
                }
            ),
            "statusCode": 424,
        }
    categories = categories_response.json()
    category = [x for x in categories if x["id"] == mindset["resource_category_id"]][0]
    other_categories = [
        x for x in categories if not x["id"] == mindset["resource_category_id"]
    ]
    print(mindset, category, other_categories)
    slug = mindset["slug"]
    slug = re.sub(r"^the-", "", slug)
    content = []
    content += [f"<h1>Your Compensation Mindset</h1>"]
    content += [
        (
            f'<img style="display: block; margin: 16px auto;" '
            f'src="https://s3.amazonaws.com/freefrom-compensation-dev/images/mindsets/'
            f'{slug}.png" '
            f'alt="">'
        )
    ]
    content += [f"<p><b>{mindset['name']}</b></p>"]
    content += [f"<p>{x}</p>" for x in mindset["description"].split("\n")]
    content += [
        (
            f"<p>The {mindset['name']}&rsquo;s goals and priorities are best matched "
            f"with a <b>{category['name'].lower()}</b> as a compensation option.</p>"
        )
    ]
    content += [f"<p>{x}</p>" for x in category["description"].split("\n")]
    content += [
        f"<p style='text-transform: uppercase'><b>A Note About Your Results</b></p>"
    ]
    state_name = STATES.get(state, "your area")
    content += [
        (
            f"<p>No person fits perfectly within only one Compensation Mindset. "
            f"You must decide which type of compensation is best for you. "
            f"Below, you can find information about the other compensation options in "
            f"{state_name}</p>"
        )
    ]
    for other_category in other_categories:
        content += [
            f"<p><b>{other_category['name']}:</b> {other_category['description']}</p>"
        ]
    content = "\n".join(content)
    print(content)
    mandrill_response = requests.post(
        "https://mandrillapp.com/api/1.0/messages/send-template.json",
        json={
            "key": MANDRILL_API_KEY,
            "template_name": "compass-results",
            "template_content": [{"name": "main", "content": content}],
            "message": {
                "subject": "Your FreeFrom Compensation Compass Results",
                "from_email": "compass@freefrom.org",
                "from_name": "FreeFrom Compensation Compass",
                "to": [{"email": email_address}],
                "track_opens": True,
                "auto_text": True,
                "inline_css": True,
                "view_content_link": False,
                "tags": [f"mindest-{mindset_id}", f"state-{state}"],
            },
        },
    )
    if not mandrill_response.ok:
        print(mandrill_response.text)
        return {
            "body": json.dumps(
                {"status": "UPSTREAM_API_ERROR", "error": "Mandrill API failed"}
            ),
            "statusCode": 424,
        }
    return {"body": json.dumps({"status": "RESULTS_SENT"}), "statusCode": 200}


def lambda_handler(event: dict, context: object) -> dict:
    headers = event.get("headers", {})
    referrer = headers.get("referer") or headers.get("Referer")
    if not referrer_is_allowed(referrer):
        return {"body": json.dumps({"status": "NOT_AUTHORIZED"}), "statusCode": 403}
    body = json.loads(event.get("body", "{}"))
    resource = event.get("resource")
    if resource == "/subscribe":
        return subscribe(body["email"])
    elif resource == "/send-results":
        return send_results(body["email"], body["mindset_id"], body["state"])
    return {"body": json.dumps({"status": "NOT_SUPPORTED"}), "statusCode": 405}


# for testing on the command line
if __name__ == "__main__":
    if sys.argv[1] == "subscribe":
        print(subscribe(sys.argv[1]))
    elif sys.argv[1] == "results":
        print(send_results(sys.argv[2], sys.argv[3], sys.argv[4]))
