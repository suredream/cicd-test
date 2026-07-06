from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def hello():
    print("Hello from Airflow in Codespaces!")

with DAG(
    dag_id="example_minimal",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@once",
    catchup=False,
):
    PythonOperator(
        task_id="hello_task",
        python_callable=hello,
    )
