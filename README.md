# FreeFrom Compensation Mailer

## Overview

FreeFrom is a nonprofit dedicated to helping survivors of domestic violence achieve financial stability. On their website they have a compensation tool where users can answer a series of questions in order to get information about financial resources that are available to them depending on their state.

This repository contains the AWS Lambda functions for adding new subscribers to the mailing list and for emailing Compensation Quiz results to quiz takers.

Additionally it contains a copy of the HTML email template for Mandrill. Changes to this template need to be manually copied over to Mandrill.

## Subscribe endpoint

**POST /subscribe**

Adds the given email address to the Mailchimp audience if it's not already there.

_Request Payload:_

```json
{
  "email": "test@example.com"
}
```

_Response Payloads:_

If the email address is new to the audience, a `200 OK` response with the following is returned:

```json
{
  "status": "NEWLY_SUBSCRIBED"
}
```

If the email address is already in the audience, a `200 OK` response with the following is returned:

```json
{
  "status": "ALREADY_SUBSCRIBED"
}
```

## Send Results endpoint

**POST /send-results**

Sends the Compensation Mindset and associated resources to the given email address.

_Request Payload:_

```json
{
  "email": "test@example.com",
  "mindset_id": 1,
  "state": "CA"
}
```

_Response Payloads:_

If the results were successfully sent, a `200 OK` response with the following is returned:

```json
{
  "status": "RESULTS_SENT"
}
```

_The response status may also be `RESULTS_QUEUED` if Mandrill hasn't yet sent the email._

If one of the upstream APIs fails, a `424 FAILED DEPENDENCY` response with the following is returned:

```json
{
  "status": "UPSTREAM_API_ERROR",
  "error": "Descriptive error message"
}
```
