
class Entity:

    def __init__(self, entity_id: str):
        self.__id: str = entity_id

    def get_id(self) -> str:
        return self.__id
