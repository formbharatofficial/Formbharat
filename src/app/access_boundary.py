"""Local profile slots are not accounts.

A future account system needs its own user record, a password hash stored
outside source code, and a server session tied to that user. Profiles and
documents would then be owned by the user id. That migration is not started.
Until then, slots 1-5 stay separate only by profile_id checks.
"""


def slot_access():
    return {
        "authenticated_account": False,
        "access": "profile_slot",
        "account_note": (
            "Profile slots 1-5 are local device slots, not signed-in accounts."
        ),
    }
