"""The logic to calculate the availability of books.

This module provides functionality to determine whether books are available
for borrowing or browsing through the OPDS system, based on Internet Archive
lending metadata.
"""
from typing import Optional
from pydantic import BaseModel, Field


class AvailableInfo(BaseModel):
    """Information about a book's lending availability status.

    This model contains all the metadata fields from Internet Archive
    that are used to determine whether a book can be borrowed or browsed.
    """
    lending_available_to_borrow: Optional[bool] = Field(
        None, description="If lending___available_to_borrow is true for a book, "
                          "that book can be lent through OPDS right now."
                          "Otherwise, it is currently unavailable")
    lending_available_to_browse: Optional[bool] = Field(
        None, description="IA field to check book availability")
    lending_max_lendable_copies: Optional[int] = Field(
        None, description="IA field to check book availability")
    lending_users_on_waitlist: Optional[int] = Field(
        None, description="IA field to check book availability")
    lending_active_borrows: Optional[int] = Field(
        None, description="IA field to check book availability")
    lending_active_browses: Optional[int] = Field(
        None, description="IAfield to check book availability")
    lending_borrow_expiration: Optional[str] = Field(
        None, description="IA field to check book availability")
    lending_browse_expiration: Optional[str] = Field(
        None, description="IA field to check book availability")


def check_availability(available_info: AvailableInfo) -> dict:
    """
    If lending___available_to_borrow is true for a book,
    that book can be lent through OPDS right now.
    Otherwise, it is currently unavailable.

    If available_to_borrow is not set or false, check available_to_browse.
    If true, then the book is available to browse.

    A book may be available to browse and borrow at the same time,
    and in that case, we always default to borrow.

    If lending___is_borrowable is true for a book,
    that book can be lent if there are available copies.
    If it is not true, then the book can never be lent and
    should probably be excluded from the list entirely,
    at least until we consider making 1-hours browses available through OPDS.

    If a book is borrowable, but not currently available to borrow,
    we can make an assumption about when
    it may become available, using the fields to calculate the probably available time:

    Args:
        available_info: An AvailableInfo object containing the book's
            lending metadata from Internet Archive.

    Returns:
        A dictionary with the availability status containing:
        - 'state': Either 'available' or 'unavailable'
        - 'until': (optional) ISO timestamp when the book may become
          available, included only when state is 'unavailable' and
    """
    if available_info.lending_available_to_borrow:
        return {
            "state": "available"
        }

    if available_info.lending_available_to_browse:
        return {
            "state": "available"
        }

    fields = {
        "max_lendable_copies": available_info.lending_max_lendable_copies,
        "users_on_waitlist": available_info.lending_users_on_waitlist,
        "active_borrows": available_info.lending_active_borrows,
        "active_browses": available_info.lending_active_browses}

    if None in fields.values():
        return {
            "state": "unavailable"
        }

    book_available_at_next_browse_expiration, book_available_at_next_borrow_expiration = \
        _calculate_expiration(
            fields["max_lendable_copies"],
            fields["users_on_waitlist"],
            fields["active_borrows"],
            fields["active_browses"]
        )

    if book_available_at_next_browse_expiration and book_available_at_next_borrow_expiration:
        try:
            return {
                "state": "unavailable",
                "until": min(available_info.lending_borrow_expiration,
                             available_info.lending_browse_expiration)
            }
        except TypeError:
            return {
                "state": "unavailable"
            }

    if book_available_at_next_browse_expiration:
        return {
            "state": "unavailable",
            "until": available_info.lending_browse_expiration
        }
    if book_available_at_next_borrow_expiration:
        return {
            "state": "unavailable",
            "until": available_info.lending_borrow_expiration
        }

    return {
        "state": "unavailable"
    }


def _calculate_expiration(
        max_lendable_copies: int,
        users_on_waitlist: int,
        active_borrows: int,
        active_browses: int,
) -> (bool, bool):
    """Calculate whether a book will become available after next expiration.

    This function determines if a book will have available copies when the
    next browse or borrow session expires, taking into account the total
    lendable copies, current usage, and waitlist.

    The calculation accounts for:
    - One copy is always reserved for browse sessions (max_borrowable = max - 1)
    - Browse sessions can use any available copy
    - Borrow sessions can only use borrowable copies

    Args:
        max_lendable_copies: The total number of copies that can be lent
            at any time (borrows + browses combined).
        users_on_waitlist: The total number of users waiting to borrow
            the book.
        active_borrows: The total number of active borrow transactions.
        active_browses: The total number of active 1-hour browse sessions
            checked out on the book.

    Returns:
        A tuple of two booleans:
        - First element: True if the book will be available after the next
          browse expiration, False otherwise.
        - Second element: True if the book will be available after the next
          borrow expiration, False otherwise.
    """
    max_borrowable_copies = max_lendable_copies - 1
    remaining_borrowable_copies = max_borrowable_copies - \
        (active_borrows + users_on_waitlist)

    remaining_lendable_copies_after_browse_expiration = max_lendable_copies - \
        ((active_browses - 1) + active_borrows
         + users_on_waitlist)
    book_available_at_next_browse_expiration = all(
        (remaining_lendable_copies_after_browse_expiration > 0,
         remaining_borrowable_copies > 0))

    remaining_lendable_copies_after_borrow_expiration = max_lendable_copies - \
        (active_browses + (active_borrows - 1) +
         users_on_waitlist)
    remaining_borrowable_copies_after_borrow_expiration = max_borrowable_copies - \
        ((active_borrows - 1) + users_on_waitlist)

    book_available_at_next_borrow_expiration = all(
        (remaining_lendable_copies_after_borrow_expiration > 0,
         remaining_borrowable_copies_after_borrow_expiration))

    return book_available_at_next_browse_expiration, book_available_at_next_borrow_expiration
