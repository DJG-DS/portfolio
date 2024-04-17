import streamlit as st
import pandas as pd
import smopy
import matplotlib.pyplot as plt

# Load the sensor data
sensor_df = pd.read_csv("master.csv")

# Get unique sensor names
sensor = sensor_df["Sensor Name"].unique()
sensor_list = sensor.tolist()

# Add "All Sensors" to the beginning of the list
sensor_all = ["All Sensors"]
sensor_names = sensor_all + sensor_list

# Streamlit app
st.title('PM2.5 levels in Newcastle')
selected_sensor = st.selectbox('Select a sensor:', sensor_names)

try:
    # Display images and metrics for the selected sensor
    if selected_sensor != 'All Sensors':
        image_path_plot = f"{selected_sensor}/{selected_sensor}_prophet_forecast_plot.png"
        image_path_components = f"{selected_sensor}/{selected_sensor}_prophet_forecast_plot_components.png"
        
        st.header('Last 14 days of sensor readings')
        df_sensor = sensor_df[sensor_df["Sensor Name"]== selected_sensor]
        # Convert 'Timestamp' column to a DatetimeIndex
        df_sensor['Timestamp'] = pd.to_datetime(df_sensor['Timestamp'])

        # Set 'Timestamp' as the index
        df_sensor.set_index('Timestamp', inplace=True)

        # Group the data by day and select the last data point for the last 14 days
        df_sensor_fort = df_sensor.resample('D').last().tail(14)

        # Reset the index to have the 'Timestamp' as a regular column
        df_sensor_fort.reset_index(inplace=True)
        # Display the DataFrame
        st.dataframe(df_sensor_fort)

        # Display images and metrics for the selected sensor
        st.image(image_path_plot, caption=f"{selected_sensor} Forecast Plot", use_column_width=True)
        st.image(image_path_components, caption=f"{selected_sensor} Forecast Plot Components", use_column_width=True)
        
        sensor_data = pd.read_csv(selected_sensor + "/" + selected_sensor + "_forecast.csv")
        metrics = sensor_data[["MSE", "RMSE", "MAE", "MAPE"]]
        metrics = metrics.iloc[-1]
        
        # Calculate mean average and max value of sensor
        mean_pred = sensor_data['display_value'].mean()
        max_pred = sensor_data['display_value'].max()
        
        # Check if display_value is greater than 250
        if max_pred > 250:
            mean_pred = max_pred = "Sensor data predicts value to be at a hazardous level."

        # Print the mean average and max value
        st.write(f"Mean Average value of PM2.5 at this location: {mean_pred}")
        st.write(f"Max Value of PM2.5 at this location: {max_pred}")

        # Display metrics for the selected sensor
        #st.header('Metrics')
        # Display each metric on a new line
        #for metric, value in metrics.items():
        #    st.write(f'The metric for {metric} is: {value}\n')

        # Slider for changing plot color
        plot_color = st.slider('Choose day number 1 to 14 to see colour coding of PM2.5 levels:', 1, 14)        
        selected_row_value = sensor_data.iloc[plot_color - 1]['display_value']

        # Define color based on reading value
        if selected_row_value <= 12:
            color = 'green'
        elif 12.1 <= selected_row_value <= 35.4:
            color = 'yellow'
        elif 35.5 <= selected_row_value <= 55.4:
            color = 'orange'
        elif 55.5 <= selected_row_value <= 150.4:
            color = 'red'
        elif 150.5 <= selected_row_value <= 250.4:
            color = 'purple'
        else:
            color = 'black'

        # Plot sensor location
        st.header('Sensor Location')

        # Extract latitude and longitude
        latitude = sensor_data['Sensor Centroid Latitude'].values[-1]
        longitude = sensor_data['Sensor Centroid Longitude'].values[-1]

        # Set the aspect_ratio to 1 for a square plot
        bbox = (latitude, longitude, latitude, longitude)
        map = smopy.Map(bbox, z=17, aspect_ratio=1)
        ax = map.show_mpl(figsize=(10, 10))

        # Plot the single point
        x, y = map.to_pixels(latitude, longitude)
        ax.plot(x, y, 'o', ms=20, mew=2, color=color)

        #plt.title('Sensor Location')
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        st.pyplot(plt)

    else:
        # Initialize lists to store latitude and longitude for all sensors
        all_latitudes, all_longitudes = [], []
        pred_values = []
        # Initialize a list to store sensor names that are not green
        non_green_sensors = []
        
        st.header('PM2.5 Colour coding Chart')
        st.write("Good: 0 - 12: Green")
        st.write("Moderate: 12.1 - 35.4 = Yellow")
        st.write("Unhealthy for sensitive groups: 35.5 - 55.4 = Orange")
        st.write("Unhealthy: 55.5 - 150.4 = Red")
        st.write("Very Unhealthy: 150.5 - 250.4 = Purple")
        st.write("Hazardous: 250.5+ = Black")

        # Iterate over each sensor
        for sensor_name in sensor_names[1:]:
            # Construct the correct file path
            file_path = f"{sensor_name}/{sensor_name}_forecast.csv"

            # Assuming each CSV file has 'Sensor Centroid Latitude' and 'Sensor Centroid Longitude'
            sensor_data = pd.read_csv(file_path)

            # Extract latitude and longitude from the last row
            latitude = sensor_data['Sensor Centroid Latitude'].values[-1]
            longitude = sensor_data['Sensor Centroid Longitude'].values[-1]

            # Collect 'pred' values for each sensor
            pred_values.append(sensor_data['display_value'].tolist())

            all_latitudes.append(latitude)
            all_longitudes.append(longitude)

        # Slider for changing the day to display
        plot_day = st.slider('Choose day number 1 to 14 to see color coding of PM2.5 levels:', 1, 14)

        # Extract 'pred' values for the selected day for each sensor
        selected_pred_values = [pred[plot_day-1] for pred in pred_values]

        # Plot all sensor locations with colors based on 'pred' values for the selected day
        st.header('Sensor Locations')
        bbox = (min(all_latitudes), min(all_longitudes), max(all_latitudes), max(all_longitudes))
        map = smopy.Map(bbox, z=11)
        ax = map.show_mpl(figsize=(10, 10))

        # Define color based on reading value for the selected day for each sensor
        for sensor_name, lat, lon, pred_value in zip(sensor_names[1:], all_latitudes, all_longitudes, selected_pred_values):
            if pred_value <= 12:
                color = 'green'
            elif 12.1 <= pred_value <= 35.4:
                color = 'yellow'
                # Add non-green sensors to the list
                non_green_sensors.append((sensor_name, color))
            elif 35.5 <= pred_value <= 55.4:
                color = 'orange'
                # Add non-green sensors to the list
                non_green_sensors.append((sensor_name, color))
            elif 55.5 <= pred_value <= 150.4:
                color = 'red'
                # Add non-green sensors to the list
                non_green_sensors.append((sensor_name, color))
            elif 150.5 <= pred_value <= 250.4:
                color = 'purple'
                # Add non-green sensors to the list
                non_green_sensors.append((sensor_name, color))
            else:
                color = 'black'
                # Add non-green sensors to the list
                non_green_sensors.append((sensor_name, color))

            x, y = map.to_pixels(lat, lon)
            ax.plot(x, y, 'o', ms=20, mew=2, color=color)

    # Print sensor names and colors that are not green
        if non_green_sensors:
            st.write("Sensor names and their respective colors that are not displaying 'green' color:")
            for sensor_name, color in non_green_sensors:
                st.write(f"{sensor_name}: {color}")
        else:
            st.write("All sensors are displaying 'green' color.")

        plt.title('All Sensor Locations')
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        st.pyplot(plt)

except Exception as e:
    print("Sensor data unavailable")
    pass

