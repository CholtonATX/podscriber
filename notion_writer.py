import re
from datetime import datetime, timezone

from notion_client import Client

from logger import get_logger
from models import BrewingInsights, Episode, RecipeEntry

logger = get_logger(__name__)

# Notion rich_text content is limited to 2000 characters per block
_NOTION_TEXT_LIMIT = 2000


_NOTION_BLOCK_LIMIT = 100


def _ensure_database_properties(notion: Client, database_id: str) -> set[str]:
    """
    Add missing properties to the Notion database schema.
    Returns the set of property names that exist after the update.
    """
    try:
        result = notion.databases.update(
            database_id=database_id,
            properties={
                "Episode Number": {"number": {}},
                "Published Date": {"date": {}},
                "Podcast Name": {"rich_text": {}},
                "Audio URL": {"url": {}},
                "Processed At": {"date": {}},
            },
        )
        existing = set(result.get("properties", {}).keys())
        logger.info(f"Database properties: {sorted(existing)}")
        return existing
    except Exception as e:
        logger.warning(f"Could not update database schema: {e}. Will skip extra properties.")
        return set()


def create_episode_page(
    episode: Episode,
    insights: BrewingInsights,
    database_id: str,
    api_key: str,
) -> str:
    """Create a Notion page for the episode. Returns the new page's URL."""
    notion = Client(auth=api_key)

    existing_props = _ensure_database_properties(notion, database_id)

    properties = _build_properties(episode, existing_props)
    all_blocks = _build_blocks(episode, insights)

    # Notion allows at most 100 blocks per request; create with first batch then append
    first_batch = all_blocks[:_NOTION_BLOCK_LIMIT]
    remaining = all_blocks[_NOTION_BLOCK_LIMIT:]

    response = notion.pages.create(
        parent={"database_id": database_id},
        properties=properties,
        children=first_batch,
    )
    page_id = response["id"]

    for i in range(0, len(remaining), _NOTION_BLOCK_LIMIT):
        batch = remaining[i:i + _NOTION_BLOCK_LIMIT]
        notion.blocks.children.append(block_id=page_id, children=batch)

    return response["url"]


def _clean_title(title: str) -> str:
    """Strip leading 'Episode N:' / 'Episode N -' style prefixes from RSS titles."""
    return re.sub(r"^Episode\s+\S+[\s:\-–]+", "", title, flags=re.IGNORECASE).strip()


def _build_properties(episode: Episode, existing_props: set[str]) -> dict:
    props = {
        "Name": {
            "title": [{"text": {"content": f"[Ep. {episode.number}] {_clean_title(episode.title)}"[:_NOTION_TEXT_LIMIT]}}]
        },
    }
    optional = {
        "Episode Number": {"number": episode.number},
        "Published Date": {"date": {"start": episode.published.date().isoformat()}},
        "Podcast Name": {"rich_text": [{"text": {"content": episode.podcast_name[:_NOTION_TEXT_LIMIT]}}]},
        "Audio URL": {"url": episode.audio_url},
        "Processed At": {"date": {"start": datetime.now(tz=timezone.utc).date().isoformat()}},
    }
    for key, value in optional.items():
        if key in existing_props:
            props[key] = value
    return props


def _build_blocks(episode: Episode, insights: BrewingInsights) -> list[dict]:
    blocks = []

    # Episode summary callout
    blocks.append(_callout(insights.episode_summary, emoji="🍺"))
    blocks.append(_divider())

    # Brewing Techniques
    blocks.append(_heading2("Brewing Techniques"))
    blocks.extend(_bulleted_list(
        insights.brewing_techniques,
        empty_text="No techniques specifically noted in this episode.",
    ))
    blocks.append(_divider())

    # Recipes
    blocks.append(_heading2("Recipes"))
    if insights.recipes:
        for recipe in insights.recipes:
            blocks.extend(_recipe_blocks(recipe))
    else:
        blocks.append(_paragraph("No recipes discussed in this episode."))
    blocks.append(_divider())

    # Ingredients & Products
    blocks.append(_heading2("Ingredients & Products Mentioned"))
    blocks.extend(_bulleted_list(
        insights.ingredients_and_products,
        empty_text="No specific ingredients or products mentioned.",
    ))
    blocks.append(_divider())

    # Business & Marketing
    blocks.append(_heading2("Business & Marketing Insights"))
    blocks.extend(_bulleted_list(
        insights.business_and_marketing,
        empty_text="No business or marketing insights in this episode.",
    ))
    blocks.append(_divider())

    # Key Takeaways
    blocks.append(_heading2("Key Takeaways"))
    blocks.extend(_bulleted_list(
        insights.key_takeaways,
        empty_text="No standout takeaways noted.",
    ))
    blocks.append(_divider())

    # Original episode description
    blocks.append(_heading3("Original Episode Description"))
    desc = episode.description[:_NOTION_TEXT_LIMIT] if episode.description else "No description available."
    blocks.append(_paragraph(desc))

    return blocks


def _recipe_blocks(recipe: RecipeEntry) -> list[dict]:
    blocks = [_heading3(recipe.name)]
    details = []
    if recipe.style:
        details.append(f"Style: {recipe.style}")
    if recipe.og:
        details.append(f"OG: {recipe.og}")
    if recipe.fg:
        details.append(f"FG: {recipe.fg}")
    if recipe.yeast:
        details.append(f"Yeast: {recipe.yeast}")
    if recipe.grain_bill:
        details.append("Grain Bill:")
        details.extend([f"  • {g}" for g in recipe.grain_bill])
    if recipe.hop_schedule:
        details.append("Hop Schedule:")
        details.extend([f"  • {h}" for h in recipe.hop_schedule])
    if recipe.process_notes:
        details.append(f"Process: {recipe.process_notes}")

    blocks.extend(_bulleted_list(details))
    return blocks


# --- Block helpers ---

def _heading2(text: str) -> dict:
    return {"type": "heading_2", "heading_2": {"rich_text": [{"text": {"content": text[:_NOTION_TEXT_LIMIT]}}]}}


def _heading3(text: str) -> dict:
    return {"type": "heading_3", "heading_3": {"rich_text": [{"text": {"content": text[:_NOTION_TEXT_LIMIT]}}]}}


def _paragraph(text: str) -> dict:
    return {"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": text[:_NOTION_TEXT_LIMIT]}}]}}


def _callout(text: str, emoji: str = "📝") -> dict:
    return {
        "type": "callout",
        "callout": {
            "icon": {"type": "emoji", "emoji": emoji},
            "rich_text": [{"text": {"content": text[:_NOTION_TEXT_LIMIT]}}],
        },
    }


def _divider() -> dict:
    return {"type": "divider", "divider": {}}


def _bulleted_list(items: list[str], empty_text: str = "") -> list[dict]:
    if not items:
        return [_paragraph(empty_text)] if empty_text else []
    return [
        {
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"text": {"content": item[:_NOTION_TEXT_LIMIT]}}]},
        }
        for item in items
    ]
