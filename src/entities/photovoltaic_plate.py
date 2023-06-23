from pandas import DataFrame

from src.measurement import Measurement
from src.entities.entity import Entity


class PhotovoltaicPlate(Entity):

    def __init__(self, pv_id: str, surface: Measurement, efficiency: Measurement, max_output_power: Measurement):
        super().__init__(pv_id)
        self.id: str = pv_id
        self.__surface: Measurement = surface
        self.__efficiency: Measurement = efficiency
        self.__max_output_power: Measurement = max_output_power
        self.__generation: DataFrame = None

    def get_surface(self) -> Measurement:
        return self.__surface

    def get_efficiency(self) -> Measurement:
        return self.__efficiency

    def get_max_output_power(self) -> Measurement:
        return self.__max_output_power

    def get_generation(self, initial_datetime: str) -> Measurement:
        generation: DataFrame = self.__generation[self.__generation['InitialDatetime'] == initial_datetime]
        return Measurement(list(generation['MagnitudeValue'])[0], list(generation['MagnitudeUnits'])[0])

    def get_all_generation(self) -> DataFrame:
        return self.__generation

    def update_generation(self, meteo_info: DataFrame):
        generation: DataFrame = DataFrame()
        direct_radiation: DataFrame = meteo_info[meteo_info['Magnitude'] == 'direct_radiation']
        generation['InitialDatetime'] = direct_radiation['InitialDatetime']
        generation['FinalDatetime'] = direct_radiation['FinalDatetime']
        generation['Magnitude'] = 'generation'
        generation_values: list = []
        for record in range(len(generation)):
            generation_values.append(direct_radiation.iloc[record]['MagnitudeValue'] / 1000 * self.__surface.value *
                                     self.__efficiency.value / 100)
        generation['MagnitudeValue'] = generation_values
        generation['MagnitudeUnits'] = 'kW'
        self.__generation = generation
        return
