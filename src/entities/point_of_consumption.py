from pandas import DataFrame

from src.entities.entity import Entity
from src.measurement import Measurement


class PointOfConsumption(Entity):

    def __init__(self, poc_id: str):
        super().__init__(poc_id)
        self.id: str = poc_id
        self.__consumption: DataFrame = None

    def get_consumption(self, initial_datetime: str) -> Measurement:
        consumption: DataFrame = self.__consumption[self.__consumption['InitialDatetime'] == initial_datetime]
        return Measurement(list(consumption['MagnitudeValue'])[0], list(consumption['MagnitudeUnits'])[0])

    def get_all_consumption(self) -> DataFrame:
        return self.__consumption

    def update_consumption(self, consumption: DataFrame):
        self.__consumption = consumption
        return
