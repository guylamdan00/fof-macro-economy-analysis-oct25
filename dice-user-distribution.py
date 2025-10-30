#@title Users % by Last Position per DICE Event (100% Stacked Bar, High-Contrast Plasma)

import numpy as np
import pandas as pd
import plotly.express as px

# ----------------------------
# 1) Preprocessing
# ----------------------------
dwbar_df = dice_progression.copy()
dwbar_df['dice_event_start'] = pd.to_datetime(dwbar_df['dice_event_start']).dt.normalize()
dwbar_df['last_position'] = pd.to_numeric(dwbar_df['last_position'], errors='coerce')

# ----------------------------
# 2) Aggregate unique players
# ----------------------------
dwbar_agg = (
    dwbar_df.groupby(['dice_event_start', 'last_position'])['player_id']
            .nunique()
            .reset_index()
            .rename(columns={'player_id': 'unique_players'})
)

# Totals per event
dwbar_total = (
    dwbar_agg.groupby('dice_event_start')['unique_players']
              .sum()
              .reset_index()
              .rename(columns={'unique_players': 'total_unique_players'})
)

# Merge + percent of total
dwbar_agg = pd.merge(dwbar_agg, dwbar_total, on='dice_event_start', how='left')
dwbar_agg['pct_of_total'] = (dwbar_agg['unique_players'] / dwbar_agg['total_unique_players']) * 100
dwbar_agg = dwbar_agg[dwbar_agg['total_unique_players'] > 1000]

# ----------------------------
# 3) Pivot to wide format for stacked bar
# ----------------------------
dwbar_pivot = dwbar_agg.pivot_table(
    index='dice_event_start',
    columns='last_position',
    values='pct_of_total',
    fill_value=0
).sort_index()

# ----------------------------
# 4) Adjusted high-contrast Plasma palette
# ----------------------------
# Take only a central portion of Plasma (e.g., 20–90%) to boost contrast
plasma_full = px.colors.sequential.Plasma
n = len(plasma_full)
plasma_boosted = plasma_full[int(n * 0.2): int(n * 0.9)]

# ----------------------------
# 5) Plot
# ----------------------------
dwbar_fig = px.bar(
    dwbar_pivot,
    x=dwbar_pivot.index,
    y=dwbar_pivot.columns,
    color_discrete_sequence=plasma_boosted,
    title='Distribution of Players by Level Completed per DICE Event (High-Contrast Plasma)',
    labels={
        'value': 'Percentage of Total Players',
        'dice_event_start': 'DICE Event Start Date',
        'variable': 'Level Completed'
    }
)

dwbar_fig.update_layout(
    barmode='stack',
    width=2000,
    height=800,
    margin=dict(l=50, r=50, t=80, b=80),
    xaxis=dict(
        tickangle=45,
        title='DICE Event Start Date',
        tickvals=dwbar_pivot.index,
        ticktext=[d.strftime('%Y-%m-%d') for d in dwbar_pivot.index]
    ),
    yaxis=dict(
        title='Percentage of Total Players',
        range=[0, 100],
        ticksuffix='%'
    ),
    legend_title_text='Level Completed'
)

dwbar_fig.show()
