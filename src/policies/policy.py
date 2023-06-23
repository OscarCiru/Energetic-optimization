from src.measurement import Measurement
from src.entities.entities_manager import EntitiesManager


class Policy:

    def __init__(self, entities_manager: EntitiesManager):
        self._entities_manager: EntitiesManager = entities_manager
        self._datetime_format: str = '%Y-%m-%d %H:%M:%S'

    def _generation(self, pvs: list, initial_datetime: str) -> Measurement:
        generation: Measurement = Measurement(0, 'kW')
        for pv in pvs:
            generation.value += pv.get_generation(initial_datetime).value
        return generation

    def _consumption(self, pocs: list, initial_datetime: str) -> Measurement:
        consumption: Measurement = Measurement(0, 'kWh')
        for poc in pocs:
            consumption.value += poc.get_consumption(initial_datetime).value
        return consumption

    def _purchase_price(self, pods: list, initial_datetime: str) -> Measurement:
        return Measurement(pods[0].get_purchase_price(initial_datetime).value, '€/kWh')

    def _equal_batteries_charging(self, demanding_batteries: list, available_power: Measurement,
                                  previous_charged_power: Measurement, initial_datetime: str,
                                  final_datetime: str) -> Measurement:
        if len(demanding_batteries) == 0 or available_power.value == 0.0:
            return available_power
        power: Measurement = Measurement(available_power.value, available_power.units)
        still_demanding_batteries: list = demanding_batteries.copy()
        power_to_charge: Measurement = Measurement(power.value / len(demanding_batteries), power.units)
        for battery in demanding_batteries:
            vacant_power: Measurement = Measurement(
                (battery.get_nominal_energy().value - battery.energy.value) / 0.25,
                power.units)
            max_input_power: Measurement = Measurement(
                battery.get_max_input_power().value - previous_charged_power.value, power.units)
            charged_power: Measurement = battery.charge(initial_datetime, final_datetime, power_to_charge)
            power.value -= charged_power.value
            if charged_power.value == vacant_power.value or charged_power.value == max_input_power.value:
                still_demanding_batteries.remove(battery)
        power = self._equal_batteries_charging(still_demanding_batteries, power, power_to_charge, initial_datetime,
                                               final_datetime)
        return power
