import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import requests
import dash_auth  

VALID_USERNAME_PASSWORD_PAIRS = {
    'admin': 'pass123',
    'amogh': 'test',
    'profBhanu': 'apa'
}

API_KEY = "c18cc2782efdf477ad3f0ed1b2f3b5a3"

CROP_SETTINGS = {
    "Wheat":  {"soil_threshold": 35, "temp_optimal": 25, "water_need": 4},   
    "Rice":   {"soil_threshold": 45, "temp_optimal": 30, "water_need": 8},   
    "Cotton": {"soil_threshold": 40, "temp_optimal": 32, "water_need": 5},   
    "Corn":   {"soil_threshold": 38, "temp_optimal": 28, "water_need": 6},   
    "Tomato": {"soil_threshold": 42, "temp_optimal": 27, "water_need": 3.5}  
}

def get_weather_data(api_key, city):
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {'q': city, 'appid': api_key, 'units': 'metric'}
    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        if response.status_code == 200:
            temperature = data['main']['temp']
            rainfall_mm = data.get('rain', {}).get('1h', 0)
            return temperature, rainfall_mm, None
        else:
            return None, None, data.get('message', 'Unknown error')
    except requests.exceptions.RequestException as e:
        return None, None, f"Connection error: {e}"

app = dash.Dash(__name__)
app.title = "APA Project"

app.layout = html.Div(style={'fontFamily': 'Arial, sans-serif', 'padding': '20px'}, children=[
    
    html.H1("🌱 Smart Irrigation Dashboard", style={'textAlign': 'center'}),
    html.P("Automatic Plant Watering System with Weather Forecast Integration", style={'textAlign': 'center'}),
    
    html.Hr(),
    
    html.Div(style={'width': '40%', 'float': 'left', 'paddingRight': '2%'}, children=[
        html.H3("System Configuration"),

        html.Label("City:"),
        dcc.Input(id='city-input', value='Hyderabad', type='text', style={'width': '100%'}),
        
        html.Label("Crop Type:", style={'marginTop': '10px'}),
        dcc.Dropdown(
            id='crop-dropdown',
            options=[{'label': k, 'value': k} for k in CROP_SETTINGS.keys()],
            value='Rice'
        ),
        
        html.Label("Soil Moisture (%):", style={'marginTop': '10px'}),
        dcc.Slider(id='soil-slider', min=0, max=100, value=35, marks={i: str(i) for i in range(0, 101, 20)}),
        
        html.Label("Water Tank Level (%):", style={'marginTop': '10px'}),
        dcc.Slider(id='tank-slider', min=0, max=100, value=70, marks={i: str(i) for i in range(0, 101, 20)}),

        html.H4("System Parameters", style={'marginTop': '20px'}),
        html.Label("Field Area (m²):"),
        dcc.Input(id='area-input', value=50, type='number', style={'width': '100%'}),
        html.Label("Pump Flow (L/min):"),
        dcc.Input(id='flow-input', value=10, type='number', style={'width': '100%'}),
        html.Label("Tank Capacity (L):"),
        dcc.Input(id='capacity-input', value=500, type='number', style={'width': '100%'}),
        
        html.Button(
            'Run Irrigation Check', 
            id='run-button', 
            n_clicks=0, 
            style={'width': '100%', 'marginTop': '25px', 'padding': '10px', 'fontSize': '16px', 'backgroundColor': '#007BFF', 'color': 'white'}
        )
    ]),
    
    html.Div(style={'width': '55%', 'float': 'right'}, children=[
        html.H3("System Dashboard"),
        
        dcc.Markdown(id='dashboard-output', style={'backgroundColor': '#f4f4f4', 'padding': '15px', 'borderRadius': '5px'})
    ])
])

auth = dash_auth.BasicAuth(
    app,
    VALID_USERNAME_PASSWORD_PAIRS
)

@app.callback(
    Output('dashboard-output', 'children'), 
    [Input('run-button', 'n_clicks')],      
    [State('city-input', 'value'),         
     State('crop-dropdown', 'value'),
     State('soil-slider', 'value'),
     State('tank-slider', 'value'),
     State('area-input', 'value'),
     State('flow-input', 'value'),
     State('capacity-input', 'value')]
)
def update_dashboard(n_clicks, city, crop_type, soil_moisture, water_level, 
                     field_area, pump_flow_rate, tank_capacity):
    
    if n_clicks == 0:
        return "Click 'Run Irrigation Check' to see the system status."


    temperature, forecasted_rain, error = get_weather_data(API_KEY, city)
    
    if error:
        return f"**API Error:** {error}"

    crop_info = CROP_SETTINGS.get(crop_type, CROP_SETTINGS["Wheat"])
    soil_threshold = crop_info["soil_threshold"]
    water_need_per_m2 = crop_info["water_need"]

    available_water = (water_level / 100) * tank_capacity
    total_water_needed = water_need_per_m2 * field_area
    pump_run_time = total_water_needed / pump_flow_rate
    
    RAIN_THRESHOLD = 2; WATER_LOW_THRESHOLD = 20
    final_status, reason, status_icon = "", "", ""

    if water_level < WATER_LOW_THRESHOLD:
        final_status, status_icon, reason = "IDLE", "", "Low water level in tank."
    elif available_water < total_water_needed:
        final_status, status_icon, reason = "IDLE", "", "Not enough water in tank to irrigate."
    elif soil_moisture >= soil_threshold:
        final_status, status_icon, reason = "IDLE", "", "Soil is already moist enough."
    elif forecasted_rain >= RAIN_THRESHOLD:
        final_status, status_icon, reason = "IDLE", "", f"Rain ({forecasted_rain} mm) is expected."
    else:
        final_status, status_icon, reason = "ACTIVE", "", "Soil is DRY and NO rain is forecast."

    output_text = f"""
    ### **Pump Status: {final_status} {status_icon}**
    **Reason:** {reason}
    
    ---
    
    #### System Details:
    * **Selected Crop:** {crop_type}
    * **Soil Moisture:** {soil_moisture}% (Dry if < {soil_threshold}%)
    * **Weather ({city}):** {forecasted_rain} mm rain, {temperature}°C
    
    #### Water Calculation:
    * **Tank Level:** {water_level}% ({available_water:.1f} L available)
    * **Water Needed:** {total_water_needed:.1f} L
    * **Est. Run Time:** {pump_run_time:.1f} min
    """
    return output_text

if __name__ == '__main__':
    app.run(debug=True, port=8502) 