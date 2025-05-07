# SciVis ‘26: Visualizing Climate Change Hotspots and Their Impact Using the NEX-GDDP-CMIP6 Dataset

This application implements a simple and intuitive Flask webapp to visualize the NEX-GDDP-CMIP6 dataset provided by NASA for the SciVis26 competition. 

In addition to visualization, we provide the ability to play through and compare data between different time stamps as well as country-based statistics on the time series data (i.e., Change in Temperature, Economic Impact). We hope that this analysis will be useful to scientists and policymakers trying to study the progress of climate change.

## Installation Instructions
This code uses a Flask webapp. To run the application locally, first you will need `Python 3` and a web browser. Next, set up a Python virtual environment:

```python -m venv my_virtual_env``` 

and activate it: 

```source my_virtual_env/bin/activate```

Next, you will need to install the dependencies. I have included a file `requirements.txt` that includes all of the Python libraries. If that is not working or you need some alternative configuration, you may install the libraries manually:

* `numpy`
* `flask`
* `OpenVisus`
* `requests`
* `pillow`
* `matplotlib`
* `shapely`

After installing these libraries, simply navigate to the `app` folder and run the following command:

```python app.py```

This should launch an instance of the Flask application. It will give you a link to follow to access the program. For example:

```Running on http://127.0.0.1:5000```

Alternatively, you can usually use `localhost:5000`

After you get the link, use your web browser of choice to go to it.

## Using the program

Whenever you navigate to the webpage where the app is running, you will see the visualization and a control panel at the top. There are several distinct features. 

* Date selection will allow you to specify which day of data you are visualizing 
* Metric dropdown allows you to pick which metric to visualize 
* Dropdowns to select which model to use
* Play by year and play by day function. Will play sequentially at a course-grain through the pay by year function or at fine-grain through the play by day function
* Compute Top 5 Change function will allow you to compute the top 5 fastest changing countries in terms of change in wet bulb temperature and the effect that it will have economically. 

## Contact
My email is: washwor1@vols.utk.edu 

## Acknowledgements 
Barrage, L. and Nordhaus, W. (2023) Policies, projections, and the social cost of carbon: Results from the dice-2023 model [Preprint]. doi:10.3386/w31112. 

NASA Earth Exchange Global Daily Downscaled Projections (NEX-GDDP-CMIP6) (no date) NASA. Available at: https://www.nccs.nasa.gov/services/data-collections/land-based-products/nex-gddp-cmip6 (Accessed: 05 May 2025). 

SubbaRao, M. (2025) NASA Scientific Visualization studio, NASA. Available at: https://svs.gsfc.nasa.gov/5190/#:~:text=The%20NASA%20climate%20spiral%20visualization,labels%20in%20English%20and%20Celsius (Accessed: 05 May 2025). 

Too hot to handle: How climate change may make some places too hot to live - NASA science (2024) NASA. Available at: https://science.nasa.gov/earth/climate-change/too-hot-to-handle-how-climate-change-may-make-some-places-too-hot-to-live/#:~:text=As%20Earth%E2%80%99s%20climate%20warms%2C%20incidences,warn%20us%20of%20harmful%20conditions (Accessed: 05 May 2025).
