"""Fixed, public-safe routes used by GitHub experience demonstration packages."""

from __future__ import annotations


GITHUB_DEMO_ROUTES: dict[str, tuple[str, ...]] = {
    "night_signal": ("listen", "approach", "listen", "listen", "leave"),
    "harbor_protocol": ("listen", "approach", "listen", "approach", "listen"),
}


def github_demo_actions(scenario: str) -> tuple[str, ...]:
    """Return the one reviewed public-safe route for a known synthetic scenario."""

    try:
        return GITHUB_DEMO_ROUTES[scenario]
    except KeyError as error:
        raise ValueError("No GitHub synthetic demo route is registered for scenario: " + scenario) from error
