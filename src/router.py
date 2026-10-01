"""Step 5: decide what happens next. Plain rules, no AI.

Keeping this in code means a manager can read exactly why a message
got no draft, and the model can never talk its way into a reply.
"""

ROUTES = {
    "enquiry": "draft_reply",
    "complaint": "route_to_person",   # an upset customer gets a human, never a bot reply
    "not_enquiry": "skip",
}


def route(label):
    return ROUTES[label]
