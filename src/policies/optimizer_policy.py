import os
import math
import pandas
from pandas import DataFrame
from datetime import datetime, timedelta

from src.policies.policy import Policy
from src.entities.entities_manager import EntitiesManager
from src.measurement import Measurement


class OptimizerPolicy(Policy):

    def __init__(self, coefficients: dict, entities_manager: EntitiesManager):
        super().__init__(entities_manager)

        self.__consumption_slope: float = coefficients['consumption_slope']
        self.__purchase_price_slope: float = coefficients['purchase_price_slope']
        self.__consumption_low: float = coefficients['consumption_low']
        self.__generation_low: float = coefficients['generation_low']
        self.__purchase_prices_low: float = coefficients['purchase_price_low']

        drivers_path: str = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir,
                                                         'data', 'input', 'drivers.csv'))
        drivers: DataFrame = pandas.read_csv(drivers_path, sep=';')
        fields: list = ['surplus', 'consumption_rise', 'purchase_price_rise', 'consumption_low', 'generation_low',
                        'purchase_price_low']
        self.__send_to_batteries: list = [list(x) for x in
                                          list(drivers[drivers['send_to_batteries'] == 1][fields].values)]
        self.__charge_from_pods: list = [list(x) for x in
                                         list(drivers[drivers['charge_from_pods'] == 1][fields].values)]
        self.__get_from_batteries: list = [list(x) for x in
                                           list(drivers[drivers['get_from_batteries'] == 1][fields].values)]
        self.__state: list = []

    def simulate(self, initial_datetime: str, final_datetime: str, time_lapse: float):
        initial_date: str = initial_datetime
        final_date: str = datetime.strftime(
            datetime.strptime(initial_date, self._datetime_format) + timedelta(hours=time_lapse), self._datetime_format)
        while initial_date <= final_datetime:
            self.__distribute(initial_date, final_date, time_lapse)
            initial_date = final_date
            final_date = datetime.strftime(
                datetime.strptime(initial_date, self._datetime_format) + timedelta(hours=time_lapse),
                self._datetime_format)
        return

    def __distribute(self, initial_datetime: str, final_datetime: str, time_lapse: float):
        batteries: list = self._entities_manager.get_batteries()
        pvs: list = self._entities_manager.get_photovoltaic_plates()
        pods: list = self._entities_manager.get_points_of_grid_delivery()
        pocs: list = self._entities_manager.get_points_of_consumption()

        current_consumption: Measurement = self._consumption(pocs, initial_datetime)
        next_consumption: Measurement = self._consumption(pocs, final_datetime)
        current_generation: Measurement = self._generation(pvs, initial_datetime)
        current_purchase_price: Measurement = self._purchase_price(pods, initial_datetime)
        next_purchase_price: Measurement = self._purchase_price(pods, final_datetime)

        consumption_slope: float = self.__slope(current_consumption, next_consumption)
        purchase_prices_slope: float = self.__slope(current_purchase_price, next_purchase_price)

        current_relative_consumption: float = (current_consumption.value - self.__consumption_range(pocs)[0]) / (
                    self.__consumption_range(pocs)[1] - self.__consumption_range(pocs)[0])
        current_relative_generation: float = (current_generation.value - self.__generation_range(pvs)[0]) / (
                self.__generation_range(pvs)[1] - self.__generation_range(pvs)[0])
        current_relative_purchase_price: float = \
            (current_purchase_price.value - self.__purchase_prices_range(pods)[0]) / (
                    self.__purchase_prices_range(pods)[1] - self.__purchase_prices_range(pods)[0])

        self.__state = [
            current_generation.value - current_consumption.value / time_lapse >= 0.0,
            consumption_slope >= self.__consumption_slope,
            purchase_prices_slope >= self.__purchase_price_slope,
            current_relative_consumption < self.__consumption_low,
            current_relative_generation < self.__generation_low,
            current_relative_purchase_price < self.__purchase_prices_low,
        ]

        if self.__state[0]:
            return self.__send_power(current_consumption, current_generation, batteries, pods, initial_datetime,
                                     final_datetime, time_lapse)

        return self.__get_power(current_consumption, current_generation, batteries, pods, initial_datetime,
                                final_datetime, time_lapse)

    def __send_power(self, consumption: Measurement, generation: Measurement, batteries: list, pods: list,
                     initial_datetime: str, final_datetime: str, time_lapse: float):
        remaining: Measurement = Measurement(generation.value - consumption.value / time_lapse, generation.units)
        demanding_batteries: list = self._entities_manager.get_demanding_batteries(batteries)

        if self.__state in self.__send_to_batteries:
            if demanding_batteries:
                not_charged_power: Measurement = self._equal_batteries_charging(demanding_batteries, remaining,
                                                                                Measurement(0.0, remaining.units),
                                                                                initial_datetime, final_datetime)
                remaining.value -= remaining.value - not_charged_power.value
                if remaining.value == 0.0:
                    [battery.update_flowed_power(initial_datetime, final_datetime, remaining) for battery in batteries]
                    [pod.update_flowed_power(initial_datetime, final_datetime, remaining) for pod in pods]
                    return

        power_per_pod: Measurement = Measurement(remaining.value / len(pods), remaining.units)
        for pod in pods:
            received_power: Measurement = pod.receive_power(initial_datetime, final_datetime, power_per_pod)
            remaining.value -= received_power.value

        [battery.update_flowed_power(initial_datetime, final_datetime, remaining) for battery in batteries]
        [pod.update_flowed_power(initial_datetime, final_datetime, remaining) for pod in pods]
        return

    def __get_power(self, consumption: Measurement, generation: Measurement, batteries: list, pods: list,
                    initial_datetime: str, final_datetime: str, time_lapse: float):
        remaining: Measurement = Measurement(consumption.value / time_lapse - generation.value, generation.units)
        supplying_batteries: list = self._entities_manager.get_supplying_batteries(batteries)
        demanding_batteries: list = self._entities_manager.get_demanding_batteries(batteries)

        if self.__state in self.__get_from_batteries:
            if supplying_batteries:
                for supplying_battery in supplying_batteries:
                    supplied_power: Measurement = supplying_battery.discharge(initial_datetime, final_datetime,
                                                                              remaining)
                    remaining.value -= supplied_power.value
                if remaining.value == 0.0:
                    [battery.update_flowed_power(initial_datetime, final_datetime, remaining) for battery in batteries]
                    [pod.update_flowed_power(initial_datetime, final_datetime, remaining) for pod in pods]
                    return

        power_per_pod: Measurement = Measurement(remaining.value / len(pods), remaining.units)
        for pod in pods:
            supplied_power: Measurement = pod.supply_power(initial_datetime, final_datetime, power_per_pod)
            remaining.value -= supplied_power.value

        if self.__state in self.__charge_from_pods:
            if demanding_batteries:
                available_power: Measurement = Measurement(0.0, remaining.units)
                for pod in pods:
                    available_power.value += pod.available_power(initial_datetime).value
                not_charged_power: Measurement = self._equal_batteries_charging(demanding_batteries, available_power,
                                                                                Measurement(0.0, remaining.units),
                                                                                initial_datetime, final_datetime)
                charged_power_per_pod: Measurement = Measurement(
                    (available_power.value - not_charged_power.value) / len(pods), remaining.units)
                [pod.update_flowed_power(initial_datetime, final_datetime, charged_power_per_pod) for pod in pods]

        [battery.update_flowed_power(initial_datetime, final_datetime, remaining) for battery in batteries]
        [pod.update_flowed_power(initial_datetime, final_datetime, remaining) for pod in pods]
        return

    def __slope(self, current: Measurement, following: Measurement) -> float:
        k: float = 0.72134752
        if current.value == 0.0 and following.value == 0:
            return 0.0
        if current.value == 0.0 and following.value != 0:
            return following.value
        if current.value != 0.0 and following.value == 0:
            return -current.value
        else:
            return k * math.log(current.value / following.value) + 0.5

    def __consumption_range(self, pocs: list) -> list:
        consumption: DataFrame = pocs[0].get_all_consumption()
        return [min(list(consumption['MagnitudeValue'])), max(list(consumption['MagnitudeValue']))]

    def __generation_range(self, pvs: list) -> list:
        generation: DataFrame = pvs[0].get_all_generation()
        return [min(list(generation['MagnitudeValue'])), max(list(generation['MagnitudeValue']))]

    def __purchase_prices_range(self, pods: list) -> list:
        purchase_prices: DataFrame = pods[0].get_all_purchase_prices()
        return [min(list(purchase_prices['MagnitudeValue'])), max(list(purchase_prices['MagnitudeValue']))]
