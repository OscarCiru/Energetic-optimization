from datetime import datetime, timedelta

from src.policies.policy import Policy
from src.entities.entities_manager import EntitiesManager
from src.measurement import Measurement


class StandardPolicy(Policy):

    def __init__(self, entities_manager: EntitiesManager):
        super().__init__(entities_manager)
        pass

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

        generation: Measurement = self._generation(pvs, initial_datetime)
        consumption: Measurement = self._consumption(pocs, initial_datetime)

        #   Case 1: Consumption overcome generation.
        if generation.value < consumption.value / time_lapse:
            remaining: Measurement = Measurement(consumption.value / time_lapse - generation.value, 'kW')
            supplying_batteries: list = self._entities_manager.get_supplying_batteries(batteries)
            if supplying_batteries:
                for supplying_battery in supplying_batteries:
                    supplied_power: Measurement = supplying_battery.discharge(initial_datetime, final_datetime,
                                                                              remaining)
                    remaining.value -= supplied_power.value
                    if remaining.value == 0.0:
                        [battery.update_flowed_power(initial_datetime, final_datetime, remaining) for battery in
                         batteries]
                        [pod.update_flowed_power(initial_datetime, final_datetime, remaining) for pod in pods]
                        return
            supplying_pods: list = self._entities_manager.get_supplying_pods(pods, initial_datetime)
            for supplying_pod in supplying_pods:
                supplied_power: Measurement = supplying_pod.supply_power(initial_datetime, final_datetime, remaining)
                remaining.value -= supplied_power.value
                if remaining.value == 0.0:
                    [battery.update_flowed_power(initial_datetime, final_datetime, remaining) for battery in
                     batteries]
                    [pod.update_flowed_power(initial_datetime, final_datetime, remaining) for pod in pods]
                    return
        #   Case 2: Generation overcome consumption.
        if generation.value > consumption.value / time_lapse:
            remaining: Measurement = Measurement(generation.value - consumption.value / time_lapse, 'kW')
            demanding_batteries: list = self._entities_manager.get_demanding_batteries(batteries)
            if demanding_batteries:
                not_charged_power: Measurement = self._equal_batteries_charging(demanding_batteries, remaining,
                                                                                Measurement(0.0, remaining.units),
                                                                                initial_datetime, final_datetime)
                remaining.value -= remaining.value - not_charged_power.value
                if remaining.value == 0.0:
                    [battery.update_flowed_power(initial_datetime, final_datetime, remaining) for battery in
                     batteries]
                    [pod.update_flowed_power(initial_datetime, final_datetime, remaining) for pod in pods]
                    return
            for pod in pods:
                sold_power: Measurement = pod.receive_power(initial_datetime, final_datetime, remaining)
                remaining.value -= sold_power.value
                if remaining.value == 0.0:
                    [battery.update_flowed_power(initial_datetime, final_datetime, remaining) for battery in
                     batteries]
                    [pod.update_flowed_power(initial_datetime, final_datetime, remaining) for pod in pods]
                    return
        #   Case 3: Generation equal to consumption.
        [battery.update_flowed_power(initial_datetime, final_datetime, Measurement(0.0, consumption.units)) for battery
         in batteries]
        [pod.update_flowed_power(initial_datetime, final_datetime, Measurement(0.0, consumption.units)) for pod in pods]
        return
