from pandas import DataFrame

from src.parser import Parser
from src.entities.entities_manager import EntitiesManager
from src.measurement import Measurement
from src.policies.optimizer_policy import OptimizerPolicy


class MeshSearch:

    def __init__(self):
        self.__parser: Parser = Parser()
        self.__lower_cost: Measurement = Measurement(1e100, '€')
        self.__consumption_coefficients: list = [x / 100 for x in range(40, 61, 5)]
        self.__purchase_price_coefficients: list = [x / 100 for x in range(40, 61, 5)]
        self.__consumption_low_coefficients: list = [x / 100 for x in range(40, 61, 5)]
        self.__generation_low_coefficients: list = [x / 100 for x in range(40, 61, 5)]
        self.__purchase_price_low_coefficients: list = [x / 100 for x in range(40, 61, 5)]
        self.__best_coefficients: dict = {}

    def search(self, technical_characteristics: DataFrame, meteo_data: DataFrame, contracted_power_data: DataFrame,
               filtered_purchase_prices: DataFrame, sale_price: Measurement, consumption_data: DataFrame,
               initial_datetime: str, final_datetime: str, time_lapse: float) -> dict:

        for consumption_coefficient in self.__consumption_coefficients:
            for purchase_price_coefficient in self.__purchase_price_coefficients:
                for consumption_low_coefficient in self.__consumption_low_coefficients:
                    for generation_low_coefficient in self.__generation_low_coefficients:
                        for purchase_price_low_coefficient in self.__purchase_price_low_coefficients:

                            entities_manager: EntitiesManager = self.__set_policy(
                                technical_characteristics, meteo_data, contracted_power_data, filtered_purchase_prices,
                                sale_price, consumption_data)

                            coefficients: dict = {
                                'consumption_slope': consumption_coefficient,
                                'purchase_price_slope': purchase_price_coefficient,
                                'consumption_low': consumption_low_coefficient,
                                'generation_low': generation_low_coefficient,
                                'purchase_price_low': purchase_price_low_coefficient
                            }
                            policy: OptimizerPolicy = OptimizerPolicy(coefficients, entities_manager)
                            policy.simulate(initial_datetime, final_datetime, time_lapse)

                            entities: list = entities_manager.get_entities()
                            simulation: DataFrame = self.__parser.merge_simulation_data(initial_datetime,
                                                                                        final_datetime, time_lapse,
                                                                                        entities)
                            simulation_cost: Measurement = self.__parser.calculate_cost(simulation, entities,
                                                                                        time_lapse)
                            
                            print('Coefficients:', coefficients)
                            print('Policy cost:', simulation_cost)

                            if simulation_cost.value < self.__lower_cost.value:
                                self.__lower_cost = simulation_cost
                                self.__best_coefficients = coefficients

        print('Best coefficients:', self.__best_coefficients)

        return self.__best_coefficients

    def __set_policy(self, technical_characteristics: DataFrame, meteo_data: DataFrame,
                     contracted_power_data: DataFrame, filtered_purchase_prices: DataFrame, sale_price: Measurement,
                     consumption_data: DataFrame) -> EntitiesManager:
        entities_manager: EntitiesManager = EntitiesManager(technical_characteristics)
        [pv.update_generation(meteo_data) for pv in entities_manager.get_photovoltaic_plates()]
        [pod.update_max_output_power(contracted_power_data) for pod in
         entities_manager.get_points_of_grid_delivery()]
        [pod.update_purchase_prices(filtered_purchase_prices) for pod in
         entities_manager.get_points_of_grid_delivery()]
        [pod.update_sale_price(sale_price) for pod in
         entities_manager.get_points_of_grid_delivery()]
        [poc.update_consumption(consumption_data) for poc in
         entities_manager.get_points_of_consumption()]
        return entities_manager
