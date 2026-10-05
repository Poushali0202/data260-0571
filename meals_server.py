import logging
import sys

import httpx
from mcp.server.mcpserver import MCPServer

from retry import retry_call

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("meals")

BASE = "https://www.themealdb.com/api/json/v1/1"
mcp = MCPServer("meals")


def fetch(path, **params):
    def call():
        response = httpx.get(f"{BASE}/{path}", params=params, timeout=10.0)
        response.raise_for_status()
        return response.json()

    try:
        data = retry_call(call, retry_on=(httpx.HTTPError,))
    except httpx.HTTPError as error:
        raise RuntimeError(f"TheMealDB request failed: {error}")
    except ValueError as error:
        raise RuntimeError(f"TheMealDB returned invalid JSON: {error}")
    log.info("GET %s %s -> %d meals", path, params, len(data.get("meals") or []))
    return data.get("meals") or []


def card(meal):
    return {"id": meal["idMeal"], "name": meal["strMeal"], "thumb": meal["strMealThumb"]}


def details(meal):
    ingredients = []
    for i in range(1, 21):
        name = (meal.get(f"strIngredient{i}") or "").strip()
        if name:
            ingredients.append({"name": name, "measure": (meal.get(f"strMeasure{i}") or "").strip()})
    return {
        "id": meal["idMeal"],
        "name": meal["strMeal"],
        "category": meal["strCategory"],
        "area": meal["strArea"],
        "instructions": meal["strInstructions"],
        "image": meal["strMealThumb"],
        "source": meal.get("strSource"),
        "youtube": meal.get("strYoutube"),
        "ingredients": ingredients,
    }


def no_matches(what):
    return {"results": [], "message": f"no matches for {what}"}


@mcp.tool()
def search_meals_by_name(query: str, limit: int = 5) -> list[dict] | dict:
    """Search meals by name. Returns up to limit (1 to 25) meals with id, name, area, category and thumb."""
    limit = max(1, min(25, limit))
    meals = fetch("search.php", s=query)
    if not meals:
        return no_matches(f"name '{query}'")
    return [card(m) | {"area": m["strArea"], "category": m["strCategory"]} for m in meals[:limit]]


@mcp.tool()
def meals_by_ingredient(ingredient: str, limit: int = 12) -> list[dict] | dict:
    """Meals whose main ingredient matches. Returns small cards with id, name and thumb."""
    limit = max(1, min(50, limit))
    meals = fetch("filter.php", i=ingredient)
    if not meals:
        return no_matches(f"ingredient '{ingredient}'")
    return [card(m) for m in meals[:limit]]


@mcp.tool()
def random_meal() -> dict:
    """One random meal with its full recipe details."""
    meals = fetch("random.php")
    if not meals:
        return no_matches("random meal")
    return details(meals[0])


@mcp.tool()
def meal_details(id: str | int) -> dict:
    """Full recipe details for one meal id: category, area, instructions, image, source, youtube and ingredients."""
    meals = fetch("lookup.php", i=str(id))
    if not meals:
        return no_matches(f"meal id {id}")
    return details(meals[0])


if __name__ == "__main__":
    mcp.run(transport="stdio")
