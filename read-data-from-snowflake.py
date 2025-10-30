#@title Economy Investigation
import gspread
import pandas as pd
from google.auth import default
from google.colab import auth
import numpy as np
from google.colab import drive
auth.authenticate_user()
creds, _ = default()
gc = gspread.authorize(creds)

drive.mount('/content/drive')

data_path = '/content/drive/MyDrive/Economy Investigation'

print('running query')

query = """
with q as (
  select
    max_event_timestamp as promo_ts,
    player_id,
    is_payer,
    energy_balance_bop,
    energy_balance_eop,
    total_energy_out
  from fish_of_fortune_prod.dwh.fact_daily_activities
  where event_date >= current_date - interval '191 day'
    and event_date < current_date - 1
    and player_id not in (
      select player_id
      from fish_of_fortune_prod.dwh.dim_test_users
      where is_player_tests = 1
    )
)
select
  to_date(promo_ts) as promo_date,
  dayname(to_date(promo_ts)) as promo_day,
  case
    when dayofweekiso(promo_ts) between 1 and 3 then 'Dice'
    else 'Trail'
  end as cycle_name,
  player_id,
  is_payer,
  energy_balance_bop,
  energy_balance_eop,
  total_energy_out
from q
order by promo_date
"""

cur = ctx.cursor()
try:
    cur.execute(query)
    player_balance = cur.fetch_pandas_all()     # returns a pandas DataFrame directly
finally:
    cur.close()

print("Energy query ran successfully")

mb_query = """
with mb_progression as (
  select
      player_id,
      calendar_id,
      config_id,
      is_payer,
      max(bar_id) as last_position
  from fish_of_fortune_prod.dwh.fact_missionbar_progression
  where event_timestamp >= current_date - interval '191 day'
    and event_name = 'MissionBar_Bar_Claimed'
  group by player_id, calendar_id, config_id, is_payer
),
calendar_event_start as (
  select
      calendar_id,
      cast(starts_at as date) as mb_event_start,
      cast(ends_at   as date) as mb_event_end,
      datediff('day', starts_at, ends_at) as days_live
  from (
      select
          calendar_id,
          starts_at,
          ends_at,
          row_number() over (
            partition by calendar_id
            order by starts_at desc
          ) as rn
      from fish_of_fortune_prod.dwh.v_dim_calendar_last_state
      where event_name = 'MissionBar'
        and starts_at >= current_date - interval '191 day'
        and starts_at < current_timestamp
  ) d
  where rn = 1
)
select
    m.player_id,
    m.calendar_id,
    m.config_id,
    m.is_payer,
    m.last_position,
    c.mb_event_start,
    c.mb_event_end,
    c.days_live
from mb_progression as m
left join calendar_event_start as c
  on m.calendar_id = c.calendar_id;
"""

cur = ctx.cursor()
try:
    cur.execute(mb_query)
    mb_progression = cur.fetch_pandas_all()     # returns a pandas DataFrame directly
finally:
    cur.close()

print("MB query ran successfully")

dice_query = """
with calendar as(
    select
        event_name,
        calendar_id,
        config_name,
        starts_at,
        ends_at,
        TO_VARCHAR(INCLUDE_SEGMENT_GROUPS) AS json_text,
        case when (json_text ilike '%DSI_0-1%') or (json_text ilike '%DSI_2-3%') then 1 else 0 end as is_dsi_seg_group
    from
        fish_of_fortune_prod.dwh.v_dim_calendar_last_state
    where
        1 = 1
        and event_name ilike '%ProgressingMiniGame%'
        and alternative_group_name_internal ilike '%dice%'
        and starts_at >= current_date - interval '191 day'
        and starts_at < current_timestamp
        and is_dsi_seg_group = 0
), dice_progression as (
    select
        player_id,
        calendar_id,
        minigame_config_id,
        minigame_config_display_name,
        case
            when minigame_level_number = 1 then 7
            else minigame_level_number - 1
        end as minigame_level_number,
        event_name
    from
        fish_of_fortune_prod.base.prs_events
    where
        1 = 1
        and event_name = 'Minigame_Levelup'
        and minigame_type ilike 'dice'
        and minigame_config_display_name not ilike '%dsi%'
        and event_date >= current_date - interval '191 day'
        and event_date < current_timestamp
)
select
    d.player_id,
    d.calendar_id,
    c.config_name,
    max(d.minigame_level_number) as last_position,
    c.starts_at,
    c.ends_at
from dice_progression as d
left join calendar as c
  on d.calendar_id = c.calendar_id
  where c.starts_at >= current_date - interval '191 day'
        and c.starts_at < current_timestamp
  group by all;
"""
cur = ctx.cursor()
try:
    cur.execute(dice_query)
    dice_progression = cur.fetch_pandas_all()     # returns a pandas DataFrame directly
finally:
    cur.close()


puzzle_query = """
with calendar as (
    select
        calendar_id,
        config_name,
        starts_at,
        ends_at
    from fish_of_fortune_prod.dwh.v_dim_calendar_last_state
    where event_name ilike '%Puzzle%'
      and starts_at >= dateadd(day, -191, current_date)
      and starts_at <  current_date
      -- exclude DSI segment groups (case-insensitive)
      -- and not regexp_like(to_varchar(include_segment_groups), 'DSI_0-1|DSI_2-3', 'i')
),
puzzle_progression as (
    select
        player_id,
        calendar_id,
        puzzle_config_display_name,
        max(puzzle_level_number) - 1 as levels_completed
    from fish_of_fortune_prod.base.prs_events
    where event_name = 'Puzzle_Levelup'
      and event_date >= dateadd(day, -191, current_date)
      and event_date <  current_date
      and player_id not in (
        select player_id
        from fish_of_fortune_prod.dwh.dim_test_users
        where is_player_tests = 1
      )
      -- exclude DSI segment groups (case-insensitive)
      -- and not regexp_like(to_varchar(segment_list), 'DSI_0-1|DSI_2-3', 'i')
    group by player_id, calendar_id, puzzle_config_display_name
)
select
    p.player_id,
    p.calendar_id,
    p.puzzle_config_display_name,
    c.config_name,
    p.levels_completed,
    c.starts_at,
    c.ends_at
from puzzle_progression p
join calendar c
on p.calendar_id = c.calendar_id;
"""

cur = ctx.cursor()
try:
    cur.execute(puzzle_query)
    puzzle_progression = cur.fetch_pandas_all()     # returns a pandas DataFrame directly
finally:
    cur.close()


print("all queries ran successfully")

player_balance.columns = player_balance.columns.str.strip().str.lower().str.replace(' ', '_')

# duplicates = player_balance[player_balance.duplicated(subset=['player_id', 'promo_date'], keep=False)]
# duplicates.sort_values(by=['player_id', 'promo_date'], inplace=True)

# # Display summary
# print(f"Total duplicates: {len(duplicates)}")
# print(f"Unique players affected: {duplicates['player_id'].nunique()}")

spreadsheet = gc.open_by_key('1Va9Hzlc9QJcTtIb4h_5YP5_pBCNsP_bNEnOTGyXEOvQ')
worksheet = spreadsheet.worksheet('monetization_plan')
monetization_plan = pd.DataFrame(worksheet.get())
monetization_plan.columns = monetization_plan.iloc[0]
monetization_plan = monetization_plan.drop(0)
monetization_plan.columns = monetization_plan.columns.str.strip().str.lower().str.replace(' ', '_')
monetization_plan = monetization_plan[['date', 'special_holiday', 'campaign', 'new_features', 'cycle', 'main_story', 'album', 'puzzle_/_th', 'trail_/_dice', 'theme_path']]
monetization_plan.rename(columns={'date': 'promo_date'}, inplace=True)
monetization_plan['promo_date'] = pd.to_datetime(monetization_plan['promo_date']).dt.date

player_balance = pd.merge(player_balance, monetization_plan[['promo_date', 'special_holiday', 'campaign', 'new_features', 'cycle', 'main_story', 'album', 'puzzle_/_th']], on='promo_date', how='left')

# duplicates = player_balance[player_balance.duplicated(subset=['player_id', 'promo_date'], keep=False)]
# duplicates.sort_values(by=['player_id', 'promo_date'], inplace=True)

# # Display summary
# print(f"Total duplicates: {len(duplicates)}")
# print(f"Unique players affected: {duplicates['player_id'].nunique()}")

mb_file_name = 'mb_progression.parquet'
print('saving mb_progression data')
mb_progression.to_parquet(data_path + '/' + mb_file_name, index=False)
player_balance_file_name = 'player_balance.parquet'
print('saving player_balance data')
player_balance.to_parquet(data_path + '/' + player_balance_file_name, index=False)

mb_progression.columns = mb_progression.columns.str.strip().str.lower().str.replace(' ', '_')
mb_progression = (
    mb_progression.sort_values(['player_id', 'mb_event_start', 'last_position'], ascending=[True, True, False])
    .drop_duplicates(subset=['player_id', 'mb_event_start'], keep='first')
)
mb_progression.sort_values(by='mb_event_start', inplace=True)
duplicates = mb_progression[mb_progression.duplicated(subset=['player_id', 'mb_event_start'], keep=False)]
duplicates.sort_values(by=['player_id', 'mb_event_start'], inplace=True)

# Display summary
print(f"Total duplicates: {len(duplicates)}")
print(f"Unique players affected: {duplicates['player_id'].nunique()}")

mb_file_name = 'mb_progression.parquet'
print('saving mb_progression data')
mb_progression.to_parquet(data_path + '/' + mb_file_name, index=False)

dice_progression.columns = dice_progression.columns.str.strip().str.lower().str.replace(' ', '_')
dice_progression.sort_values(by='starts_at', inplace=True)
dice_progression['dice_event_start'] = pd.to_datetime(dice_progression['starts_at']).dt.date
dice_progression['dice_event_end'] = pd.to_datetime(dice_progression['ends_at']).dt.date
# # Check for duplicates by player_id and dice_event_start
# duplicates = dice_progression[dice_progression.duplicated(subset=['player_id', 'dice_event_start'], keep=False)]

# # Display summary
# print(f"Total duplicates: {len(duplicates)}")
# print(f"Unique players affected: {duplicates['player_id'].nunique()}")

dice_file_name = 'dice_progression.parquet'
print('saving dice_progression data')
dice_progression.to_parquet(data_path + '/' + dice_file_name, index=False)

puzzle_progression.columns = puzzle_progression.columns.str.strip().str.lower().str.replace(' ', '_')
puzzle_progression.sort_values(by='starts_at', inplace=True)
puzzle_progression['puzzle_event_starts_at'] = pd.to_datetime(puzzle_progression['starts_at']).dt.date
puzzle_progression['puzzle_event_ends_at'] = pd.to_datetime(puzzle_progression['ends_at']).dt.date
# puzzle_progression.sort_values(by='puzzle_event_starts_at', inplace=True)
# duplicates = puzzle_progression[puzzle_progression.duplicated(subset=['player_id', 'puzzle_event_starts_at', 'puzzle_config_display_name'], keep=False)]
# duplicates.sort_values(by=['player_id', 'puzzle_event_starts_at'], inplace=True)

puzzle_file_name = 'puzzle_progression.parquet'
print('saving puzzle_progression data')
puzzle_progression.to_parquet(data_path + '/' + puzzle_file_name, index=False)


print('data saved sucssufully')
