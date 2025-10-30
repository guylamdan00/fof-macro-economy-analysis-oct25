#@title Balance BOP vs EOP by Percentile (namespaced: bep_*)

# ----------------------------
# One-time preprocess (namespaced)
# ----------------------------
bep_df = player_balance.copy()
bep_df['promo_date'] = pd.to_datetime(bep_df['promo_date']).dt.normalize()

bep_qs = [0.5, 0.75, 0.9, 0.95, 0.99]
bep_q_labels = {q: f"{int(q*100)}th percentile" for q in bep_qs}

def bep_compute_quantiles(col: str):
    if col not in bep_df.columns:
        return None
    by_payer = (
        bep_df.groupby(['is_payer','promo_date'])[col]
              .quantile(q=bep_qs).unstack()
              .rename_axis(index=['is_payer','promo_date'], columns='q')
    )
    overall = (
        bep_df.groupby('promo_date')[col]
              .quantile(q=bep_qs).unstack()
              .rename_axis(index='promo_date', columns='q')
    )
    overall.index = pd.MultiIndex.from_product(
        [['All'], overall.index], names=['is_payer','promo_date']
    )
    return pd.concat([overall, by_payer]).sort_index()

bep_quantiles_eop = bep_compute_quantiles("energy_balance_eop")
bep_quantiles_bop = bep_compute_quantiles("energy_balance_bop")

# Campaign start detection (namespaced)
bep_camp = (
    bep_df[['promo_date','main_story']]
    .drop_duplicates('promo_date')
    .sort_values('promo_date')
)
bep_prev = bep_camp['main_story'].shift()
bep_campaign_starts = bep_camp[
    (bep_camp['main_story'].notna()) &
    ((bep_prev.isna()) | (bep_camp['main_story'] != bep_prev))
].reset_index(drop=True)

bep_min_date = bep_df['promo_date'].min().date() if not bep_df.empty else date.today()
bep_max_date = bep_df['promo_date'].max().date() if not bep_df.empty else date.today()

# ----------------------------
# Widgets (namespaced)
# ----------------------------
bep_percentile_options = ['All'] + [bep_q_labels[q] for q in bep_qs]
bep_w_percentiles = widgets.SelectMultiple(
    options=bep_percentile_options, value=('All',),
    description='Percentiles:', rows=6,
    layout=widgets.Layout(width='260px')
)
bep_w_payer = widgets.Dropdown(options=['All', 0, 1], value='All', description='Is Payer:')
bep_w_start = widgets.DatePicker(description='Start', value=bep_min_date)
bep_w_end   = widgets.DatePicker(description='End',   value=bep_max_date)
bep_w_update = widgets.Button(description='Update', button_style='primary')
bep_controls = widgets.HBox([bep_w_percentiles, bep_w_payer, bep_w_start, bep_w_end, bep_w_update])

# Single controlled output area (namespaced)
bep_out = widgets.Output()

def bep_parse_qs(sel):
    if ('All' in sel) or (len(sel) == 0):
        return bep_qs
    return [float(s.split('th')[0]) / 100 for s in sel]

def bep_slice(is_payer, start_d, end_d, qframe):
    if qframe is None:
        return pd.DataFrame(columns=bep_qs)
    if is_payer not in qframe.index.get_level_values(0):
        return pd.DataFrame(columns=bep_qs)
    frame = qframe.xs(is_payer, level='is_payer')
    if start_d: frame = frame.loc[pd.Timestamp(start_d):]
    if end_d:   frame = frame.loc[:pd.Timestamp(end_d)]
    return frame

# ----------------------------
# Update (plots EOP solid, BOP dashed + campaign markers) — namespaced
# ----------------------------
def bep_update_plot(*_):
    frame_eop = bep_slice(bep_w_payer.value, bep_w_start.value, bep_w_end.value, bep_quantiles_eop)
    frame_bop = bep_slice(bep_w_payer.value, bep_w_start.value, bep_w_end.value, bep_quantiles_bop)
    sel_qs = bep_parse_qs(bep_w_percentiles.value)

    # Filter campaign starts to the selected window
    start_d = pd.Timestamp(bep_w_start.value) if bep_w_start.value else None
    end_d   = pd.Timestamp(bep_w_end.value)   if bep_w_end.value   else None
    camp_window = bep_campaign_starts.copy()
    if start_d is not None:
        camp_window = camp_window[camp_window['promo_date'] >= start_d]
    if end_d is not None:
        camp_window = camp_window[camp_window['promo_date'] <= end_d]

    with bep_out:
        bep_out.clear_output(wait=True)
        fig, ax = plt.subplots(figsize=(20, 6))

        if frame_eop.empty and frame_bop.empty:
            ax.set_title("No data for the selected filters")
            ax.set_xlabel("Promo Date"); ax.set_ylabel("Balance")
            ax.grid(True, alpha=0.3)
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=1))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            fig.autofmt_xdate()
            # Draw campaign markers even if no lines (optional)
            for _, row in camp_window.iterrows():
                ax.axvline(row['promo_date'], linestyle=':', linewidth=1, alpha=0.25)
                ax.annotate(str(row['main_story']), xy=(row['promo_date'], 1), xycoords=('data', 'axes fraction'),
                            xytext=(2, -5), textcoords='offset points', rotation=90, va='top', fontsize=8)
            plt.show()
            return

        used = False
        for q in sel_qs:
            if q in frame_eop.columns:
                ax.plot(frame_eop.index, frame_eop[q], label=f"eop {bep_q_labels[q]}", linestyle='-')
                used = True
            if q in frame_bop.columns:
                ax.plot(frame_bop.index, frame_bop[q], label=f"bop {bep_q_labels[q]}", linestyle='--')
                used = True

        ax.set_xlabel('Promo Date')
        ax.set_ylabel('Balance')
        ax.set_title('Balance BOP vs EOP Percentiles Over Time')
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

# Wire button (namespaced)
bep_w_update.on_click(bep_update_plot)

display(bep_controls, bep_out)
bep_update_plot()
