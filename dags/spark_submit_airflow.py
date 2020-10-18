from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.hooks.S3_hook import S3Hook
from airflow.operators import PythonOperator
from airflow.contrib.operators.emr_create_job_flow_operator import (
    EmrCreateJobFlowOperator,
)
from airflow.contrib.operators.emr_add_steps_operator import EmrAddStepsOperator
from airflow.contrib.sensors.emr_step_sensor import EmrStepSensor
from airflow.contrib.operators.emr_terminate_job_flow_operator import (
    EmrTerminateJobFlowOperator,
)

# Configurations
BUCKET_NAME = "<your-bucket-name>"  # replace this with your bucket name
local_data = "./dags/data/movie_review.csv"
s3_data = "data/movie_review.csv"
local_script = "./dags/scripts/spark/random_text_classification.py"
s3_script = "scripts/random_text_classification.py"
s3_clean = "clean_data/"
SPARK_STEPS = []

JOB_FLOW_OVERRIDES = {}

# helper function
def _local_to_s3(filename, key, bucket_name=BUCKET_NAME):
    s3 = S3Hook()
    s3.load_file(filename=filename, bucket_name=bucket_name, replace=True, key=key)


default_args = {
    "owner": "airflow",
    "depends_on_past": True,
    "wait_for_downstream": True,
    "start_date": datetime(2020, 10, 17),
    "email": ["airflow@airflow.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "spark_submit_airflow",
    default_args=default_args,
    schedule_interval="0 10 * * *",
    max_active_runs=1,
)

start_data_pipeline = DummyOperator(task_id="start_data_pipeline", dag=dag)

data_to_s3 = DummyOperator(task_id="data_to_s3", dag=dag)

script_to_s3 = DummyOperator(task_id="script_to_s3", dag=dag)

# Create an EMR cluster
create_emr_cluster = DummyOperator(task_id="create_emr_cluster", dag=dag)

# Add your steps to the EMR cluster
step_adder = DummyOperator(task_id="add_steps", dag=dag)

last_step = len(SPARK_STEPS) - 1
# wait for the steps to complete
step_checker = DummyOperator(task_id="watch_step", dag=dag)

# Terminate the EMR cluster
terminate_emr_cluster = DummyOperator(task_id="terminate_emr_cluster", dag=dag)

end_data_pipeline = DummyOperator(task_id="end_data_pipeline", dag=dag)

start_data_pipeline >> [data_to_s3, script_to_s3] >> create_emr_cluster
create_emr_cluster >> step_adder >> step_checker >> terminate_emr_cluster
terminate_emr_cluster >> end_data_pipeline
