import pytest
from opds.availability import _calculate_expiration, check_availability, AvailableInfo


@pytest.mark.parametrize(
    "max_lendable_copies, users_on_waitlist, active_borrows, active_browses, expect",
    [
        (4, 0, 0, 0, (True, True)),
        (4, 2, 1, 1, (False, True)),
        (4, 0, 2, 2, (True, True)),
        (4, 4, 0, 0, (False, False)),
        (4, 1, 3, 3, (False, False)),
        (4, 2, 0, 2, (True, True)),
        (4, 0, 4, 0, (False, False)),
        (4, 0, 0, 4, (True, True))
    ],
)
def test_calculate_expiration(
        max_lendable_copies,
        users_on_waitlist,
        active_borrows,
        active_browses,
        expect):
    assert _calculate_expiration(
        max_lendable_copies,
        users_on_waitlist,
        active_borrows,
        active_browses) == expect


@pytest.mark.parametrize("item_metadata, book_available, expect",
                         [({"lending___available_to_borrow": True}, (), "available"),
                             ({"lending___available_to_borrow": False}, (), "unavailable"),
                             ({"lending___available_to_borrow": False,
                               "lending___max_lendable_copies": True,
                               "lending___users_on_waitlist": True,
                               "lending___active_borrows": True,
                               "lending___active_browses": True},
                              (False, False),
                              "unavailable"),
                             ({"lending___available_to_borrow": False,
                               "lending___max_lendable_copies": True,
                               "lending___users_on_waitlist": True,
                               "lending___active_borrows": True,
                               "lending___active_browses": True},
                              (False, True),
                              "unavailable"),
                             ({"lending___available_to_borrow": False,
                               "lending___max_lendable_copies": True,
                               "lending___users_on_waitlist": True,
                               "lending___active_borrows": True,
                               "lending___active_browses": True},
                              (True, False),
                              "unavailable"),
                             ({"lending___available_to_borrow": False,
                               "lending___max_lendable_copies": True,
                               "lending___users_on_waitlist": True,
                               "lending___active_borrows": True,
                               "lending___active_browses": True},
                              (True, True),
                              "unavailable"),
                             ({"lending___available_to_borrow": False,
                               "lending___available_to_browse": True,
                                "lending___max_lendable_copies": True,
                                "lending___users_on_waitlist": True,
                                "lending___active_borrows": True,
                                "lending___active_browses": True},
                               (),
                               "available"),
                          ],
                         )
def test_check_availability(mocker, item_metadata, book_available, expect):
    mock_calculate_expiration = mocker.patch(
        "opds.availability._calculate_expiration")
    mock_calculate_expiration.return_value = book_available

    available_info = AvailableInfo(
        lending_available_to_borrow=item_metadata.get("lending___available_to_borrow"),
        lending_available_to_browse=item_metadata.get("lending___available_to_browse"),
        lending_max_lendable_copies=item_metadata.get("lending___max_lendable_copies"),
        lending_users_on_waitlist=item_metadata.get("lending___users_on_waitlist"),
        lending_active_borrows=item_metadata.get("lending___active_borrows"),
        lending_active_browses=item_metadata.get("lending___active_browses"),
        lending_borrow_expiration=item_metadata.get("lending___borrow_expiration"),
        lending_browse_expiration=item_metadata.get("lending___browse_expiration"))

    availability = check_availability(available_info)
    assert availability.get("state") == expect
