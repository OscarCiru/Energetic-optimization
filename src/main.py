import os
import json

import pandas
from pandas import DataFrame

from src.measurement import Measurement
from src.parser import Parser
from src.machine_learning.knn_model import KNNModel
from src.entities.entities_manager import EntitiesManager
from src.policies.standard_policy import StandardPolicy
from src.machine_learning.mesh_search import MeshSearch
from src.policies.optimizer_policy import OptimizerPolicy

__parent_path: str = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
#   Input paths.
__data_input_path: str = os.path.join(__parent_path, 'data', 'input')
__consumption_history: str = os.path.join(__data_input_path, 'consumption_history.csv')
__contracted_power_history: str = os.path.join(__data_input_path, 'contracted_power_history.csv')
__meteo_history: str = os.path.join(__data_input_path, 'meteo_history.json')
__contracted_power_data: str = os.path.join(__data_input_path, 'contracted_power_data.csv')
__meteo_data: str = os.path.join(__data_input_path, 'meteo_data.json')
__purchase_prices: str = os.path.join(__data_input_path, 'prices.csv')
__technical_characteristics: str = os.path.join(__data_input_path, 'technical_characteristics.csv')
#   Output_paths.
__data_output_path: str = os.path.join(__parent_path, 'data', 'output')
__standard_simulation: str = os.path.join(__data_output_path, 'standard_simulation.csv')
__optimized_simulation: str = os.path.join(__data_output_path, 'optimized_simulation.csv')

parser: Parser = Parser()
knn: KNNModel = KNNModel()

#   Read the files with the history information.

#   Consumption:
consumption_history: DataFrame = pandas.read_csv(__consumption_history, sep=';')
#   Convert the consumption values into float type.
consumption_history['MagnitudeValue'].apply(lambda x: float(x))
#   Contracted power:
contracted_power_history: DataFrame = pandas.read_csv(__contracted_power_history, sep=';')
#   Meteorological:
with open(__meteo_history) as json_data:
    meteo_info: dict = json.load(json_data)
#   Parse the meteorological info into a DataFrame.
meteo_history: DataFrame = parser.convert_meteo_info_into_dataframe(meteo_info)
#   Create the DataFrame that the KNN model accepts.
context_info_history: DataFrame = parser.build_context_info(contracted_power_history, meteo_history)

#   Train the KNN model.

try:
    knn.train(context_info_history, consumption_history)
except:
    print('The KNN model has not been trained because an error occurred.')

#   Read the files with the information necessary for the prediction.

#   Contracted power:
contracted_power_data: DataFrame = pandas.read_csv(__contracted_power_data, sep=';')
#   Meteorological:
with open(__meteo_data) as json_data:
    meteo_info: dict = json.load(json_data)
#   Parse the meteorological info into a DataFrame.
meteo_data: DataFrame = parser.convert_meteo_info_into_dataframe(meteo_info)
#   Create the DataFrame that the KNN model accepts.
context_info: DataFrame = parser.build_context_info(contracted_power_data, meteo_data)

#   Predict the energy consumption.

consumption_predict: DataFrame = knn.predict(context_info)
consumption_data: DataFrame = contracted_power_data.copy(deep=True)
consumption_data['Magnitude'] = 'consumption'
consumption_data['MagnitudeValue'] = consumption_predict
consumption_data['MagnitudeUnits'] = 'kWh'
#   Get the datetime range for the optimization.
initial_datetime: str = list(consumption_data['InitialDatetime'])[0]
fake_final_datetime: str = list(consumption_data['InitialDatetime'])[-1]
final_datetime: str = list(consumption_data['InitialDatetime'])[-2]
time_lapse: float = 0.25

#   Initialize the elements that are involved in the optimization process.

#   Get the technical characteristics of the equipments:
technical_characteristics: DataFrame = pandas.read_csv(__technical_characteristics, sep=';')
#   Get the energy prices.
purchase_prices: DataFrame = pandas.read_csv(__purchase_prices, sep=';')
sale_price: Measurement = Measurement(0.13, '€/kWh')
#   Filter the prices dataframe with optimization dates range.
filtered_purchase_prices: DataFrame = parser.filter_dataframe(purchase_prices, initial_datetime, fake_final_datetime)
#   Set the entities involved in the process.
entities_manager: EntitiesManager = EntitiesManager(technical_characteristics)
#   Update the photovoltaic plates.
[pv.update_generation(meteo_data) for pv in entities_manager.get_photovoltaic_plates()]
#   Update the points of grid delivery.
[pod.update_max_output_power(contracted_power_data) for pod in entities_manager.get_points_of_grid_delivery()]
[pod.update_purchase_prices(filtered_purchase_prices) for pod in entities_manager.get_points_of_grid_delivery()]
[pod.update_sale_price(sale_price) for pod in entities_manager.get_points_of_grid_delivery()]
#   Update the points of consumption.
[poc.update_consumption(consumption_data) for poc in entities_manager.get_points_of_consumption()]

#   Execute the standard policy.

standard_policy: StandardPolicy = StandardPolicy(entities_manager)
standard_policy.simulate(initial_datetime, final_datetime, time_lapse)

#   Persist the results.

entities: list = entities_manager.get_entities()
standard_simulation: DataFrame = parser.merge_simulation_data(initial_datetime, final_datetime, time_lapse, entities)
standard_simulation.to_csv(__standard_simulation, sep=';', index=False)

#   Get the cost associated to the standard simulation.

standard_simulation_cost: Measurement = parser.calculate_cost(standard_simulation, entities, time_lapse)

#   Do the Monte Carlo search.

mesh_carlo: MeshSearch = MeshSearch()
optimized_coefficients: dict = mesh_carlo.search(technical_characteristics, meteo_data, contracted_power_data,
                                                 filtered_purchase_prices, sale_price, consumption_data,
                                                 initial_datetime, final_datetime, time_lapse)
# optimized_coefficients: dict = {'consumption_slope': 0.4, 'purchase_price_slope': 0.55, 'consumption_low': 0.4,
#                                 'generation_low': 0.45, 'purchase_price_low': 0.4}

print('The best coefficients are: ', optimized_coefficients)

#   Execute the optimized policy

#   Reset the entities involved in the process.
entities_manager: EntitiesManager = EntitiesManager(technical_characteristics)
#   Update the photovoltaic plates.
[pv.update_generation(meteo_data) for pv in entities_manager.get_photovoltaic_plates()]
#   Update the points of grid delivery.
[pod.update_max_output_power(contracted_power_data) for pod in entities_manager.get_points_of_grid_delivery()]
[pod.update_purchase_prices(filtered_purchase_prices) for pod in entities_manager.get_points_of_grid_delivery()]
[pod.update_sale_price(sale_price) for pod in entities_manager.get_points_of_grid_delivery()]
#   Update the points of consumption.
[poc.update_consumption(consumption_data) for poc in entities_manager.get_points_of_consumption()]

optimized_policy: OptimizerPolicy = OptimizerPolicy(optimized_coefficients, entities_manager)
optimized_policy.simulate(initial_datetime, final_datetime, time_lapse)

#   Persist the results.

entities: list = entities_manager.get_entities()
optimized_simulation: DataFrame = parser.merge_simulation_data(initial_datetime, final_datetime, time_lapse, entities)
optimized_simulation.to_csv(__optimized_simulation, sep=';', index=False)

#   Get the cost associated to the standard simulation.

optimized_simulation_cost: Measurement = parser.calculate_cost(optimized_simulation, entities, time_lapse)

#   Print the cost of each policy.

print('Standard simulation cost: ', standard_simulation_cost.value)
print('Optimized simulation cost: ', optimized_simulation_cost.value)

#   Build the images of the result.

parser.build_images(initial_datetime, final_datetime, time_lapse, standard_simulation, optimized_simulation,
                    filtered_purchase_prices, __data_output_path)
