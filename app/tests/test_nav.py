"""The shell offers each role the destinations its routes allow (nav.py)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from cloverproof_app.auth import CurrentUser, OrgContext
from cloverproof_app.nav import Nav, build_nav
from cloverproof_app.repo.users import Organisation


def person(platform_role: str | None = None, actor_kind: str = "human") -> CurrentUser:
    return CurrentUser(
        uuid4(), "t@example.test", "Test User", uuid4(), "hash", actor_kind, platform_role
    )


def org_of(user: CurrentUser, *roles: str, organisations: int = 1) -> OrgContext:
    orgs = tuple(Organisation(uuid4(), f"Test Org {i}") for i in range(organisations))
    return OrgContext(user, orgs[0], roles, orgs)


def labels(nav: Nav | None) -> list[str]:
    assert nav is not None
    return [link.label for link in nav.links]


def current(nav: Nav | None) -> list[str]:
    assert nav is not None
    return [link.label for link in nav.links if link.current]


def test_signed_out_has_no_navigation() -> None:
    assert build_nav("/login", None, None) is None


@pytest.mark.parametrize(
    ("roles", "expected"),
    [
        (("org_admin",), ["Farmers", "Products", "Users"]),
        (("agronomist",), ["Farmers", "Review queue", "Products"]),
        (("advisor",), ["Farmers", "Products"]),
        (("org_admin", "agronomist"), ["Farmers", "Review queue", "Products", "Users"]),
        (("farmer",), ["Products"]),
    ],
)
def test_links_follow_the_role(roles: tuple[str, ...], expected: list[str]) -> None:
    user = person()
    assert labels(build_nav("/products", user, org_of(user, *roles))) == expected


def test_superadmin_member_may_review_like_the_route_allows() -> None:
    user = person("superadmin")
    nav = build_nav("/farmers", user, org_of(user, "advisor"))
    assert "Review queue" in labels(nav)
    assert nav is not None and "Superadmin" in nav.role_text


def test_service_account_is_not_offered_the_review_queue() -> None:
    user = person(actor_kind="service")
    assert "Review queue" not in labels(build_nav("/farmers", user, org_of(user, "agronomist")))


def test_superadmin_without_organisation_gets_what_works() -> None:
    nav = build_nav("/products", person("superadmin"), None)
    assert labels(nav) == ["Products", "Organisations"]
    assert nav is not None and nav.home == "/products" and nav.org_name is None
    assert nav.can_manage_orgs
    assert nav.account is not None and nav.account.href == "/account/password"


def test_only_a_human_superadmin_is_offered_organisations() -> None:
    plain = person()
    service = person(actor_kind="service")
    assert "Organisations" not in labels(build_nav("/farmers", plain, org_of(plain, "org_admin")))
    assert "Organisations" not in labels(build_nav("/farmers", service, None))
    nav = build_nav("/admin/organisations", person("superadmin"), None)
    assert current(nav) == ["Organisations"]


def test_locked_superadmin_is_not_offered_organisations() -> None:
    nav = build_nav("/account/password", person("superadmin"), None, locked=True)
    assert nav is not None and nav.links == () and not nav.can_manage_orgs


def test_undecided_organisation_offers_the_chooser() -> None:
    nav = build_nav("/products", person(), None, must_choose_org=True)
    assert nav is not None and nav.must_choose_org


def test_switching_needs_more_than_one_organisation() -> None:
    user = person()
    one, two = org_of(user, "advisor"), org_of(user, "advisor", organisations=2)
    assert not build_nav("/farmers", user, one).can_switch_org  # type: ignore[union-attr]
    assert build_nav("/farmers", user, two).can_switch_org  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/", ["Farmers"]),
        ("/farmers/new", ["Farmers"]),
        ("/fields/x", ["Farmers"]),
        ("/plans/x/edit", ["Farmers"]),
        ("/review", ["Review queue"]),
        ("/products", ["Products"]),
        ("/admin/users/x", ["Users"]),
        ("/account", []),
        ("/farmersx", []),
    ],
)
def test_current_page_is_marked_once(path: str, expected: list[str]) -> None:
    user = person()
    assert current(build_nav(path, user, org_of(user, "org_admin", "agronomist"))) == expected


def test_temporary_password_locks_the_navigation() -> None:
    user = person()
    nav = build_nav("/account/password", user, org_of(user, "org_admin"), locked=True)
    assert nav is not None and nav.links == () and nav.account is None
