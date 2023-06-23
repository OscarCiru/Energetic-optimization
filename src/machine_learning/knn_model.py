import numpy
from pandas import DataFrame
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score


class KNNModel:

    def __init__(self):
        self.scaler: StandardScaler = StandardScaler()
        self.__knn: KNeighborsRegressor = None

    def train(self, context_info: DataFrame, consumption: DataFrame):
        #   Set the data as input (x) and output (y).
        x: DataFrame = context_info
        y: DataFrame = consumption['MagnitudeValue'].to_numpy()[:, numpy.newaxis]

        #   Normalize the information.
        x_scaled: DataFrame = self.scaler.fit_transform(x)

        #   Divide the information into training and validation.
        x_train, x_validation, y_train, y_validation = train_test_split(x_scaled, y, test_size=0.3, random_state=11)

        #   Apply cross validation to find the best value for k.
        k_values: list = list(range(1, 11))
        cv_scores: list = []
        for k in k_values:
            knn: KNeighborsRegressor = KNeighborsRegressor(n_neighbors=k)
            scores = cross_val_score(knn, x_train, y_train, cv=5, scoring='neg_mean_squared_error')
            cv_scores.append(-scores.mean())

        #   Take the value for k with the lower mean squared error.
        best_k: int = k_values[cv_scores.index(min(cv_scores))]
        print("The best value for k:", best_k)

        #   Train the model with the best value for k.
        self.__knn = KNeighborsRegressor(n_neighbors=best_k)
        self.__knn.fit(x_train, y_train)

        #   Make the predictions for the validation set of data.
        y_prediction = self.__knn.predict(x_validation)
        print('The R2 value of the KNN model trained:', r2_score(y_validation, y_prediction))

    def predict(self, context_info: DataFrame) -> DataFrame:
        #   Normalize the information.
        context_info_scaled: DataFrame = self.scaler.fit_transform(context_info)

        #   Make the prediction.
        prediction: DataFrame = self.__knn.predict(context_info_scaled)

        #   Return the result.
        return prediction
