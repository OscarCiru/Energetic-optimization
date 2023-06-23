from pandas import DataFrame

from src.measurement import Measurement
from src.entities.battery import Battery
from src.entities.photovoltaic_plate import PhotovoltaicPlate
from src.entities.point_of_grid_delivery import PointOfGridDelivery
from src.entities.point_of_consumption import PointOfConsumption


class EntitiesManager:

    def __init__(self, entities_info: DataFrame):
        self.__entities: list = self.__load(entities_info)

    def get_entities(self) -> list:
        return self.__entities

    def get_batteries(self) -> list:
        return list(filter(lambda x: type(x) == Battery, self.__entities))

    def get_photovoltaic_plates(self) -> list:
        return list(filter(lambda x: type(x) == PhotovoltaicPlate, self.__entities))

    def get_points_of_grid_delivery(self) -> list:
        return list(filter(lambda x: type(x) == PointOfGridDelivery, self.__entities))

    def get_points_of_consumption(self) -> list:
        return list(filter(lambda x: type(x) == PointOfConsumption, self.__entities))

    def get_supplying_batteries(self, batteries: list) -> list:
        supplying_batteries: list = []
        for battery in batteries:
            if self.__is_supplying_battery(battery):
                supplying_batteries.append(battery)
        return supplying_batteries

    def get_demanding_batteries(self, batteries: list) -> list:
        demanding_batteries: list = []
        for battery in batteries:
            if self.__is_demanding_battery(battery):
                demanding_batteries.append(battery)
        return demanding_batteries

    def get_supplying_pods(self, pods: list, initial_datetime: str) -> list:
        supplying_pods: list = []
        for pod in pods:
            if self.__is_supplying_pod(pod, initial_datetime):
                supplying_pods.append(pod)
        return supplying_pods

    def __load(self, entities_info: DataFrame) -> list:
        batteries: list = self.__set_batteries(entities_info)
        pvs: list = self.__set_photovoltaic_plates(entities_info)
        pods: list = self.__set_points_of_grid_delivery(entities_info)
        pocs: list = self.__set_points_of_consumption(entities_info)
        entities = batteries + pvs + pods + pocs
        return entities

    def __set_batteries(self, entities_info: DataFrame) -> list:
        batteries_info: DataFrame = entities_info[entities_info['Entity'] == 'battery']
        battery_ids: list = list(set(list(batteries_info['Id'])))
        batteries: list = []
        for battery_id in battery_ids:
            battery_info: DataFrame = batteries_info[batteries_info['Id'] == battery_id]
            nominal_energy: Measurement = Measurement(
                float(battery_info[battery_info['Magnitude'] == 'nominal_energy']['MagnitudeValue'].iloc[0]),
                str(battery_info[battery_info['Magnitude'] == 'nominal_energy']['MagnitudeUnits'].iloc[0]))
            max_input_power: Measurement = Measurement(
                float(battery_info[battery_info['Magnitude'] == 'max_input_power']['MagnitudeValue'].iloc[0]),
                str(battery_info[battery_info['Magnitude'] == 'max_input_power']['MagnitudeUnits'].iloc[0]))
            max_output_power: Measurement = Measurement(
                float(battery_info[battery_info['Magnitude'] == 'max_output_power']['MagnitudeValue'].iloc[0]),
                str(battery_info[battery_info['Magnitude'] == 'max_output_power']['MagnitudeUnits'].iloc[0]))
            batteries.append(Battery(str(battery_id), nominal_energy, max_input_power, max_output_power))
        return batteries

    def __set_photovoltaic_plates(self, entities_info: DataFrame) -> list:
        pvs_info: DataFrame = entities_info[entities_info['Entity'] == 'photovoltaic_plate']
        pv_ids: list = list(set(list(pvs_info['Id'])))
        pvs: list = []
        for pv_id in pv_ids:
            pv_info: DataFrame = pvs_info[pvs_info['Id'] == pv_id]
            surface: Measurement = Measurement(
                float(pv_info[pv_info['Magnitude'] == 'surface']['MagnitudeValue'].iloc[0]),
                str(pv_info[pv_info['Magnitude'] == 'surface']['MagnitudeUnits'].iloc[0]))
            efficiency: Measurement = Measurement(
                float(pv_info[pv_info['Magnitude'] == 'efficiency']['MagnitudeValue'].iloc[0]),
                str(pv_info[pv_info['Magnitude'] == 'efficiency']['MagnitudeUnits'].iloc[0]))
            max_output_power: Measurement = Measurement(
                float(pv_info[pv_info['Magnitude'] == 'max_output_power']['MagnitudeValue'].iloc[0]),
                str(pv_info[pv_info['Magnitude'] == 'max_output_power']['MagnitudeUnits'].iloc[0]))
            pv: PhotovoltaicPlate = PhotovoltaicPlate(str(pv_id), surface, efficiency, max_output_power)
            pvs.append(pv)
        return pvs

    def __set_points_of_grid_delivery(self, entities_info: DataFrame) -> list:
        pods_info: DataFrame = entities_info[entities_info['Entity'] == 'point_of_grid_delivery']
        pod_ids: list = list(set(list(pods_info['Id'])))
        pods: list = []
        for pod_id in pod_ids:
            pod_info: DataFrame = pods_info[pods_info['Id'] == pod_id]
            max_input_power: Measurement = Measurement(
                float(pod_info[pod_info['Magnitude'] == 'max_input_power']['MagnitudeValue'].iloc[0]),
                str(pod_info[pod_info['Magnitude'] == 'max_input_power']['MagnitudeUnits'].iloc[0]))
            pod: PointOfGridDelivery = PointOfGridDelivery(str(pod_id), max_input_power)
            pods.append(pod)
        return pods

    def __set_points_of_consumption(self, entities_info: DataFrame) -> list:
        pocs_info: DataFrame = entities_info[entities_info['Entity'] == 'point_of_consumption']
        poc_ids: list = list(set(list(pocs_info['Id'])))
        pocs: list = []
        for poc_id in poc_ids:
            poc: PointOfConsumption = PointOfConsumption(str(poc_id))
            pocs.append(poc)
        return pocs

    def __is_supplying_battery(self, battery: Battery) -> bool:
        available_power: Measurement = battery.available_power()
        if available_power.value > 0.0:
            return True
        return False

    def __is_demanding_battery(self, battery: Battery) -> bool:
        stored_energy: Measurement = battery.energy
        if stored_energy.value < battery.get_nominal_energy().value:
            return True
        return False

    def __is_supplying_pod(self, pod: PointOfGridDelivery, initial_datetime: str) -> bool:
        available_power: Measurement = pod.available_power(initial_datetime)
        if available_power.value > 0.0:
            return True
        return False
