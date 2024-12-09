Forecasting Project Repository

Welcome to the Forecasting Project Repository. This repository contains materials and code developed for a forecasting project aimed at analysing and predicting trends using data science techniques. Below is an overview of the content included in the repository and instructions for its usage.

Repository Contents
1. Jupyter Notebooks
- building_a_forecast_model.ipynb: A step-by-step guide to building a forecasting model, including data preprocessing, feature engineering, and model evaluation.
- pipeline_workbook.ipynb and pipeline_workbook-storageAccountV2.ipynb: Notebooks focusing on the creation and refinement of data pipelines for efficient forecasting processes.

2. Power BI Report
- ForcastingDemo.pbix: A Power BI file presenting an interactive dashboard for visualizing forecasting outputs and key insights.

3. Presentation
- forecasting_presentation.pptx: A detailed presentation covering:
  - Introduction to the project
  - Steps for building a forecasting model
  - Insights gained
  - Tools and applications used, including Streamlit and Power BI
  - Final remarks on the utility of forecasting models.

4. Streamlit Application
- streamlit_app.py: A Python script to deploy a web application using Streamlit. Features include:
  - Visualization of PM2.5 levels from sensor data.
  - Interactive selection of sensors and display of corresponding forecasts.
  - Color-coded indicators for air quality based on PM2.5 levels.
  - Mapping sensor locations using Smopy.

5. Sensor Data
- sensor_locs.csv: A dataset providing metadata for sensors, including their locations and readings.

Usage Instructions
Prerequisites
- Python 3.8+ installed on your system.
- Libraries such as Pandas, Matplotlib, Smopy, and Streamlit.
- Power BI Desktop (for .pbix files).

Running the Streamlit App
- Place all necessary files in the same directory as the script.
- Run the app using:
  streamlit run streamlit_app.py
- Interact with the application through your browser to explore sensor data and forecasts.

Viewing Power BI Report
- Open ForcastingDemo.pbix with Power BI Desktop for interactive insights.

Exploring Notebooks
- Use Jupyter Notebook to open and execute the .ipynb files for detailed walkthroughs of the forecasting pipeline and model.

Key Features
- Forecasting Techniques: Leverage advanced forecasting models for accurate predictions.
- Pipeline Integration: Streamlined data handling and processing.
- Interactive Visualizations: Power BI and Streamlit-based tools for intuitive data exploration.
- Actionable Insights: Tools to derive insights for decision-making.