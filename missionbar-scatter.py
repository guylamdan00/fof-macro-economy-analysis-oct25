#@title Users % by Last Position per MB Event

mb_agg = mb_progression.groupby(['mb_event_start', 'last_position'])['player_id'].nunique().reset_index()
mb_agg.rename(columns={'player_id': 'unique_players'}, inplace=True)

total_players_per_start = mb_agg.groupby('mb_event_start')['unique_players'].sum().reset_index()
total_players_per_start.rename(columns={'unique_players': 'total_unique_players'}, inplace=True)

mb_agg = pd.merge(mb_agg, total_players_per_start, on='mb_event_start', how='left')
mb_agg['percentage_of_total_players'] = (mb_agg['unique_players'] / mb_agg['total_unique_players']) * 100
mb_agg = mb_agg[mb_agg['total_unique_players'] > 1000]

display(mb_agg.head())

import plotly.express as px

# ensure datetime
mb_agg = mb_agg.copy()
mb_agg['mb_event_start'] = pd.to_datetime(mb_agg['mb_event_start'])

# OPTIONAL: boost marker sensitivity (downweight big values a bit so small ones show up)
size_series = mb_agg['percentage_of_total_players'].astype(float)
size_series = np.power(size_series, 0.75)  # 0.6–0.85 works well; lower => more boost to small values

fig = px.scatter(
    mb_agg,
    x='mb_event_start',
    y='last_position',
    size=size_series,                       # use transformed size
    color='percentage_of_total_players',
    color_continuous_scale="Plasma",         # high-contrast perceptual scale
    hover_data={
        'mb_event_start': True,
        'last_position': True,
        'unique_players': True,
        'percentage_of_total_players': ':.2f%'
    },
    title='Percentage of Unique Players by Last Position and MB Event Start Date',
    labels={
        'mb_event_start': 'MB Event Start Date',
        'last_position': 'Last Position Reached',
        'percentage_of_total_players': 'Percentage of Total Players'
    },
    size_max=25                                # bigger bubbles overall
)

# -------- show ONLY the actual event-start dates as ticks --------
tick_vals = (
    mb_agg['mb_event_start']
    .dropna()
    .sort_values()
    .drop_duplicates()
    .to_numpy()
)
# If there are too many events, sample ticks (keeps ~35 ticks max for readability)
max_ticks = 50
step = max(1, int(np.ceil(len(tick_vals) / max_ticks)))
tick_vals = tick_vals[::step]
tick_text = [pd.to_datetime(d).strftime('%Y-%m-%d') for d in tick_vals]

fig.update_xaxes(
    tickmode='array',
    tickvals=tick_vals,
    ticktext=tick_text,
    tickangle=45
)

# Bigger interactive canvas + clearer colorbar
fig.update_layout(
    width=2000,
    height=800,
    margin=dict(l=50, r=50, t=80, b=80),
    coloraxis_colorbar=dict(
        title="Pct of Total Players",
        tickformat=".0f"
    )
)

# Optional: clamp color range to the 99th percentile for more contrast
cmax = float(np.percentile(mb_agg['percentage_of_total_players'], 99))
fig.update_coloraxes(cmin=0, cmax=cmax)

try:
    mbm_story_src = monetization_plan[['promo_date', 'main_story']].copy()
except NameError:
    mbm_story_src = pd.DataFrame(columns=['promo_date', 'main_story'])

if not mbm_story_src.empty:
    mbm_story_src['promo_date'] = pd.to_datetime(mbm_story_src['promo_date']).dt.normalize()
    mbm_story_src['main_story'] = mbm_story_src['main_story'].astype(str).str.strip()
    mbm_story_src = mbm_story_src.dropna(subset=['promo_date','main_story']).query("main_story != ''")

    # first appearance per story (global earliest date)
    mbm_firsts = (
        mbm_story_src.sort_values(['main_story','promo_date'])
                     .groupby('main_story', as_index=False)['promo_date']
                     .first()
    )

    # limit markers to the plotted x-range (min/max event start)
    x_min = pd.to_datetime(mb_agg['mb_event_start'].min()).normalize() if not mb_agg.empty else None
    x_max = pd.to_datetime(mb_agg['mb_event_start'].max()).normalize() if not mb_agg.empty else None
    if x_min is not None and x_max is not None:
        mbm_firsts = mbm_firsts.query("(@x_min <= promo_date) & (promo_date <= @x_max)")

    # add vertical dotted lines + rotated labels above the plot
    for _, row in mbm_firsts.iterrows():
        d = row['promo_date']
        label = row['main_story']

        fig.add_vline(
            x=d, line_dash='dot', line_width=1, opacity=0.45
        )
        fig.add_annotation(
            x=d, y=1.02,  # slightly above the plotting area
            xref='x', yref='paper',
            text=label,
            showarrow=False,
            textangle=90,
            yanchor='bottom',
            font=dict(size=10),
            opacity=0.9
        )

    # add a bit of headroom so labels don't overlap the title
    fig.update_layout(margin=dict(l=50, r=50, t=100, b=80))

fig.show()
