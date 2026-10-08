"""Pure-logic pieces of the agent layer: intent routing and link-building tools."""

import pytest

from api.agents import tools
from api.agents.brain import _plan_execution


@pytest.mark.parametrize(
    "message, agents, chain",
    [
        ("I'm hungry, what should I get for dinner?", ["FoodAgent"], False),
        ("order my usual food", ["ProfileAgent", "FoodAgent"], True),
        ("reorder my headphones", ["ShoppingAgent"], False),
        ("sync gmail and show my food orders", ["EmailAgent", "FoodAgent"], True),
        ("send an email to Alex", ["EmailAgent"], False),
        ("what's in my profile?", ["ProfileAgent"], False),
        ("what's the capital of France?", ["GeneralAgent"], False),
    ],
)
def test_plan_execution_routes_intent(message, agents, chain):
    plan = _plan_execution(message)
    assert plan["agents_to_deploy"] == agents
    assert plan["chain"] is chain


def test_search_product_links_are_url_safe():
    links = tools.search_product_to_buy("usb c cable")["search_links"]
    assert links["amazon"] == "https://www.amazon.com/s?k=usb+c+cable"
    assert links["target"] == "https://www.target.com/s?searchTerm=usb+c+cable"


def test_platform_search_url_falls_back_to_google():
    assert tools._get_platform_search_url("doordash", "Panda Express") == "https://www.doordash.com/search/store/Panda%20Express/"
    assert tools._get_platform_search_url("unknown", "Joe's").startswith("https://www.google.com/search?q=Joe's")


def test_browser_automation_is_off_by_default():
    amazon = tools.autonomous_shop_amazon("usb c cable")
    food = tools.autonomous_order_food("pad thai")
    assert amazon["status"] == food["status"] == "browser_automation_disabled"
    assert amazon["search_links"]["amazon"].endswith("k=usb+c+cable")
    assert "doordash.com" in food["url"]
