#@title MB Last Position by Percentile
# MB percentiles (last_position) by mb_event_start — Matplotlib + ipywidgets
# Self-contained: all names are prefixed with "mbp_" to avoid collisions.
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import ipywidgets as widgets
from IPython.display import display

# ----------------------------
# 1) One-time preprocessing
# ----------------------------
mbp_df = mb_agg[['mb_event_start', 'last_position', 'unique_players']].copy()
mbp_df['mb_event_start'] = pd.to_datetime(mbp_df['mb_event_start']).dt.normalize()
mbp_df['last_position']  = pd.to_numeric(mbp_df['last_position'], errors='coerce')
mbp_df['unique_players'] = pd.to_numeric(mbp_df['unique_players'], errors='coerce')
mbp_df = mbp_df.dropna(subset=['mb_event_start', 'last_position', 'unique_players'])

# Collapse duplicates per (event, position) if any
mbp_df = (
    mbp_df.groupby(['mb_event_start', 'last_position'], as_index=False)['unique_players']
          .sum()
)

# ---- Monetization plan labels: show only first appearance of each story ----
try:
    mbp_story_src = monetization_plan[['promo_date', 'main_story']].copy()
except NameError:
    mbp_story_src = pd.DataFrame(columns=['promo_date','main_story'])

mbp_story_src['promo_date'] = pd.to_datetime(mbp_story_src['promo_date']).dt.normalize()
mbp_story_src['main_story'] = mbp_story_src['main_story'].astype(str).str.strip()
mbp_story_src = mbp_story_src.dropna(subset=['promo_date','main_story']).query("main_story != ''")

# 1st appearance per story (global earliest date)
mbp_story_firsts = (
    mbp_story_src.sort_values(['main_story','promo_date'])
                  .groupby('main_story', as_index=False)['promo_date']
                  .first()
)

# Build date -> list of stories (in case several first-appear on the same day)
from collections import defaultdict
mbp_story_first_map = defaultdict(list)
for _, row in mbp_story_firsts.iterrows():
    mbp_story_first_map[row['promo_date']].append(row['main_story'])


# Supported percentiles
mbp_qs = [0.5, 0.75, 0.9, 0.95, 0.99]
mbp_q_labels = {q: f"{int(q*100)}th percentile" for q in mbp_qs}

def mbp_draw_story_markers(ax, x_start: pd.Timestamp, x_end: pd.Timestamp):
    if not mbp_story_first_map:
        return

    # all first-appearance dates within the visible range
    dates_in_range = [d for d in mbp_story_first_map.keys()
                      if (d >= pd.Timestamp(x_start).normalize())
                      and (d <= pd.Timestamp(x_end).normalize())]

    for d in sorted(dates_in_range):
        stories = mbp_story_first_map[d]
        label = " • ".join(stories)  # combine if multiple debut the same day
        ax.axvline(pd.Timestamp(d), linestyle=':', linewidth=1, alpha=0.6)
        ax.text(pd.Timestamp(d), 1.01, label,
                rotation=90, va='bottom', ha='center',
                transform=ax.get_xaxis_transform())



def mbp_weighted_percentiles(group: pd.DataFrame) -> pd.Series:
    g = group.sort_values('last_position')
    w = g['unique_players'].to_numpy()
    x = g['last_position'].to_numpy()
    cdf = np.cumsum(w) / w.sum()
    out = {}
    for q in mbp_qs:
        i = np.searchsorted(cdf, q, side='left')
        if i >= len(x): i = len(x) - 1
        out[q] = x[i]
    return pd.Series(out)

# Compute once: index = mb_event_start, columns = mbp_qs
mbp_pct_table = (
    mbp_df.groupby('mb_event_start', group_keys=False)
           .apply(mbp_weighted_percentiles)
           .sort_index()
)

mbp_min_date = mbp_pct_table.index.min().date() if not mbp_pct_table.empty else None
mbp_max_date = mbp_pct_table.index.max().date() if not mbp_pct_table.empty else None

# ----------------------------
# 2) Widgets (namespaced)
# ----------------------------
mbp_percentile_options = ['All'] + [mbp_q_labels[q] for q in mbp_qs]
mbp_w_percentiles = widgets.SelectMultiple(
    options=mbp_percentile_options, value=('All',),
    description='Percentiles:', rows=6, layout=widgets.Layout(width='260px')
)
mbp_w_start = widgets.DatePicker(description='Start', value=mbp_min_date)
mbp_w_end   = widgets.DatePicker(description='End',   value=mbp_max_date)
mbp_w_update = widgets.Button(description='Update', button_style='primary')
mbp_controls = widgets.HBox([mbp_w_percentiles, mbp_w_start, mbp_w_end, mbp_w_update])

mbp_out = widgets.Output()

def mbp_parse_qs(sel):
    if ('All' in sel) or (len(sel) == 0):
        return mbp_qs
    return [float(s.split('th')[0]) / 100 for s in sel]

def mbp_slice(start_d, end_d):
    frame = mbp_pct_table
    if start_d: frame = frame.loc[pd.Timestamp(start_d):]
    if end_d:   frame = frame.loc[:pd.Timestamp(end_d)]
    return frame

# ----------------------------
# 3) Render (replaces plot each time)
# ----------------------------
def mbp_update_plot(*_):
    frame = mbp_slice(mbp_w_start.value, mbp_w_end.value)
    sel_qs = mbp_parse_qs(mbp_w_percentiles.value)

    with mbp_out:
        mbp_out.clear_output(wait=True)
        fig, ax = plt.subplots(figsize=(20, 6))

        if frame.empty:
            ax.set_title("No data for the selected range")
            ax.set_xlabel("MB Event Start Date"); ax.set_ylabel("Last Position")
            ax.grid(True, alpha=0.3)
            plt.show()
            return

        # Plot selected percentile lines as integers
        for q in sel_qs:
            if q in frame.columns:
                ax.plot(frame.index, frame[q].astype(int), label=mbp_q_labels[q])

        ax.set_xlabel('MB Event Start Date')
        ax.set_ylabel('Last Position (integer)')
        ax.set_title('Player Last Position — Weighted Percentiles by MB Event Start', pad='100')
        ax.grid(True, alpha=0.5)

        # X ticks: every actual event date (thin labels if too many)
        tick_vals = frame.index.to_numpy()
        max_labels = 60  # adjust if you want more/less labels shown
        step = max(1, int(np.ceil(len(tick_vals) / max_labels)))
        ax.set_xticks(tick_vals[::step])
        ax.set_xticklabels([pd.to_datetime(d).strftime('%Y-%m-%d') for d in tick_vals[::step]],
                           rotation=45, ha='right')

        # Y ticks: integer only (no .5)
        ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        mbp_draw_story_markers(ax, frame.index.min(), frame.index.max())

        ax.legend()
        plt.tight_layout()
        plt.show()

mbp_w_update.on_click(mbp_update_plot)

display(mbp_controls, mbp_out)
mbp_update_plot()
