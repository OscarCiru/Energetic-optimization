import os
import pandas
from pandas import DataFrame
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

from src.entities.battery import Battery
from src.entities.photovoltaic_plate import PhotovoltaicPlate
from src.entities.point_of_grid_delivery import PointOfGridDelivery
from src.entities.point_of_consumption import PointOfConsumption
from src.measurement import Measurement


class Parser:

    def __init__(self):
        self.__meteo_datetime_format: str = '%Y-%m-%dT%H:%M'
        self.__datetime_format: str = '%Y-%m-%d %H:%M:%S'

    def convert_meteo_info_into_dataframe(self, meteo_info: dict) -> DataFrame:
        initial_date: datetime = datetime.strptime(meteo_info['hourly']['time'][0], self.__meteo_datetime_format)
        final_date: datetime = datetime.strptime(meteo_info['hourly']['time'][-1], self.__meteo_datetime_format)
        weather_variables: list = ['temperature_2m', 'direct_radiation', 'precipitation', 'relativehumidity_2m']
        weather_values: dict = meteo_info['hourly']
        weather_units: dict = meteo_info['hourly_units']

        dates: list = [initial_date]
        count: int = 1
        while dates[-1] != final_date+timedelta(minutes=45):
            dates.append(initial_date + timedelta(minutes=15 * count))
            count += 1

        result: DataFrame = DataFrame()
        for weather_variable in weather_variables:
            weather_info: DataFrame = DataFrame()
            values: list = [value for value in weather_values[weather_variable] for _ in range(4)]
            units: str = weather_units[weather_variable]
            weather_info['InitialDatetime'] = dates
            weather_info['FinalDatetime'] = weather_info['InitialDatetime'].apply(lambda x: x + timedelta(minutes=15))
            weather_info['Magnitude'] = weather_variable
            weather_info['MagnitudeValue'] = values
            weather_info['MagnitudeUnits'] = units
            result = pandas.concat([result, weather_info])

        result['MagnitudeUnits'] = result['MagnitudeUnits'].apply(lambda x: x.replace('Â', ''))

        return result

    def build_context_info(self, contracted_power: DataFrame, meteo_info: DataFrame) -> DataFrame:
        result: DataFrame = DataFrame()
        result['contracted_power'] = contracted_power['MagnitudeValue']
        weather_params: list = list(set(list(meteo_info['Magnitude'])))
        for weather_param in weather_params:
            result[weather_param] = meteo_info[meteo_info['Magnitude'] == weather_param]['MagnitudeValue']
        return result

    def filter_dataframe(self, data: DataFrame, initial_datetime: str, final_datetime: str) -> DataFrame:
        data_filtered: DataFrame = data[data['InitialDatetime'] >= initial_datetime]
        data_filtered: DataFrame = data_filtered[data_filtered['InitialDatetime'] <= final_datetime]
        return data_filtered

    def merge_simulation_data(self, initial_datetime: str, final_datetime: str, time_lapse: float, entities: list):
        initial_date: str = initial_datetime
        final_date: str = datetime.strftime(
            datetime.strptime(initial_date, self.__datetime_format) + timedelta(hours=time_lapse),
            self.__datetime_format)
        simulation: DataFrame = DataFrame()
        while initial_date <= final_datetime:
            for entity in entities:
                new_record: DataFrame = DataFrame()
                if type(entity) == Battery:
                    new_record = self.__build_battery_data(entity, initial_date, final_date)
                elif type(entity) == PhotovoltaicPlate:
                    new_record = self.__build_photovoltaic_plate_data(entity, initial_date, final_date)
                elif type(entity) == PointOfGridDelivery:
                    new_record = self.__build_point_of_grid_delivery_data(entity, initial_date, final_date)
                elif type(entity) == PointOfConsumption:
                    new_record = self.__build_point_of_consumption(entity, initial_date, final_date)
                simulation = pandas.concat([simulation, new_record])
            initial_date = final_date
            final_date = datetime.strftime(
                datetime.strptime(initial_date, self.__datetime_format) + timedelta(hours=time_lapse),
                self.__datetime_format)
        return simulation

    def calculate_cost(self, simulation: DataFrame, entities: list, time_lapse: float) -> Measurement:
        cost: Measurement = Measurement(0.0, '€')
        dates: list = list(set(list(simulation['InitialDatetime'])))
        pods: list = list(filter(lambda x: type(x) == PointOfGridDelivery, entities))
        for pod in pods:
            pod_consumption: DataFrame = simulation[simulation['EntityId'] == pod.get_id()]
            for date in dates:
                purchase_price: Measurement = pod.get_purchase_price(date)
                sale_price: Measurement = pod.get_sale_price()
                consumption: float = pod_consumption[pod_consumption['InitialDatetime'] == date][
                                         'MagnitudeValue'].iloc[0] * time_lapse
                if consumption >= 0.0:
                    cost.value += consumption * purchase_price.value
                else:
                    cost.value -= consumption * sale_price.value
        return cost

    def build_images(self, initial_datetime: str, final_datetime: str, time_lapse: float,
                     standard_simulation: DataFrame, optimized_simulation: DataFrame, purchase_prices: DataFrame,
                     output_path: str):
        dates: list = self.__get_dates_list(initial_datetime, final_datetime, time_lapse)
        self.__build_generation_image(standard_simulation, dates, output_path)
        self.__build_consumption_image(standard_simulation, optimized_simulation, dates, time_lapse, output_path)
        self.__build_batteries_and_prices_image(standard_simulation, optimized_simulation, purchase_prices, dates,
                                                output_path)
        return

    def __get_dates_list(self, initial_datetime: str, final_datetime: str, time_lapse: float) -> list:
        initial_date: datetime = datetime.strptime(initial_datetime, self.__datetime_format)
        final_date: datetime = datetime.strptime(final_datetime, self.__datetime_format)
        dates: list = [initial_date]
        count: int = 1
        while dates[-1] != final_date:
            dates.append(initial_date + timedelta(hours=time_lapse * count))
            count += 1
        dates = [datetime.strftime(date, self.__datetime_format) for date in dates]
        return dates

    def __build_battery_data(self, battery: Battery, initial_datetime: str, final_datetime: str) -> DataFrame:
        battery_power: float = list(self.filter_dataframe(battery.flowed_power, initial_datetime,
                                                          initial_datetime)['MagnitudeValue'])[0]
        stored_energy: float = list(self.filter_dataframe(battery.stored_energy, initial_datetime,
                                                          initial_datetime)['MagnitudeValue'])[0]
        battery_state_of_charge: float = (stored_energy / battery.get_nominal_energy().value) * 100
        battery_data: dict = {
            'InitialDatetime': initial_datetime,
            'FinalDatetime': final_datetime,
            'EntityId': battery.get_id(),
            'EntityType': 'battery',
            'Magnitude': ['power', 'state_of_charge'],
            'MagnitudeValue': [battery_power, battery_state_of_charge],
            'MagnitudeUnits': ['kW', '%']
        }
        return DataFrame(battery_data)

    def __build_photovoltaic_plate_data(self, pv: PhotovoltaicPlate, initial_datetime: str,
                                        final_datetime: str) -> DataFrame:
        pv_power: float = pv.get_generation(initial_datetime).value
        pv_data: dict = {
            'InitialDatetime': initial_datetime,
            'FinalDatetime': final_datetime,
            'EntityId': pv.get_id(),
            'EntityType': 'photovoltaic_plate',
            'Magnitude': ['power'],
            'MagnitudeValue': [pv_power],
            'MagnitudeUnits': ['kW']
        }
        return DataFrame(pv_data, index=[0])

    def __build_point_of_grid_delivery_data(self, pod: PointOfGridDelivery, initial_datetime: str,
                                            final_datetime: str) -> DataFrame:
        pod_power: float = list(self.filter_dataframe(pod.flowed_power, initial_datetime,
                                                      initial_datetime)['MagnitudeValue'])[0]
        battery_data: dict = {
            'InitialDatetime': initial_datetime,
            'FinalDatetime': final_datetime,
            'EntityId': pod.get_id(),
            'EntityType': 'point_of_grid_delivery',
            'Magnitude': ['power'],
            'MagnitudeValue': [pod_power],
            'MagnitudeUnits': ['kW']
        }
        return DataFrame(battery_data)

    def __build_point_of_consumption(self, poc: PointOfConsumption, initial_datetime: str,
                                     final_datetime: str) -> DataFrame:
        poc_energy: float = poc.get_consumption(initial_datetime).value
        battery_data: dict = {
            'InitialDatetime': initial_datetime,
            'FinalDatetime': final_datetime,
            'EntityId': poc.get_id(),
            'EntityType': 'point_of_consumption',
            'Magnitude': ['energy'],
            'MagnitudeValue': [poc_energy],
            'MagnitudeUnits': ['kWh']
        }
        return DataFrame(battery_data, index=[0])

    def __build_generation_image(self, standard_simulation: DataFrame, dates: list, output_path: str):
        pvs_data: DataFrame = standard_simulation[standard_simulation['EntityType'] == 'photovoltaic_plate']
        generation: list = []
        pv_ids: list = list(set(list(pvs_data['EntityId'])))
        for date in dates:
            datetime_generation: DataFrame = pvs_data[pvs_data['InitialDatetime'] == date]
            pv_generation: float = 0.0
            for pv_id in pv_ids:
                pv_generation += list(
                    datetime_generation[datetime_generation['EntityId'] == pv_id]['MagnitudeValue'])[0]
            generation.append(pv_generation)

        fig, ax = plt.subplots(figsize=(8, 3))

        ax.bar(dates, generation)

        ax.grid(True, which='both')
        ax.set_xticks([])
        ax.set_xlabel('Datetime')
        ax.set_ylabel('Generation (kW)')
        ax.set_title('Generation of the photovoltaic plates', fontweight='bold', fontsize=10)

        plt.savefig(os.path.join(output_path, 'Generation.png'), dpi=300)
        plt.clf()

    def __build_consumption_image(self, standard_simulation: DataFrame, optimized_simulation: DataFrame, dates: list,
                                  time_lapse: float, output_path: str):
        pocs_data: DataFrame = standard_simulation[standard_simulation['EntityType'] == 'point_of_consumption']
        standard_pods_data: DataFrame = standard_simulation[
            standard_simulation['EntityType'] == 'point_of_grid_delivery']
        optimized_pods_data: DataFrame = optimized_simulation[
            optimized_simulation['EntityType'] == 'point_of_grid_delivery']
        poc_ids: list = list(set(list(pocs_data['EntityId'])))
        pod_ids: list = list(set(list(standard_pods_data['EntityId'])))
        consumption: list = []
        standard_power: list = []
        optimized_power: list = []
        for date in dates:
            datetime_consumption: DataFrame = pocs_data[pocs_data['InitialDatetime'] == date]
            standard_datetime_power: DataFrame = standard_pods_data[standard_pods_data['InitialDatetime'] == date]
            optimized_datetime_power: DataFrame = optimized_pods_data[optimized_pods_data['InitialDatetime'] == date]
            poc_consumption: float = 0.0
            standard_pod_power: float = 0.0
            optimized_pod_power: float = 0.0
            for poc_id in poc_ids:
                poc_consumption += list(
                    datetime_consumption[datetime_consumption['EntityId'] == poc_id]['MagnitudeValue'])[0]
            consumption.append(poc_consumption)
            for pod_id in pod_ids:
                standard_pod_power += list(
                    standard_datetime_power[standard_datetime_power['EntityId'] == pod_id]['MagnitudeValue'])[0]
                optimized_pod_power += list(
                    optimized_datetime_power[optimized_datetime_power['EntityId'] == pod_id]['MagnitudeValue'])[0]
            standard_power.append(standard_pod_power)
            optimized_power.append(optimized_pod_power)
        standard_power = [element * time_lapse for element in standard_power]
        optimized_power = [element * time_lapse for element in optimized_power]

        fig, ax = plt.subplots(figsize=(8, 3))

        ax.bar(dates, consumption, color='orange')

        ax.grid(True, which='both')
        ax.set_xticks([])
        ax.set_xlabel('Datetime')
        ax.set_ylabel('Consumption (kWh)')
        ax.set_title('Consumption of the domain', fontweight='bold', fontsize=10)

        plt.savefig(os.path.join(output_path, 'DerConsumption.png'), dpi=300)
        plt.clf()

        fig, axs = plt.subplots(2, 1, figsize=(8, 5))

        axs[0].plot(dates, standard_power, color='darkblue', label='Standard consumption')
        axs[0].grid(True, which='both')
        axs[0].set_xticks([])
        axs[0].set_ylabel('Consumption (kWh)')
        axs[0].set_ylim(0, 210)
        axs[0].set_title('Standard consumption of the point of grid delivery', fontweight='bold', fontsize=10)

        axs[1].plot(dates, optimized_power, color='darkgreen', label='Optimized consumption')
        axs[1].grid(True, which='both')
        axs[1].set_xticks([])
        axs[1].set_xlabel('Datetime')
        axs[1].set_ylabel('Consumption (kWh)')
        axs[0].set_ylim(0, 210)
        axs[1].set_title('Optimized consumption of the point of grid delivery', fontweight='bold', fontsize=10)
        plt.tight_layout()

        plt.savefig(os.path.join(output_path, 'GridConsumption.png'), dpi=300)
        plt.clf()

    def __build_batteries_and_prices_image(self, standard_simulation: DataFrame, optimized_simulation: DataFrame,
                                           purchase_prices: DataFrame, dates: list, output_path: str):
        standard_batteries_data: DataFrame = standard_simulation[standard_simulation['EntityType'] == 'battery']
        optimized_batteries_data: DataFrame = optimized_simulation[optimized_simulation['EntityType'] == 'battery']
        purchase_prices_data: list = list(purchase_prices['MagnitudeValue'])
        purchase_prices_data.pop()
        battery_ids: list = list(set(list(standard_batteries_data['EntityId'])))
        standard_power: dict = {key: [] for key in battery_ids}
        standard_state_of_charge: dict = {key: [] for key in battery_ids}
        optimized_power: dict = {key: [] for key in battery_ids}
        optimized_state_of_charge: dict = {key: [] for key in battery_ids}
        for date in dates:
            standard_datetime_data: DataFrame = standard_batteries_data[
                standard_batteries_data['InitialDatetime'] == date]
            optimized_datetime_data: DataFrame = optimized_batteries_data[
                optimized_batteries_data['InitialDatetime'] == date]
            for battery_id in battery_ids:
                standard_battery_data: DataFrame = standard_datetime_data[
                    standard_datetime_data['EntityId'] == battery_id]
                standard_power[battery_id].append(
                    list(standard_battery_data[standard_battery_data['Magnitude'] == 'power']['MagnitudeValue'])[0])
                standard_state_of_charge[battery_id].append(
                    list(standard_battery_data[standard_battery_data['Magnitude'] == 'state_of_charge'][
                             'MagnitudeValue'])[0])
                optimized_battery_data: DataFrame = optimized_datetime_data[
                    optimized_datetime_data['EntityId'] == battery_id]
                optimized_power[battery_id].append(
                    list(optimized_battery_data[optimized_battery_data['Magnitude'] == 'power']['MagnitudeValue'])[0])
                optimized_state_of_charge[battery_id].append(
                    list(optimized_battery_data[optimized_battery_data['Magnitude'] == 'state_of_charge'][
                             'MagnitudeValue'])[0])

        for battery_id in battery_ids:
            fig, axs = plt.subplots(2, 1, figsize=(8, 5))

            axs0 = axs[0].twinx()

            axs[0].plot(dates, standard_power[battery_id], color='darkblue', label='Standard power')
            axs0.plot(dates, purchase_prices_data, color='red', label='Purchase price')
            axs[0].grid(True, which='both')
            axs[0].set_xticks([])
            axs[0].set_ylabel('Flowing power (kW)')
            axs0.set_ylabel('Purchase price (€/kWh)')
            axs[0].set_title('Standard flowing power for battery ' + battery_id + ' and purchase prices',
                             fontweight='bold', fontsize=10)
            lines = axs[0].get_lines() + axs0.get_lines()
            labels = [line.get_label() for line in lines]
            axs[0].legend(lines, labels, loc='lower right')

            axs[1].plot(dates, standard_state_of_charge[battery_id], color='darkgreen')
            axs[1].grid(True, which='both')
            axs[1].set_xticks([])
            axs[1].set_xlabel('Datetime')
            axs[1].set_ylabel('State of charge (%)')
            axs[1].set_title('Standard state of charge for battery ' + battery_id, fontweight='bold', fontsize=10)
            plt.tight_layout()

            plt.savefig(os.path.join(output_path, 'StandardBattery' + battery_id + 'Power.png'), dpi=300)
            plt.clf()

            fig, axs = plt.subplots(2, 1, figsize=(8, 5))

            axs0 = axs[0].twinx()

            axs[0].plot(dates, optimized_power[battery_id], color='darkblue', label='Optimized power')
            axs0.plot(dates, purchase_prices_data, color='red', label='Purchase price')
            axs[0].grid(True, which='both')
            axs[0].set_xticks([])
            axs[0].set_ylabel('Flowing power (kW)')
            axs0.set_ylabel('Purchase price (€/kWh)')
            axs[0].set_title('Optimized flowing power for battery ' + battery_id + ' and purchase prices',
                             fontweight='bold', fontsize=10)
            lines = axs[0].get_lines() + axs0.get_lines()
            labels = [line.get_label() for line in lines]
            axs[0].legend(lines, labels, loc='lower right')

            axs[1].plot(dates, optimized_state_of_charge[battery_id], color='darkgreen')
            axs[1].grid(True, which='both')
            axs[1].set_xticks([])
            axs[1].set_xlabel('Datetime')
            axs[1].set_ylabel('State of charge (%)')
            axs[1].set_title('Optimized state of charge for battery ' + battery_id, fontweight='bold', fontsize=10)
            plt.tight_layout()

            plt.savefig(os.path.join(output_path, 'OptimizedBattery' + battery_id + 'Power.png'), dpi=300)
            plt.clf()
