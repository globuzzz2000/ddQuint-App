#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Well plot visualization (individual plots only).

Moved from ddquint.visualization.well_plots and trimmed to remove
individual plotting.
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.ticker as ticker
import logging

from ..config import Config, VisualizationError

logger = logging.getLogger(__name__)


def create_well_plot(df, clustering_results, well_id, save_path,
                    add_copy_numbers=True, sample_name=None):
    """
    Create an individual well scatter plot with copy number annotations.
    Always plot as much information as available:
      - Plot raw droplets as 'Unclustered' when df is available
      - Overlay clustered/filtered droplets in target colors when available
      - Always include 'Unclustered' in legend if raw data was plotted
    """
    config = Config.get_instance()
    logger.debug(f"Creating well plot for {well_id}")

    try:
        fig, ax = _create_base_plot(config)
        _apply_axis_formatting(ax, config)

        # Track whether we plot unclustered so legend can include it
        plotted_unclustered = False

        # 1) Plot raw droplets as 'Unclustered' when df is available
        if df is not None and not df.empty:
            _add_raw_data_content(ax, df)
            plotted_unclustered = True

        # 2) Overlay clustered/filtered droplets if available and valid
        try:
            df_filtered = clustering_results.get('df_filtered') if isinstance(clustering_results, dict) else None
            target_mapping = clustering_results.get('target_mapping') if isinstance(clustering_results, dict) else None
            counts = clustering_results.get('counts', {}) if isinstance(clustering_results, dict) else {}
            copy_numbers = clustering_results.get('copy_numbers') if isinstance(clustering_results, dict) else None
            copy_number_states = clustering_results.get('copy_number_states', {}) if isinstance(clustering_results, dict) else {}

            if df_filtered is not None and hasattr(df_filtered, 'empty') and not df_filtered.empty:
                # Overlay filtered points using TargetLabel; do not require target_mapping
                label_color_map = dict(config.TARGET_COLORS or {})
                df_filtered_copy = df_filtered.copy()
                unknown_color = label_color_map.get('Unknown', '#c7c7c7')
                # Split unknown vs others
                is_unknown = df_filtered_copy['TargetLabel'] == 'Unknown'
                df_known = df_filtered_copy[~is_unknown]
                df_unknown = df_filtered_copy[is_unknown]
                if not df_known.empty:
                    colors_known = df_known['TargetLabel'].map(label_color_map).fillna(unknown_color).astype(str).tolist()
                    ax.scatter(df_known['Ch2Amplitude'], df_known['Ch1Amplitude'], c=colors_known, s=8, alpha=0.6)
                if not df_unknown.empty:
                    ax.scatter(df_unknown['Ch2Amplitude'], df_unknown['Ch1Amplitude'], c=unknown_color, s=6, alpha=0.5)

                # Copy number annotations when requested
                if add_copy_numbers and copy_numbers:
                    _add_copy_number_annotations(ax, df_filtered_copy, copy_numbers, copy_number_states, label_color_map)

            # 3) Legend: targets + Unclustered when raw was plotted
            label_color_map = config.TARGET_COLORS
            _add_legend(ax, label_color_map, counts, has_unclustered=plotted_unclustered)
        except Exception as e:
            logger.debug(f"Overlay/legend section failed: {e}", exc_info=True)

        _set_plot_labels_and_title(ax, well_id, sample_name)

        dpi = config.get_plot_dpi('individual')
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        logger.debug(f"Well plot saved to: {save_path} (DPI: {dpi})")
        return save_path
    except Exception as e:
        logger.error(f"Error creating well plot for {well_id}: {e}")
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        return None


def _create_base_plot(config):
    """Create the base figure and axes for individual plots."""
    fig_size = config.get_plot_dimensions()
    fig = plt.figure(figsize=fig_size)
    ax = fig.add_axes([0.1, 0.1, 0.7, 0.8])
    return fig, ax


def _apply_axis_formatting(ax, config, border_color='#B0B0B0'):
    """Apply consistent axis formatting."""
    axis_limits = config.get_axis_limits()
    ax.set_xlim(axis_limits['x'])
    ax.set_ylim(axis_limits['y'])
    ax.grid(True, alpha=0.4, linewidth=0.8)
    grid_intervals = config.get_grid_intervals()
    ax.xaxis.set_major_locator(ticker.MultipleLocator(grid_intervals['x']))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(grid_intervals['y']))
    ax.set_aspect('auto')
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1.0)
        spine.set_color(border_color)


def _is_error_result(clustering_results):
    return clustering_results.get('error') is not None


def _has_insufficient_data(df, clustering_results, config):
    # Deprecated: we always plot what we have (raw + filtered overlay when available)
    return False


def _validate_clustering_data(clustering_results):
    return (
        'df_filtered' in clustering_results and clustering_results['df_filtered'] is not None and
        not clustering_results['df_filtered'].empty and
        'target_mapping' in clustering_results and clustering_results['target_mapping'] is not None
    )


def _add_raw_data_with_error(ax, df, clustering_results, well_id):
    df_filtered = clustering_results.get('df_filtered')
    target_mapping = clustering_results.get('target_mapping')
    label_color_map = Config.get_instance().TARGET_COLORS

    if df_filtered is not None and not df_filtered.empty:
        logger.debug(f"Plotting {len(df_filtered)} clustered droplets for well {well_id} with error context")
        df_filtered_copy = df_filtered.copy()
        # Split unknown vs others for consistent styling
        unknown_color = label_color_map.get('Unknown', '#c7c7c7')
        is_unknown = df_filtered_copy['TargetLabel'] == 'Unknown'
        df_known = df_filtered_copy[~is_unknown]
        df_unknown = df_filtered_copy[is_unknown]
        if not df_known.empty:
            colors_known = df_known['TargetLabel'].map(label_color_map).fillna(unknown_color).astype(str).tolist()
            ax.scatter(df_known['Ch2Amplitude'], df_known['Ch1Amplitude'], c=colors_known, s=8, alpha=0.6)
        if not df_unknown.empty:
            ax.scatter(df_unknown['Ch2Amplitude'], df_unknown['Ch1Amplitude'], c=unknown_color, s=6, alpha=0.5)
        counts = clustering_results.get('counts', {})
        _add_legend(ax, label_color_map, counts)
    else:
        unknown_color = Config.get_instance().TARGET_COLORS.get('Unknown', '#c7c7c7')
        ax.scatter(df['Ch2Amplitude'], df['Ch1Amplitude'], c=unknown_color, s=8, alpha=0.6)


def _add_raw_data_content(ax, df):
    unknown_color = Config.get_instance().TARGET_COLORS.get('Unknown', '#c7c7c7')
    # Plot raw droplets with the same styling as 'Unknown' (s=6, alpha=0.5)
    ax.scatter(df['Ch2Amplitude'], df['Ch1Amplitude'], c=unknown_color, s=6, alpha=0.5)


def _add_data_content(ax, df, clustering_results, well_id, add_copy_numbers, sample_name, config):
    df_filtered = clustering_results['df_filtered']
    counts = clustering_results['counts']
    copy_numbers = clustering_results['copy_numbers']
    label_color_map = config.TARGET_COLORS

    logger.debug(f"Plotting {len(df_filtered)} filtered droplets for well {well_id}")

    clustered_indices = set(df_filtered.index)
    # Be robust: if df is None or empty, skip; else compute unclustered
    df_unclustered = df[~df.index.isin(clustered_indices)] if df is not None and not df.empty else None

    unknown_color = label_color_map.get('Unknown', '#c7c7c7')
    if df_unclustered is not None and not df_unclustered.empty:
        ax.scatter(df_unclustered['Ch2Amplitude'], df_unclustered['Ch1Amplitude'],
                   c=unknown_color, s=6, alpha=0.5)

    df_filtered_copy = df_filtered.copy()
    df_filtered_copy['color'] = df_filtered_copy['TargetLabel'].map(label_color_map)
    colors = df_filtered_copy['color'].fillna(label_color_map.get('Unknown', '#c7c7c7')).astype(str).tolist()
    ax.scatter(df_filtered_copy['Ch2Amplitude'], df_filtered_copy['Ch1Amplitude'], c=colors, s=8, alpha=0.6)

    # Fallback: if everything above produced no visible points and raw df exists, plot raw to avoid empty plot
    try:
        if (df_unclustered is None or df_unclustered.empty) and df is not None and not df.empty and df_filtered_copy.empty:
            ax.scatter(df['Ch2Amplitude'], df['Ch1Amplitude'], c=unknown_color, s=6, alpha=0.5)
    except Exception:
        pass

    if add_copy_numbers and copy_numbers:
        _add_copy_number_annotations(ax, df_filtered_copy, copy_numbers,
                                     clustering_results.get('copy_number_states', {}),
                                     label_color_map)

    _add_legend(ax, label_color_map, counts, has_unclustered=(not df_unclustered.empty))


def _add_copy_number_annotations(ax, df_filtered, copy_numbers, copy_number_states, label_color_map):
    logger.debug("Adding copy number annotations")
    from .copy_number import apply_copy_number_display_multiplier
    display_copy_numbers = apply_copy_number_display_multiplier(copy_numbers)
    for target, color in label_color_map.items():
        if target not in ['Negative', 'Unknown'] and target in copy_numbers:
            target_points = df_filtered[df_filtered['TargetLabel'] == target]
            if not target_points.empty:
                cx = target_points['Ch2Amplitude'].mean()
                cy = target_points['Ch1Amplitude'].mean()
                cn_value = display_copy_numbers[target]
                cn_text = f"{cn_value:.2f}"
                state = copy_number_states.get(target, 'euploid')
                font_size = 12
                font_weight = 'bold' if state in ['aneuploidy', 'buffer_zone'] else 'normal'
                if state == 'aneuploidy':
                    text_color = 'darkred'
                elif state == 'buffer_zone':
                    text_color = 'darkslategray'
                else:
                    text_color = 'black'
                ax.text(cx, cy, cn_text, color=text_color, fontsize=font_size, fontweight=font_weight,
                        ha='center', va='center',
                        bbox=dict(facecolor='white', alpha=0.7, pad=1, edgecolor='none'))


def _add_legend(ax, label_color_map, counts, has_unclustered=False):
    from ..config import Config
    try:
        ordered_labels = Config.get_ordered_labels()
    except Exception:
        ordered_labels = ['Negative', 'Chrom1', 'Chrom2', 'Chrom3', 'Chrom4', 'Chrom5']

    def get_display_name(internal_name):
        if internal_name in ('Negative', 'Unknown', 'Unclustered'):
            return internal_name
        if internal_name.startswith('Chrom'):
            try:
                chrom_num = internal_name[5:]
                target_key = f'Target{chrom_num}'
                target_names = Config.get_target_names()
                if target_names and target_key in target_names and target_names[target_key].strip():
                    return target_names[target_key].strip()
                return target_key
            except Exception:
                return internal_name
        return internal_name

    legend_handles = []
    for tgt in ordered_labels:
        if tgt not in counts or counts[tgt] == 0 or tgt == 'Unknown':
            continue
        color = label_color_map[tgt]
        display_name = get_display_name(tgt)
        handle = mpl.lines.Line2D([], [], marker='o', linestyle='', markersize=10,
                                  markerfacecolor=color, markeredgecolor='none', label=display_name)
        legend_handles.append(handle)

    # Include 'Unclustered' legend entry if raw was plotted or Unknown counts exist
    include_unclustered = has_unclustered or (counts.get('Unknown', 0) > 0)
    if include_unclustered:
        unknown_color = label_color_map.get('Unknown', '#c7c7c7')
        unclustered_handle = mpl.lines.Line2D([], [], marker='o', linestyle='', markersize=10,
                                              markerfacecolor=unknown_color, markeredgecolor='none', label='Unclustered')
        legend_handles.append(unclustered_handle)

    ax.legend(handles=legend_handles, title="Target", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)


def _set_plot_labels_and_title(ax, well_id, sample_name):
    ax.set_xlabel("HEX Amplitude")
    ax.set_ylabel("FAM Amplitude")
    if sample_name:
        ax.set_title(f"Well {well_id} - {sample_name}")
    else:
        ax.set_title(f"Well {well_id}")


def create_placeholder_plot(well_id, save_path):
    """Create a placeholder plot."""
    config = Config.get_instance()
    logger.debug(f"Creating placeholder plot for {well_id}")
    try:
        fig, ax = _create_base_plot(config)
        _apply_axis_formatting(ax, config)
        dpi = config.get_plot_dpi('placeholder')
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        return save_path
    except Exception as e:
        logger.error(f"Error creating placeholder plot for {well_id}: {e}")
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        return None
