import re
from uuid import UUID
import aiohttp
import requests
from src.schemas.parsers import Episode, Genre, ParsedGenre, ParsedEpisode, ParsedLink, ParsedTitle, ParsedTitleShort, ParsedTitlesPage, TitlesPage
from src.redis.services import CacheService
from src.utils.parsers import Parser, ParserFunctions
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from src.db.session import AsyncSession, async_session_maker
from src.core.config import settings
from bs4 import BeautifulSoup
from src.crud.genres_crud import GenresCrud
from typing import List
import hashlib
from src.db.session import get_async_session_context
WEBSITE_URL = "https://anidub.pro"
API_URL = "https://isekai.anidub.fun"
LINK_SPLITTER = "~"

kinds = {
    "anime_tv": "tv",
    "anime_ona": "ona",
    "anime_ova": "ova",
    "anime_movie": "movie",
}


async def get_main_page(session: aiohttp.ClientSession) -> list[ParsedTitleShort]:
    async with session.get(f'{API_URL}/mobile-api.php?name=main_posts') as response:
        titles_json = await response.json()
        titles = []
        for title in titles_json:
            xfields = title['xfields'].split('||')
            genres_names = []
            img = None
            if xfields:
                for xfield in xfields:
                    parts = xfield.split('|')
                    if 'genre' == parts[0]:
                        genres_names = parts[1].split(', ')
                    if 'upposter2' == parts[0]:
                        img = f'{WEBSITE_URL}/uploads/posts/{parts[1].split("&")[0]}'
            titles.append(ParsedTitleShort(
                id_on_website=title['id'],
                name=get_original_title(title['title']),
                image_url=img,
                en_name=get_en_title(title['title']),
                additional_info=series_from_title(title['title']),
                poster=img,
                genres_names=genres_names
            ))
        return titles


async def get_titles(page: int) -> ParsedTitlesPage:
    async with aiohttp.ClientSession() as session:
        url = WEBSITE_URL
        if page > 1:
            url += f'/page/{page}/'
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            pages_count = get_pages_count(soup)
            titles = get_titles_from_page(soup) if page > 1 else await get_main_page(session)
            if not titles or not pages_count:
                raise HTTPException(
                    status_code=404, detail="Page not found on anidub.")
            return ParsedTitlesPage(
                titles=titles,
                total_pages=pages_count
            )


def get_original_title(name: str) -> str:
    return name.split(" /")[0]


def get_en_title(name: str) -> str:
    first = name.split(" /")
    if len(first) == 1:
        return None
    second = first[1].split(" [")
    en_name = second[0].strip()
    if en_name.endswith('.'):
        en_name = en_name[:-1]
    return en_name


def series_from_title(name: str) -> str:
    first = name.split(" /")
    if len(first) == 1:
        return None
    second = first[1].split(" [")
    if len(second) == 1:
        return None
    return second[1][:-1]


def get_title_data(th_item: BeautifulSoup) -> ParsedTitleShort:
    th_in = th_item.select_one('.th-in')
    poster = th_in.select(
        '.th-img > img')[0].get('src').replace('thumbs/', '')
    poster = (poster if 'http' in poster else WEBSITE_URL+poster)
    id_on_website = th_in.get('href').split('/')[4].split('.')[0].split('-')[0]
    th_title = th_in.select_one('.th-title')
    name = get_original_title(th_title.text)
    en_name = get_en_title(th_title.text)
    series = series_from_title(th_title.text)
    return ParsedTitleShort(
        id_on_website=id_on_website,
        name=name,
        image_url=poster,
        en_name=en_name,
        additional_info=series,
        poster=poster
    )


def get_titles_from_page(soup: BeautifulSoup) -> list[ParsedTitleShort]:
    data = soup.select_one('#dle-content')
    if not data:
        raise HTTPException(
            status_code=500, detail="Can't get titles from page")
    parsed_titles = []
    titles = data.select('.th-item')
    for title in titles:
        parsed_titles.append(get_title_data(title))
    return parsed_titles


def get_pages_count(soup: BeautifulSoup):
    dle_content = soup.select_one('#dle-content')
    if not dle_content:
        return
    pagination = dle_content.select(
        'div.bottom-nav > div.pagi-nav > div.navigation > a')
    if not pagination:
        return
    return int(pagination[-1].text)


async def get_series_data(soup: BeautifulSoup, session: aiohttp.ClientSession) -> list[ParsedEpisode]:
    player = soup.select_one('.fplayer')
    if player:
        tabs_sel = player.select_one('.tabs-sel')
        if tabs_sel:
            tabs = tabs_sel.select('span')
            if tabs:
                link = tabs[0].get('data')
                is_m3u8 = False
                if 'https://player.ladonyvesna2005.info' in link:
                    async with session.get(link) as response:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        tabs = soup.select('.tabs-sel span')
                        is_m3u8 = True
                return [
                    ParsedEpisode(
                        is_m3u8=is_m3u8,
                        number=int(re.search(r'\d+', tab.text).group()),
                        name=tab.text,
                        links=[ParsedLink(
                            name='playlist', link=tab.get('data'))]
                    ) for tab in tabs
                ]
    return []


async def get_title(title_id: str) -> ParsedTitle:
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{WEBSITE_URL}/index.php', params={'newsid': title_id}) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            data = soup.select_one('.wrap > .wrap-main')
            if not data:
                raise HTTPException(
                    status_code=500, detail="Can't get title from page")
            fright = data.select_one('.fright')
            title_block = fright.select_one('h1')
            title_name = title_block.text
            name = get_original_title(title_name)
            en_name = get_en_title(title_name)
            series = series_from_title(title_name)
            fleft = data.select_one('.fleft')
            poster = fleft.select_one('.fposter > img').get('src')
            poster = (poster if 'http' in poster else WEBSITE_URL+poster)
            description = fright.select_one('.fdesc')
            description = description.text.replace(
                '\n', '') if description else None
            flist = fright.select('.flist > li')

            links = fright.select('.fmeta > span > a')
            year = None
            for link in links:
                href = link.get('href')
                if not href:
                    continue
                if 'year' in href.split('/'):
                    year = link.text
                    break
            kind = None
            if links:
                kind_link = links[-1]
                if kind_link:
                    kind_name = kind_link.get('href').split('/')[-1]
                    kind = kinds.get(kind_name)
            genres_names = []
            if flist:
                for flist_item in flist:
                    block_name = flist_item.select_one('span')
                    if block_name and block_name.text == 'Жанр:':
                        genres_names = [genre.text
                                        for genre in flist_item.select('a')]
                        break

            series_data = await get_series_data(data, session)
            episodes_message = None
            if not series_data:
                episodes_message_container = soup.select_one(
                    '.fplayer .anidub__info_mess')
                if episodes_message_container:
                    episodes_message = episodes_message_container.text
            recommendations = data.select(
                '.sect > .sect-content > .th-item')
            recommended_titles = [
                get_title_data(
                    recommendation) for recommendation in recommendations]
            return ParsedTitle(
                id_on_website=title_id,
                name=name,
                en_name=en_name,
                episodes_list=series_data,
                series_info=series,
                image_url=poster,
                year=year,
                description=description,
                genres_names=genres_names,
                recommended_titles=recommended_titles,
                kind=kind,
                episodes_message=episodes_message
            )


async def get_genre(genre_website_id: str, page: int) -> ParsedTitlesPage:
    async with aiohttp.ClientSession() as session:
        url = f'{WEBSITE_URL}/xfsearch/genre/{requests.utils.requote_uri(genre_website_id)}/'
        if page > 1:
            url += f'page/{page}/'
        async with session.get(url) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            titles = get_titles_from_page(soup)
            pages_count = get_pages_count(soup)

            if not titles:
                raise HTTPException(
                    status_code=404, detail="Page not found on anidub.")
            return ParsedTitlesPage(
                titles=titles,
                total_pages=pages_count or 1
            )

functions = ParserFunctions(
    get_titles=get_titles, get_title=get_title, get_genres=None, get_genre=get_genre)


class AnidubParser(Parser):
    async def update_genres(self, service: CacheService, raise_error: bool = False) -> List[ParsedGenre]:
        async with get_async_session_context() as db:
            genres = await GenresCrud(db).get_genres(parser_id=self.parser_id)
            return [ParsedGenre.model_validate(genre) for genre in genres]

    async def get_genres(self, background_tasks: BackgroundTasks, db: AsyncSession) -> List[Genre]:
        genres = await GenresCrud(db).get_genres(parser_id=self.parser_id)
        return genres

    async def _prepare_titles(self, titles_page: ParsedTitlesPage, db: AsyncSession, background_tasks: BackgroundTasks) -> TitlesPage:
        for title in titles_page.titles:
            if not title.genres_names:
                continue
            for genre_name in title.genres_names:
                await get_db_genre(db=db, genre_name=genre_name)
        return await super()._prepare_titles(titles_page, db, background_tasks)

    async def prepare_episode(self, db_episode: Episode, parsed_episode: ParsedEpisode, progress: int, db: AsyncSession, service: CacheService) -> Episode:
        link = parsed_episode.links[0].link
        if parsed_episode.is_m3u8:
            link_hash = hashlib.md5(link.encode()).hexdigest()
            await service.set_link_by_hash(link_hash, link)
            result_link = f'https://player.ladonyvesna2005.info/vid.php?v=/{link}'
        else:
            result_link = f'{settings.API_V1_STR}/parsers/{self.parser_id}/episode?link_hash={link_hash}'
        return Episode(
            id=db_episode.id,
            name=db_episode.name,
            links=[
                ParsedLink(
                    name=parsed_episode.links[0].name,
                    link=result_link
                ),
            ],
            number=db_episode.number,
            image_url=parsed_episode.preview,
            progress=progress,
            is_m3u8=True
        )

    async def get_episode(self, link_hash: str) -> StreamingResponse:
        raise NotImplementedError
        service = await self.get_service()
        link = await service.get_link_by_hash(link_hash)
        if not link:
            raise HTTPException(
                status_code=404, detail="Link not found")
        content = await service.get_link_content(link)
        if content:
            return content

        async with aiohttp.ClientSession() as session:
            async with session.get(link) as response:
                html = await response.text()
                p = next(re.finditer(r"\/v\/.+\d+.mp4", html), None)
                if not p:
                    raise HTTPException(
                        status_code=404, detail="Link not found")
                file_url = 'https://video.sibnet.ru' + p.group(0)
                async with session.head(file_url, headers={'Referer': link}) as response:
                    if response.status == 200:
                        content = await response.text()
                    elif response.status == 302:
                        content = 'http:' + response.headers['Location']

    def get_custom_router(self):
        api_router = APIRouter()
        api_router.add_api_route(
            path="/episode", endpoint=self.get_episode, methods=["GET"])
        return api_router

    async def _prepare_genres_names(self, genres_names: List[str], db: AsyncSession, background_tasks: BackgroundTasks) -> List[Genre]:
        genres = []
        for genre_name in genres_names:
            genre = await get_db_genre(db=db, genre_name=genre_name)
            genres.append(genre)
        return genres


parser = AnidubParser(
    name="Anidub",
    id="anidub",
    functions=functions
)


async def get_db_genre(db: AsyncSession, genre_name: str) -> Genre:
    db_genre = await GenresCrud(db).get_genre_by_website_id(website_id=genre_name)
    if not db_genre:
        db_genre = await GenresCrud(db).create_genre(genre=ParsedGenre(
            name=genre_name, id_on_website=genre_name
        ), parser_id=parser.parser_id)
    return db_genre
