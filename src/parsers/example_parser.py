import aiohttp
from src.utils.parsers import Parser, ParserFunctions
from src.schemas.parsers import LinkParsedTitle, ParsedTitle, ParsedTitleShort, ParsedGenre
from fastapi import HTTPException
from bs4 import BeautifulSoup


async def get_titles(page: int) -> list[ParsedTitleShort]:
    ...


async def get_title(title_id: str) -> ParsedTitle:
    ...


async def get_genres() -> list[ParsedGenre]:
    ...


async def get_genre(genre_website_id: str, page: int) -> list[ParsedTitleShort]:
    ...

functions = ParserFunctions(
    get_titles=get_titles, get_title=get_title, get_genres=get_genres, get_genre=get_genre)

parser = Parser(
    name="Example name",
    id="example_id",
    functions=functions
)
