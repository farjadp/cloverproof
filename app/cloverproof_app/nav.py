"""What the app shell shows to the signed-in user (base.html).

Display only: every route still checks access itself. Each rule here mirrors the dependency
of the route it links to, so nobody is offered a link that ends in a 403:

- Farmers, My account: `InternalOrg` (an internal role in the current organisation)
- Review queue: `InternalOrg` + `plan_web.is_agronomist`
- Users: `require_org_role("org_admin")`
- Products, Change password: any signed-in user
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from cloverproof_app.auth import INTERNAL_ROLES, PASSWORD_CHANGE_PATH, CurrentUser, OrgContext

ROLE_LABELS = {
    "org_admin": "Org admin",
    "agronomist": "Agronomist",
    "advisor": "Advisor",
    "farmer": "Farmer",
}
# Pages of the farmer -> field -> plan flow, which all sit under "Farmers".
FARMER_FLOW = ("/farmers", "/fields", "/plans")


@dataclass(frozen=True)
class NavLink:
    label: str
    href: str
    current: bool = False


@dataclass(frozen=True)
class Nav:
    home: str
    links: tuple[NavLink, ...]
    account: NavLink | None
    user_name: str
    role_text: str
    org_name: str | None
    can_switch_org: bool
    must_choose_org: bool


def role_label(roles: Sequence[str]) -> str:
    return ", ".join(ROLE_LABELS.get(r, r) for r in roles) or "No role"


def _within(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def _role_text(user: CurrentUser, org: OrgContext | None) -> str:
    labels = [ROLE_LABELS.get(r, r) for r in org.roles] if org else []
    if user.is_superadmin:
        labels.append("Superadmin")
    return ", ".join(labels)


def build_nav(
    path: str,
    user: CurrentUser | None,
    org: OrgContext | None,
    *,
    must_choose_org: bool = False,
    locked: bool = False,
) -> Nav | None:
    """The shell for this request; None when signed out.

    `locked`: the user must replace a temporary password first, and every other page would
    only send them back, so no destinations are offered.
    """
    if user is None:
        return None
    from cloverproof_app.plan_web import is_agronomist  # plan_web imports web, which imports us

    internal = org is not None and any(role in INTERNAL_ROLES for role in org.roles)
    links: list[NavLink] = []
    account: NavLink | None = None
    if not locked:
        if internal:
            in_flow = path == "/" or any(_within(path, prefix) for prefix in FARMER_FLOW)
            links.append(NavLink("Farmers", "/farmers", in_flow))
        if internal and org is not None and is_agronomist(org):
            links.append(NavLink("Review queue", "/review", _within(path, "/review")))
        links.append(NavLink("Products", "/products", _within(path, "/products")))
        if org is not None and "org_admin" in org.roles:
            links.append(NavLink("Users", "/admin/users", _within(path, "/admin/users")))
        if internal:
            account = NavLink("My account", "/account", _within(path, "/account"))
        else:
            current = path == PASSWORD_CHANGE_PATH
            account = NavLink("Change password", PASSWORD_CHANGE_PATH, current)
    return Nav(
        home="/" if internal else "/products",
        links=tuple(links),
        account=account,
        user_name=user.display_name,
        role_text=_role_text(user, org),
        org_name=org.org.name if org else None,
        can_switch_org=not locked and org is not None and len(org.organisations) > 1,
        must_choose_org=not locked and must_choose_org,
    )
