# imports
import pandas as pd
import numpy as np
%matplotlib inline
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error
from sklearn.metrics import mean_squared_error, mean_absolute_error
from scipy.stats import pearsonr
from math import sqrt
import os

# Perform the one-off intialisation for the prediction. The init code is run once when the endpoint is setup.
def init():
	global tokenizer, model

	model_dir = os.getenv('AZUREML_MODEL_DIR')
	if model_dir == None:
		model_dir = "./models/" # For local testing, change to where you are storing the model locally
    	
def run():
    for sensor in sensors:
        try:
            sensor_data = pd.read("")
            sensors = 
            
            # forecast
            future = model.make_future_dataframe(periods=14, freq='D')
            forecast = model.predict(future)

            # Plot the forecasted values along with uncertainty range
            fig = model.plot(forecast)
            plt.xlabel('Date')
            plt.ylabel('Value')
            plt.title('Prophet Forecast')

            # Save the current figure
            plot_file_path1 = sensor + "/" + sensor + "_prophet_forecast_plot.png"
            fig.savefig(plot_file_path1)

            # Close the figure to release resources
            plt.close(fig)

            # Plot the components of the forecast
            fig = model.plot_components(forecast)

            # Save the current figure
            plot_file_path2 = sensor + "/" + sensor + "_prophet_forecast_plot_components.png"
            fig.savefig(plot_file_path2)

            # Close the figure to release resources
            plt.close(fig)

            # Get the actual and predicted values
            actual_values = df['y'].tail(14).values  # Actual values for the last 14 days
            predicted_values = forecast['yhat'].tail(14).values  # Predicted values for the last 14 days

            # Calculate MAE, MSE, MAPE, and Pearson's correlation coefficient for the forecast
            def calculate_metrics(actual_values, predicted_values):
                mse = mean_squared_error(actual_values, predicted_values)
                mae = mean_absolute_error(actual_values, predicted_values)
                mape = np.mean(np.abs((actual_values - predicted_values) / actual_values)) * 100
                return mse, mae, mape

            # Calculate metrics
            mse, mae, mape = calculate_metrics(actual_values, predicted_values)
            rmse = sqrt(mean_squared_error(actual_values, predicted_values))
            # Calculate Pearson's correlation coefficient
            correlation_coefficient, _ = pearsonr(actual_values, predicted_values)

            metrics = {"MSE": [mse],
                "RMSE": [rmse],
                "MAE": [mae],
                "MAPE": [mape],
                "Pearson's correlation coefficient": [correlation_coefficient]
                }

            metrics_df = pd.DataFrame(metrics)


            fortnight_forecast = forecast.tail(14)
            fortnight_forecast['pred'] = np.expm1(fortnight_forecast['yhat'])
            fortnight_forecast['display_value'] = np.where(fortnight_forecast['pred'] > fortnight_forecast['yhat'], fortnight_forecast['pred'], fortnight_forecast['yhat'])
            sensor_row = sensor_data[sensor_data["Sensor Name"] == sensor].iloc[0]

            # Fill the first row of fortnight_forecast with sensor data
            fortnight_forecast.loc[0, "Sensor Centroid Latitude"] = sensor_row["Sensor Centroid Latitude"]
            fortnight_forecast.loc[0, "Sensor Centroid Longitude"] = sensor_row["Sensor Centroid Longitude"]
            fortnight_forecast = pd.concat([fortnight_forecast, metrics_df], axis=1)

            # save 14 day forecast
            fortnight_forecast.to_csv(sensor + "/" + sensor + '_forecast.csv', index=False)
        except Exception as e:
            print(f"{sensor} has error:", str(e))
            pass

	
        return outputs


if __name__ == '__main__':
	init()
	run()
