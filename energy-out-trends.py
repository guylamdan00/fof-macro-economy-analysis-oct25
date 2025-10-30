#@title Total Energy Out by Percentile

# ----------------------------
# One-time preprocess
# ----------------------------
pb_widget = player_balance.copy()
pb_widget['promo_date'] = pd.to_datetime(pb_widget['promo_date']).dt.normalize()
pb_widget['total_energy_out'] = pd.to_numeric(pb_widget['total_energy_out'], errors='coerce')

qs = [0.5, 0.75, 0.9, 0.95, 0.99]
q_labels = {q: f"{int(q*100)}th percentile" for q in qs}

def compute_quantiles(col):
    if col not in pb_widget.columns:
        return None
    # percentiles of per-player values per day (optionally by is_payer)
    by_payer = (
        pb_widget.groupby(['is_payer','promo_date'])[col]
          .quantile(q=qs).unstack().rename_axis(index=['is_payer','promo_date'], columns='q')
    )
    overall = (
        pb_widget.groupby('promo_date')[col]
          .quantile(q=qs).unstack().rename_axis(index='promo_date', columns='q')
    )
    overall.index = pd.MultiIndex.from_product([['All'], overall.index], names=['is_payer','promo_date'])
    return pd.concat([overall, by_payer]).sort_index()

quantiles_toe = compute_quantiles("total_energy_out")

# --- campaign start detection (precompute once) ---
# A "start" = main_story is non-null AND different from previous day.
camp = (
    pb_widget[['promo_date','main_story']]
    .drop_duplicates('promo_date')
    .sort_values('promo_date')
)
prev = camp['main_story'].shift()
campaign_starts = camp[
    (camp['main_story'].notna()) &
    ((prev.isna()) | (camp['main_story'] != prev))
].reset_index(drop=True)

min_date = pb_widget['promo_date'].min().date() if not pb_widget.empty else date.today()
max_date = pb_widget['promo_date'].max().date() if not pb_widget.empty else date.today()

# ----------------------------
# Widgets
# ----------------------------
percentile_options = ['All'] + [q_labels[q] for q in qs]
w_percentiles = widgets.SelectMultiple(
    options=percentile_options, value=('All',), description='Percentiles:', rows=6,
    layout=widgets.Layout(width='260px')
)
w_payer = widgets.Dropdown(options=['All', 0, 1], value='All', description='Is Payer:')
w_start = widgets.DatePicker(description='Start', value=min_date)
w_end   = widgets.DatePicker(description='End',   value=max_date)
w_update = widgets.Button(description='Update', button_style='primary')
controls = widgets.HBox([w_percentiles, w_payer, w_start, w_end, w_update])

# Single controlled output area
out = widgets.Output()

def _parse_qs(sel):
    if ('All' in sel) or (len(sel) == 0):
        return qs
    return [float(s.split('th')[0]) / 100 for s in sel]

def _slice(is_payer, start_d, end_d, qframe):
    if qframe is None:
        return pd.DataFrame(columns=qs)
    if is_payer not in qframe.index.get_level_values(0):
        return pd.DataFrame(columns=qs)
    frame = qframe.xs(is_payer, level='is_payer')  # DateTimeIndex, columns=qs
    if start_d: frame = frame.loc[pd.Timestamp(start_d):]
    if end_d:   frame = frame.loc[:pd.Timestamp(end_d)]
    return frame

# ----------------------------
# Update (plots total_energy_out percentiles + campaign markers)
# ----------------------------
def update_plot(*_):
    start_d = pd.Timestamp(w_start.value) if w_start.value else None
    end_d   = pd.Timestamp(w_end.value)   if w_end.value   else None

    frame = _slice(w_payer.value, start_d, end_d, quantiles_toe)
    sel_qs = _parse_qs(w_percentiles.value)

    # Filter campaign starts to the selected window
    camp_window = campaign_starts.copy()
    if start_d is not None:
        camp_window = camp_window[camp_window['promo_date'] >= start_d]
    if end_d is not None:
        camp_window = camp_window[camp_window['promo_date'] <= end_d]

    with out:
        out.clear_output(wait=True)
        fig, ax = plt.subplots(figsize=(20, 6))

        if frame.empty:
            ax.set_title("No data for the selected filters")
            ax.set_xlabel("Promo Date"); ax.set_ylabel("Total Energy Out (per-player percentiles)")
            ax.grid(True, alpha=0.3)
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=1))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            fig.autofmt_xdate()
            for _, row in camp_window.iterrows():
                ax.axvline(row['promo_date'], linestyle=':', linewidth=1, alpha=0.25)
                ax.annotate(str(row['main_story']), xy=(row['promo_date'], 1), xycoords=('data', 'axes fraction'),
                            xytext=(2, -5), textcoords='offset points', rotation=90, va='top', fontsize=8)
            plt.show()
            return

        used = False
        for q in sel_qs:
            if q in frame.columns:
                ax.plot(frame.index, frame[q], label=q_labels[q])
                used = True

        ax.set_xlabel('Promo Date')
        ax.set_ylabel('Total Energy Out (per-player percentile)')
        ax.set_title('Total Energy Out Percentiles Over Time')
        ax.grid(True, alpha=0.3)

        # Weekly ticks on Mondays
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate()

        # Campaign markers & labels
        for _, row in camp_window.iterrows():
            ax.axvline(row['promo_date'], linestyle=':', linewidth=1, alpha=0.25)
            ax.annotate(str(row['main_story']), xy=(row['promo_date'], 1), xycoords=('data', 'axes fraction'),
                        xytext=(2, -5), textcoords='offset points', rotation=90, va='top', fontsize=8)

        if used:
            ax.legend()
        plt.show()

# Wire button (or use .observe for live updates)
w_update.on_click(update_plot)

display(controls, out)
update_plot()
