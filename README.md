# Kontrolafgifter i bus

## Setup

This process will run on a queue of elements, which need to be set up by running the script queue_load.py with a CSV as described below.

## Process arguments

The process arguments should contain the following json object:

```json
{
    "receivers": [
        "hello@mail.com"
    ]
}
```

"receivers" is the list of emails to send the result to.

## Queue elements

Each queue element is expected to have the following json object in its data field:

```json
{
    "cpr": "1234567890",
    "aftaler": [
        "123456",
        "456789"
    ]
}
```

"cpr" is the cpr number of the person in question.
"aftaler" is a list of relevant aftaler on the given person.
