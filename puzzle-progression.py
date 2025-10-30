#@title PUZZLE — Players % by Levels Completed per Event (Matplotlib) + Max-Level & Config Filters
# --- NEW style parameters you can tweak ---
pzml_colormap_name   = 'viridis'   # good options: 'viridis', 'plasma', 'cividis', 'magma'
pzml_cmap_span       = (0.15, 0.95) # use the middle of the palette for better sensitivity/contrast
pzml_label_min_pct   = 3.0          # don't label tiny slivers (< this % of total)
pzml_label_fmt       = "{:.0f}%"    # e.g., "{:.1f}%" if you want one decimal
pzml_label_fontsize  = 9
pzml_label_big_cut   = 12.0         # segments >= this % get white text for contrast


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import ipywidgets as widgets
from IPython.display import display, clear_output
import matplotlib.cm as cm
import matplotlib.ticker as mticker

# ----------------------------
# 1) Minimal preprocessing
# ----------------------------
pzml_base = puzzle_progression[
    ['player_id','levels_completed','puzzle_config_display_name','puzzle_event_starts_at']
].copy()

pzml_base['puzzle_event_starts_at'] = pd.to_datetime(
    pzml_base['puzzle_event_starts_at'], errors='coerce'
).dt.normalize()
pzml_base['levels_completed'] = pd.to_numeric(
    pzml_base['levels_completed'], errors='coerce'
)
pzml_base = pzml_base.dropna(
    subset=['player_id','levels_completed','puzzle_config_display_name','puzzle_event_starts_at']
)

# ----------------------------
# 2) Smart config groups (by MAX levels)
# ----------------------------
pzml_cfg_max = (
    pzml_base.groupby('puzzle_config_display_name')['levels_completed']
             .max()
             .rename('max_levels')
             .reset_index()
)

pzml_available_levels = sorted(pzml_cfg_max['max_levels'].dropna().astype(int).unique().tolist())

# ----------------------------
# 3) UI controls
# ----------------------------
pzml_levels_dropdown = widgets.Dropdown(
    options=['All'] + pzml_available_levels,
    value='All',
    description='Max levels:',
    layout=widgets.Layout(width='250px')
)

pzml_config_dropdown = widgets.SelectMultiple(
    options=['All'],  # placeholder, will update dynamically
    value=('All',),
    description='Config(s):',
    layout=widgets.Layout(width='500px', height='120px')
)

pzml_update_btn = widgets.Button(
    description='Update',
    button_style='primary',
    layout=widgets.Layout(width='100px')
)

pzml_out = widgets.Output()

# ----------------------------
# 4) Data filtering
# ----------------------------
def pzml_get_filtered_df(level_choice, configs_selected):
    """Return filtered dataframe by max level & specific config selections."""
    # Filter by max-level bucket
    if level_choice == 'All':
        df = pzml_base.copy()
    else:
        allowed_configs = set(
            pzml_cfg_max.loc[pzml_cfg_max['max_levels'] == int(level_choice), 'puzzle_config_display_name']
        )
        df = pzml_base[pzml_base['puzzle_config_display_name'].isin(allowed_configs)]

    # Then filter by specific configs (if not "All")
    if configs_selected and 'All' not in configs_selected:
        df = df[df['puzzle_config_display_name'].isin(configs_selected)]

    return df

# ----------------------------
# 5) Draw function
# ----------------------------
def pzml_draw(level_choice, configs_selected):
    pzml_df = pzml_get_filtered_df(level_choice, configs_selected)
    if pzml_df.empty:
        print("No data for the selected filters.")
        return

    # aggregate unique players per (event, level)
    pzml_agg = (
        pzml_df.groupby(['puzzle_event_starts_at','levels_completed'])['player_id']
               .nunique()
               .reset_index(name='unique_players')
    )
    if pzml_agg.empty:
        print("No data after aggregation.")
        return

    # totals per event + percent
    pzml_tot = (
        pzml_agg.groupby('puzzle_event_starts_at')['unique_players']
                .sum().reset_index(name='total_unique_players')
    )
    pzml_agg = pzml_agg.merge(pzml_tot, on='puzzle_event_starts_at', how='left')
    pzml_agg['pct_of_total'] = (pzml_agg['unique_players'] / pzml_agg['total_unique_players']) * 100

    # pivot to wide
    pzml_pivot = pzml_agg.pivot_table(
        index='puzzle_event_starts_at',
        columns='levels_completed',
        values='pct_of_total',
        fill_value=0.0
    ).sort_index()

    if pzml_pivot.empty:
        print("No data to display after pivot.")
        return

    # ---- Color scale (sensitive slice of the colormap) ----
    level_cols = sorted(pzml_pivot.columns.tolist())
    n_levels = max(1, len(level_cols))
    cmap = cm.get_cmap(pzml_colormap_name)
    # Sample within a central range for better sensitivity
    samples = np.linspace(pzml_cmap_span[0], pzml_cmap_span[1], n_levels)
    level_colors = {lvl: cmap(s) for lvl, s in zip(level_cols, samples)}

    # ---- Matplotlib stacked 100% bar ----
    fig, ax = plt.subplots(figsize=(14, 5))
    x = np.arange(len(pzml_pivot.index))
    bottoms = np.zeros(len(pzml_pivot.index))

    # Plot each level with its colormap-derived color
    for lvl in level_cols:
        heights = pzml_pivot[lvl].values
        ax.bar(x, heights, bottom=bottoms, label=str(lvl), color=level_colors[lvl], edgecolor='none')
        # Add labels for sufficiently large segments
        for i, h in enumerate(heights):
            if h >= pzml_label_min_pct:
                # choose text color for contrast based on segment size
                txt_color = 'white' if h >= pzml_label_big_cut else 'black'
                ax.text(
                    x[i],
                    bottoms[i] + h/2.0,
                    pzml_label_fmt.format(h),
                    ha='center', va='center',
                    fontsize=pzml_label_fontsize,
                    color=txt_color
                )
        bottoms += heights

    # X-axis labels
    ax.set_xticks(x)
    ax.set_xticklabels(
        [pd.to_datetime(d).strftime('%Y-%m-%d') for d in pzml_pivot.index],
        rotation=45, ha='right'
    )

    # Y-axis, title, legend, grid
    ax.set_ylim(0, 100)
    ax.set_ylabel('% of players')
    ax.set_xlabel('Event start')

    cfg_summary = (
        "All configs" if not configs_selected or 'All' in configs_selected
        else f"{len(configs_selected)} selected config(s)"
    )
    suffix = f"MAX levels = {level_choice}" if level_choice != 'All' else "All levels"
    ax.set_title(f'Players % by Levels Completed per PUZZLE Event — {suffix}, {cfg_summary}')

    # Cleaner legend with level order (lowest at bottom)
    handles, labels = ax.get_legend_handles_labels()
    order = np.argsort([int(l) for l in labels])
    ax.legend(
        [handles[i] for i in order],
        [labels[i] for i in order],
        title='Levels completed',
        bbox_to_anchor=(1.02, 1), loc='upper left',
        frameon=False
    )

    ax.grid(axis='y', linestyle=':', linewidth=0.7, alpha=0.7)
    plt.tight_layout()
    plt.show()

# ----------------------------
# 6) UI logic: update config list dynamically
# ----------------------------
def pzml_update_config_list(change=None):
    """When the max-level dropdown changes, update config list options."""
    level_choice = pzml_levels_dropdown.value
    if level_choice == 'All':
        available_configs = sorted(pzml_cfg_max['puzzle_config_display_name'].unique().tolist())
    else:
        available_configs = sorted(
            pzml_cfg_max.loc[pzml_cfg_max['max_levels'] == int(level_choice), 'puzzle_config_display_name']
            .unique().tolist()
        )
    pzml_config_dropdown.options = ['All'] + available_configs
    pzml_config_dropdown.value = ('All',)

# ----------------------------
# 7) Update function (triggered by button or dropdowns)
# ----------------------------
def pzml_update(_=None):
    with pzml_out:
        clear_output(wait=True)
        pzml_draw(pzml_levels_dropdown.value, pzml_config_dropdown.value)

# Link interactions
pzml_update_btn.on_click(pzml_update)
pzml_levels_dropdown.observe(lambda change: (pzml_update_config_list(), pzml_update()), names='value')
pzml_config_dropdown.observe(lambda change: pzml_update(), names='value')

# ----------------------------
# 8) Display controls & first draw
# ----------------------------
display(widgets.HBox([pzml_levels_dropdown, pzml_config_dropdown, pzml_update_btn]))
display(pzml_out)

pzml_update_config_list()
pzml_update()
