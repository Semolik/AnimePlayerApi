from fastapi import APIRouter

class Parser:
    def __init__(self, *, id: str, name: str, title_id_type: type = str) -> None:
        self.name = id
        self.title_id_type = title_id_type
        self.router = APIRouter(prefix=f'/{id}', tags=[f'{name} parser'])
        self.add_endpoint('/titles', self.get_titles)
        self.add_endpoint('/titles/{id}', self.get_title_type_wrapper())
        self.add_endpoint('/genres', self.get_genres)
        self.add_endpoint('/genres/{genre}', self.get_genre)
    
    def add_endpoint(self, path: str, endpoint_function, method: str = "GET"):
        if method == "GET":
            self.router.get(path)(endpoint_function)
        elif method == "POST":
            self.router.post(path)(endpoint_function)
    
    async def get_title(self, id: str | int):
        pass

    def get_title_type_wrapper(self):
        async def get_title_by_id(id: self.title_id_type):
            return await self.get_title(id=id)
        return get_title_by_id
    
    async def get_titles(self, page: int):
        pass

    async def get_genres(self, page: int):
        pass

    async def get_genre(self, genre: str):
        pass