"""Availability of preserved account profiles in this release."""

GUARDIAN_ACCESS_ENABLED = False


def role_available(role):
    return role != 'responsavel' or GUARDIAN_ACCESS_ENABLED
