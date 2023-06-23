import pandas
from pandas import DataFrame

from src.measurement import Measurement
from src.entities.entity import Entity


class Battery(Entity):

    def __init__(self, battery_id: str, nominal_energy: Measurement, max_input_power: Measurement,
                 max_output_power: Measurement, energy: Measurement = None):
        super().__init__(battery_id)
        self.__id: str = battery_id
        self.__nominal_energy: Measurement = nominal_energy
        self.__max_input_power: Measurement = max_input_power
        self.__max_output_power: Measurement = max_output_power
        self.energy: Measurement = energy if energy is not None else Measurement(0.0, nominal_energy.units)
        self.flowed_power: DataFrame = DataFrame(columns=['InitialDatetime', 'FinalDatetime', 'Magnitude',
                                                          'MagnitudeValue', 'MagnitudeUnits'])
        self.stored_energy: DataFrame = DataFrame(columns=['InitialDatetime', 'FinalDatetime', 'Magnitude',
                                                           'MagnitudeValue', 'MagnitudeUnits'])

    def get_nominal_energy(self) -> Measurement:
        return self.__nominal_energy

    def get_max_input_power(self) -> Measurement:
        return self.__max_input_power

    def get_max_output_power(self) -> Measurement:
        return self.__max_output_power

    def available_power(self) -> Measurement:
        stored_power: float = self.energy.value / 0.25
        max_output_power: float = self.__max_input_power.value
        return Measurement(min([stored_power, max_output_power]), self.__max_input_power.units)

    def charge(self, initial_datetime: str, final_datetime: str, power: Measurement) -> Measurement:
        stored_power: float = self.energy.value / 0.25
        vacant_power: float = self.__nominal_energy.value / 0.25 - stored_power
        max_input_power: float = self.__max_input_power.value
        charged_power: Measurement = Measurement(min([vacant_power, max_input_power]), power.units)
        self.update_flowed_power(initial_datetime, final_datetime, charged_power)
        return charged_power

    def discharge(self, initial_datetime: str, final_datetime: str, power: Measurement) -> Measurement:
        available_power: Measurement = self.available_power()
        discharged_power: Measurement = Measurement(min([available_power.value, power.value]), power.units)
        self.update_flowed_power(initial_datetime, final_datetime, Measurement(-discharged_power.value, power.units))
        return discharged_power

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
        self.__update_stored_energy(initial_datetime, final_datetime, power)
        return

    def __update_stored_energy(self, initial_datetime: str, final_datetime: str, power: Measurement):
        self.energy.value += power.value * 0.25
        if initial_datetime in list(self.stored_energy['InitialDatetime']):
            record: int = list(self.stored_energy['InitialDatetime']).index(initial_datetime)
            self.stored_energy.at[record, 'MagnitudeValue'] += power.value * 0.25
            return
        previous_record: float = list(self.stored_energy['MagnitudeValue'])[-1] if list(
            self.stored_energy['MagnitudeValue']) else 0.0
        storing_energy: dict = {
            'InitialDatetime': initial_datetime,
            'FinalDatetime': final_datetime,
            'Magnitude': 'energy',
            'MagnitudeValue': power.value * 0.25 + previous_record,
            'MagnitudeUnits': 'kWh'
        }
        new_record: DataFrame = DataFrame(storing_energy, index=[0])
        self.stored_energy = pandas.concat([self.stored_energy, new_record])
        self.stored_energy.reset_index(drop=True, inplace=True)
        return
