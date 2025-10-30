import gspread
import pandas as pd
from google.auth import default
from google.colab import auth
import numpy as np
from google.colab import drive
import ipywidgets as widgets
from IPython.display import display
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date
auth.authenticate_user()
creds, _ = default()
gc = gspread.authorize(creds)

# add spreadsheet key
spreadsheet = gc.open_by_key('')
worksheet = spreadsheet.worksheet('monetization_plan')
monetization_plan = pd.DataFrame(worksheet.get())
monetization_plan.columns = monetization_plan.iloc[0]
monetization_plan = monetization_plan.drop(0)
monetization_plan.columns = monetization_plan.columns.str.strip().str.lower().str.replace(' ', '_')
monetization_plan = monetization_plan[['date', 'special_holiday', 'campaign', 'new_features', 'cycle', 'main_story', 'album', 'puzzle_/_th', 'trail_/_dice', 'theme_path']]
monetization_plan.rename(columns={'date': 'promo_date'}, inplace=True)
monetization_plan['promo_date'] = pd.to_datetime(monetization_plan['promo_date']).dt.date

drive.mount('/content/drive')

data_path = '/content/drive/MyDrive/Economy Investigation'

dice_file_name = 'dice_progression.parquet'
print('reading dice_progression')
dice_progression = pd.read_parquet(data_path + '/' + dice_file_name)

mb_file_name = 'mb_progression.parquet'
print('reading mb_progression')
mb_progression = pd.read_parquet(data_path + '/' + mb_file_name)

puzzle_file_name = 'puzzle_progression.parquet'
print('reading puzzle_progression')
puzzle_progression = pd.read_parquet(data_path + '/' + puzzle_file_name)

player_balance_file_name = 'player_balance.parquet'
print('reading player_balance')
player_balance = pd.read_parquet(data_path + '/' + player_balance_file_name)
print('data read sucssufully')

