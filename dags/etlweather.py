from airflow import DAG
from airflow.providers.http.hooks.http import HttpHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.decoraters import task
from airflow.utlis.dates import days_ago

LATITUDE = '19.0760'
LONGITUDE = '72.8777'
POSTGRES_CONN_ID='postgres_default'
API_CONN_ID='open_meteo_api'


default_args={
    'owner':'airflow'
    'start_date':'days_ago'
}

with DAG(dag_id='weather_etl_pipeline',
         default_args = default_args,
         schedule_interval = '@daily',
         catchup =False)as dags:
    
    @task()
    def extract_weather_data():
        
        
        http_hook=HttpHook(http_conn_id=API_CONN_ID,method ='GET')
        
        #https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m
        #https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current_weather=true
        # open meto url : 
        endpoint=f'v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&current_weather=true'
        
        #Make the request via http hook 
        response=http_hook.run(endpoint)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch the data :{response.status_code}")
        
    @task()
    def transform_weather_data(weather_data):
        "Transform the extracted Weather Data"
        current_weather = weather_data['current_weather']
        transformed_data = {
            'latitude': LATITUDE,
            'longitude':LONGITUDE,
            'temperature' : current_weather['temperature'],
            'windspeed' : current_weather['windspeed'],
            'winddirection' : current_weather['winddirection'],
            'weathercode' : current_weather['weathercode']
            
        }
        return transformed_data
    
    @task()
    def load_weather_data(transformed_data):
        "Load the transformed weather data into the database"
        pg_hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        conn = pg_hook.get_conn()
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS weather_data (latitude FLOAT,longitude FLOAT,temperature FLOAT,windspeed FLOAT,winddirection FLOAT,weathercode FLOAT)""")
        
        cursor.execute("""INSERT INTO weather_data (latitude,longitude,temperature,windspeed,winddirection,weathercode) VALUES (%s,%s,%s,%s,%s,%s)""",(transformed_data['latitude'],transformed_data['longitude'],transformed_data['temperature'],transformed_data['windspeed'],transformed_data['winddirection'],transformed_data['weathercode']))
        conn.commit()
        cursor.close()
        
        #Dag Workflow
        weather_data = extract_weather_data()
        transformed_data = transform_weather_data(weather_data)
        load_weather_data(transformed_data)