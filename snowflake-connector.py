# 1) Install deps (Arrow-enabled connector gives fast DataFrame fetches)
!pip -q install "snowflake-connector-python[pandas]" pandas


# 2) Set up connection (edit these)
import getpass, snowflake.connector, pandas as pd
from google.colab import userdata
import matplotlib.pyplot as plt
import ipywidgets as widgets
from IPython.display import display
import pandas as pd
import matplotlib.dates as mdates
from datetime import date

# snowflake_pass = userdata.get('snowflake_pass')
# add config details
account   = ""     # e.g. "ab12345.eu-central-1" (no .snowflakecomputing.com)
user      = ""
warehouse = ""
database  = ""
schema    = ""
role      = ""           # optional; set to None if not used

password = userdata.get('snowflake_pass') or getpass.getpass("Snowflake password: ")

ctx = snowflake.connector.connect(
    account=account,
    user=user,
    password=password,
    warehouse=warehouse,
    database=database,
    schema=schema,
    role=role if role else None,
    client_session_keep_alive=True,   # keeps session alive while you poke around
)

print('Snowflake Connection Established')
