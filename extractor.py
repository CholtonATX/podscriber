import anthropic

from logger import get_logger
from models import BrewingInsights, RecipeEntry

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an expert homebrewing analyst and podcast content extractor.
Your task is to analyze podcast transcripts focused on brewing, homebrewing, and craft beer,
and extract structured insights that are valuable to homebrewers and craft beer professionals.

Be specific and practical. When extracting recipes, capture as many measurable details as
possible (grain weights, hop additions with timing and amounts, yeast strains, temperatures,
gravities). For techniques, describe the actual process steps, not just the name.

If a category has no relevant content in the episode, return an empty list for that field.
Do not fabricate information not present in the transcript."""

EXTRACTION_TOOL = {
    "name": "extract_brewing_insights",
    "description": "Extract structured brewing insights from a podcast transcript",
    "input_schema": {
        "type": "object",
        "properties": {
            "episode_summary": {
                "type": "string",
                "description": "2-3 sentence summary of the episode covering the main topics discussed",
            },
            "brewing_techniques": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific brewing methods, processes, and tips mentioned. Each item is one technique described in 1-2 sentences.",
            },
            "recipes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "style": {"type": "string"},
                        "grain_bill": {"type": "array", "items": {"type": "string"}},
                        "hop_schedule": {"type": "array", "items": {"type": "string"}},
                        "yeast": {"type": "string"},
                        "og": {"type": "string"},
                        "fg": {"type": "string"},
                        "process_notes": {"type": "string"},
                    },
                    "required": ["name"],
                },
                "description": "Any beer recipes discussed in the episode",
            },
            "ingredients_and_products": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific hops, malts, yeast strains, adjuncts, equipment brands, or products mentioned by name",
            },
            "business_and_marketing": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Insights on taproom strategy, branding, distribution, pricing, or sales",
            },
            "key_takeaways": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The most important or memorable insights and direct quotes from the episode",
            },
        },
        "required": [
            "episode_summary",
            "brewing_techniques",
            "recipes",
            "ingredients_and_products",
            "business_and_marketing",
            "key_takeaways",
        ],
    },
}


def extract_insights(
    transcript: str,
    episode_title: str,
    episode_description: str,
    api_key: str,
) -> BrewingInsights:
    """Send transcript to Claude and extract structured brewing insights."""
    client = anthropic.Anthropic(api_key=api_key)

    user_message = (
        f"Episode Title: {episode_title}\n\n"
        f"Episode Description:\n{episode_description}\n\n"
        f"Transcript:\n{transcript}\n\n"
        "Please extract all brewing insights from this podcast episode using the "
        "extract_brewing_insights tool."
    )

    logger.info("Sending transcript to Claude for extraction")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": "extract_brewing_insights"},
        messages=[{"role": "user", "content": user_message}],
    )

    tool_use_block = next(b for b in response.content if b.type == "tool_use")
    data = tool_use_block.input

    recipes = [RecipeEntry(**r) for r in data.get("recipes", [])]
    return BrewingInsights(
        episode_summary=data.get("episode_summary", ""),
        brewing_techniques=data.get("brewing_techniques", []),
        recipes=recipes,
        ingredients_and_products=data.get("ingredients_and_products", []),
        business_and_marketing=data.get("business_and_marketing", []),
        key_takeaways=data.get("key_takeaways", []),
    )
