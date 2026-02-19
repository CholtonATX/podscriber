from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RecipeEntry(BaseModel):
    name: str
    style: Optional[str] = None
    grain_bill: Optional[list[str]] = None
    hop_schedule: Optional[list[str]] = None
    yeast: Optional[str] = None
    og: Optional[str] = None
    fg: Optional[str] = None
    process_notes: Optional[str] = None


class BrewingInsights(BaseModel):
    episode_summary: str
    brewing_techniques: list[str]
    recipes: list[RecipeEntry]
    ingredients_and_products: list[str]
    business_and_marketing: list[str]
    key_takeaways: list[str]


class Episode(BaseModel):
    number: int
    title: str
    published: datetime
    audio_url: str
    description: str
    podcast_name: str
