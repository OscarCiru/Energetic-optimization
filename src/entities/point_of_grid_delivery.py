import pandas
from pandas import DataFrame

from src.measurement import Measurement
from src.entities.entity import Entity


class PointOfGridDelivery(Entity):

    def __init__(self, pod_id: str, max_input_power: Measurement):
        super().__init__(pod_id)
        self.id: str = pod_id
        self.__max_input_power: Measurement = max_input_power
        self.__max_output_power: DataFrame = None
        self.__purchase_prices: DataFrame = None
        self.__sale_price: Measurement = None
        self.flowed_power: DataFrame = DataFrame(columns=['InitialDatetime', 'FinalDatetime', 'Magnitude',
                                                          'MagnitudeValue', 'MagnitudeUnits'])

    def get_max_output_power(self) -> DataFrame:
        return self.__max_output_power

    def get_max_input_power(self) -> Measurement:
        return self.__max_input_power

    def get_purchase_price(self, initial_datetime: str) -> Measurement:
        purchase_prices: DataFrame = self.__purchase_prices[
            self.__purchase_prices['InitialDatetime'] == initial_datetime]
        return Measurement(list(purchase_prices['MagnitudeValue'])[0], list(purchase_prices['MagnitudeUnits'])[0])

    def get_all_purchase_prices(self) -> DataFrame:
        return self.__purchase_prices

    def get_sale_price(self) -> Measurement:
        return self.__sale_price

    def update_max_output_power(self, max_output_power: DataFrame):
        self.__max_output_power = max_output_power

    def update_purchase_prices(self, purchase_prices: DataFrame):
        self.__purchase_prices = purchase_prices

    def update_sale_price(self, sale_price: Measurement):
        self.__sale_price = sale_price

    def available_power(self, initial_datetime: str) -> Measurement:
        max_output_power: DataFrame = self.__max_output_power[
            self.__max_output_power['InitialDatetime'] == initial_datetime]
        if not self.flowed_power.empty and initial_datetime in list(self.flowed_power['InitialDatetime']):
            flowed_power: float = list(
                self.flowed_power[self.flowed_power['InitialDatetime'] == initial_datetime]['MagnitudeValue'])[0]
        else:
            flowed_power: float = 0.0
        return Measurement(list(max_output_power['MagnitudeValue'])[0] - flowed_power,
                           list(max_output_power['MagnitudeUnits'])[0])

    def supply_power(self, initial_datetime: str, final_datetime: str, power: Measurement) -> Measurement:
        max_output_power: Measurement = self.available_power(initial_datetime)
        supplied_power: Measurement = Measurement(min([max_output_power.value, power.value]), power.units)
        self.update_flowed_power(initial_datetime, final_datetime, supplied_power)
        return supplied_power

    def receive_power(self, initial_datetime: str, final_datetime: str, power: Measurement) -> Measurement:
        max_input_power: float = self.__max_input_power.value
        received_power: Measurement = Measurement(min([max_input_power, power.value]), power.units)
        self.update_flowed_power(initial_datetime, final_datetime, Measurement(-received_power.value, power.units))
        return received_power

    def update_flowed_power(self, initial_datetime: str, final_datetime: str, power: Measurement):
        if initial_datetime in list(self.flowed_power['InitialDatetime']):
            record: int = list(self.flowed_power['InitialDatetime']).index(initial_datetime)
            self.flowed_power.at[record, 'MagnitudeValue'] += power.value
            return
        flowing_power: dict = {
            'InitialDatetime': initial_datetime,
            'FinalDatetime': final_datetime,
            'Magnitude': 'power',
            'MagnitudeValue': power.value,
            'MagnitudeUnits': power.units
        }
        new_record: DataFrame = DataFrame(flowing_power, index=[0])
        self.flowed_power = pandas.concat([self.flowed_power, new_record])
        self.flowed_power.reset_index(drop=True, inplace=True)
        return
