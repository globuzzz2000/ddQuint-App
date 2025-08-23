#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parameter editor GUI for ddQuint with user-friendly interface and comprehensive tooltips.

Provides a graphical interface for editing frequently modified parameters
like EXPECTED_CENTROIDS, clustering parameters, copy number settings,
and visualization options. Stores settings in a separate parameters
file for easy management.

Parameter Priority Order:
1. User parameters file (highest priority - trumps everything)
2. Config file specified with --config
3. Default config.py values (lowest priority)
"""

import os
import json
import sys
import logging
import contextlib

from ..config.exceptions import ConfigError

logger = logging.getLogger(__name__)

# Parameters file location
USER_SETTINGS_DIR = os.path.join(os.path.expanduser("~"), ".ddquint")
PARAMETERS_FILE = os.path.join(USER_SETTINGS_DIR, "parameters.json")

# Comprehensive tooltip definitions
PARAMETER_TOOLTIPS = {
    # Expected Centroids
    'centroids_grid': """Expected Centroid Positions

Define the expected fluorescence positions for each target chromosome.
These positions are used to assign detected clusters to specific targets.

💡 Tips:
• Measure actual centroids from control samples
• Each chromosome should have distinct positions""",

    'base_tolerance': """Base Target Tolerance

Base tolerance distance for matching detected clusters to expected centroids.
Clusters within this distance are assigned to the nearest target.

💡 Tips:
• Higher values = more lenient matching
• Lower values = stricter, more precise matching
• Adjust based on your assay's cluster tightness""",

    'scale_min': """Scale Factor Minimum

Minimum scale factor for adaptive tolerance adjustment.
Controls how tolerance scales at different fluorescence intensities.

💡 Tips:
• Range: 0.1-1.0
• Lower values = tighter matching requirements
• 0.5 = tolerance can shrink to 50% of base value
• Use lower values for well-separated targets""",

    'scale_max': """Scale Factor Maximum

Maximum scale factor for adaptive tolerance adjustment.
Controls maximum tolerance expansion at high fluorescence.

💡 Tips:
• Range: 1.0-2.0
• Higher values = more flexible matching
• 1.0 = no expansion (constant tolerance)
• Use higher values if clusters spread at high intensity""",

    # Clustering Settings
    'min_cluster_size': """HDBSCAN Min Cluster Size

Minimum number of droplets required to form a cluster.
Smaller clusters are treated as noise and ignored.

💡 Tips:
• Lower values (2-4): More sensitive, detects small clusters
• Higher values (8-15): More conservative, ignores noise
• Increase if too many noise clusters detected""",

    'min_samples': """HDBSCAN Min Samples

Minimum points in neighborhood for core point classification.
Controls how conservative the clustering algorithm is.

💡 Tips:
• Higher values = denser, more conservative clusters
• Lower values = more loose, inclusive clusters
• Increase if clusters are too fragmented""",

    'epsilon': """HDBSCAN Epsilon

Distance threshold for cluster selection from hierarchy.
Controls how clusters are extracted from the cluster tree.

💡 Tips:
• Lower values (0.01-0.05): Tighter, more separated clusters
• Higher values (0.1+): Merges nearby clusters
• Increase if legitimate clusters are split""",

    'metric': """Distance Metric

Distance metric used for clustering calculations.
Determines how distances between points are measured.

💡 Options:
• Euclidean: Standard straight-line distance (recommended)
• Manhattan: Sum of absolute differences
• Chebyshev: Maximum difference in any dimension
• Minkowski: Generalized distance metric""",

    'selection_method': """Cluster Selection Method

Method for selecting clusters from the hierarchy tree.
Determines which clusters are chosen as final results.

💡 Options:
• EOM (Excess of Mass): More stable, recommended
• Leaf: Selects leaf clusters, can be less stable""",

    'min_points': """Min Points for Clustering

Minimum total data points required before attempting clustering.
Prevents clustering on insufficient data.

💡 Tips:
• Higher values = more reliable clustering
• Lower values = clustering on sparse data""",

    # Copy Number Settings
    'min_droplets': """Min Usable Droplets

Minimum total droplets required for reliable copy number analysis.
Wells with fewer droplets are excluded from analysis.

💡 Tips:
• Higher values = better statistical confidence
• Lower values = include more wells but less reliable""",

    'median_threshold': """Median Deviation Threshold

Maximum deviation from median for selecting baseline (euploid) chromosomes.
Only chromosomes close to median are used for normalization.

💡 Tips:
• Lower values (0.10): Stricter baseline selection
• Higher values (0.20): More inclusive baseline""",

    'baseline_min': """Baseline Min Chromosomes

Minimum number of chromosomes needed to establish diploid baseline.
Ensures robust normalization with sufficient reference chromosomes.

💡 Tips:
• Higher values = more robust normalization
• Lower values = less stringent requirements""",

    'tolerance_multiplier': """Tolerance Multiplier

Multiplier applied to chromosome-specific standard deviation.
Controls width of classification ranges (euploid/aneuploidy).

💡 Tips:
• Higher values = wider tolerance ranges
• Lower values = stricter classification
• 3 = 99.7% confidence interval""",

    'deletion_target': """Aneuploidy Deletion Target

Target copy number ratio for chromosome deletions.
Relative to expected copy number.

💡 Tips:
• 0.75 = 75% of expected (3 copies instead of 4)
• Adjust based on your assay design""",

    'duplication_target': """Aneuploidy Duplication Target

Target copy number ratio for duplications.
Relative to expected copy number.

💡 Tips:
• 1.25 = 125% of expected (5 copies instead of 4)
• Adjust based on your assay design""",

    'copy_numbers_grid': """Expected Copy Numbers

Baseline copy number values for each chromosome.
Used for normalization and classification thresholds.

💡 Tips:
• Values should be close to 1.0
• Slight variations account for assay differences
• Measure from known control samples
• Update based on your specific assay performance""",

    'std_dev_grid': """Expected Standard Deviation

Standard deviation for each chromosome's copy number.
Used with tolerance multiplier to set classification ranges.

💡 Tips:
• Lower values = tighter classification ranges
• Higher values = more permissive classification
• Measure from known control samples""",

    # Visualization
    'x_axis_min': """X-Axis Minimum

Minimum value for X-axis (HEX fluorescence) in plots.
Sets the left boundary of the plot area.""",

    'x_axis_max': """X-Axis Maximum

Maximum value for X-axis (HEX fluorescence) in plots.
Sets the right boundary of the plot area.""",

    'y_axis_min': """Y-Axis Minimum

Minimum value for Y-axis (FAM fluorescence) in plots.
Sets the bottom boundary of the plot area.""",

    'y_axis_max': """Y-Axis Maximum

Maximum value for Y-axis (FAM fluorescence) in plots.
Sets the top boundary of the plot area.""",

    'x_grid_interval': """X-Grid Interval

Spacing between vertical grid lines on plots.
Helps with visual reference and measurement.""",

    'y_grid_interval': """Y-Grid Interval

Spacing between horizontal grid lines on plots.
Helps with visual reference and measurement.""",

    'individual_dpi': """Individual Plot DPI

Resolution for individual well plots in dots per inch.
Higher DPI creates better quality but larger file sizes.

💡 Tips:
• 150 DPI: Screen viewing, small files
• 300 DPI: Print quality, recommended
• 600 DPI: High-resolution, large files""",

    'composite_dpi': """Composite Plot DPI

Resolution for composite overview plots in dots per inch.
Balances quality with file size for multi-well images.

💡 Tips:
• 100-150 DPI: Overview purposes
• 200 DPI: Good balance (recommended)
• 300+ DPI: High quality, larger files"""
}

# Optional import for wxPython GUI
try:
    import wx
    import wx.grid
    HAS_WX = True
except ImportError:
    HAS_WX = False

# macOS compatibility
_is_macos = sys.platform == 'darwin'

@contextlib.contextmanager
def _silence_stderr():
    """Temporarily redirect stderr to suppress wxPython warnings on macOS."""
    if _is_macos:
        old_fd = os.dup(2)
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, 2)
            os.close(devnull)
            yield
        finally:
            os.dup2(old_fd, 2)
            os.close(old_fd)
    else:
        yield


def add_tooltip(control, tooltip_key):
    """
    Add tooltip to a control using predefined tooltip texts.
    
    Args:
        control: wxPython control to add tooltip to
        tooltip_key: Key in PARAMETER_TOOLTIPS dictionary
    """
    if tooltip_key in PARAMETER_TOOLTIPS:
        control.SetToolTip(PARAMETER_TOOLTIPS[tooltip_key])
    else:
        logger.debug(f"No tooltip defined for key: {tooltip_key}")


def create_labeled_control_with_tooltip(parent, label_text, control, tooltip_key, sizer):
    """
    Create a labeled control with tooltip and add to sizer.
    
    Args:
        parent: Parent panel
        label_text: Text for the label
        control: The control widget
        tooltip_key: Key for tooltip text
        sizer: Sizer to add to
    """
    label = wx.StaticText(parent, label=label_text)
    add_tooltip(label, tooltip_key)
    add_tooltip(control, tooltip_key)
    sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)
    sizer.Add(control, 1, wx.EXPAND)


class ParameterEditorFrame(wx.Dialog):
    """Main parameter editor dialog with tabbed interface."""
    
    def __init__(self, config_cls):
        super().__init__(None, title="ddQuint Parameter Editor", size=(850, 700))
        
        self.config_cls = config_cls
        self.parameters = self.load_parameters()
        self.modified = False
        
        self.init_ui()
        self.Bind(wx.EVT_INIT_DIALOG, self.on_init_dialog)
        self.Center()

    def on_init_dialog(self, event):
        """Handle final initializations after all controls are created."""
        self.load_values()
        event.Skip()
    
    def init_ui(self):
        """Initialize the user interface."""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        title = wx.StaticText(panel, label="ddQuint Parameter Editor")
        title_font = title.GetFont()
        title_font.PointSize += 4
        title_font = title_font.Bold()
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL | wx.CENTER, 10)
        
        # Priority info
        priority_text = wx.StaticText(panel, 
            label="Priority: User Parameters > Config File > Default Values")
        priority_text.SetFont(priority_text.GetFont().Smaller())
        main_sizer.Add(priority_text, 0, wx.ALL | wx.CENTER, 5)
        
        self.notebook = wx.Notebook(panel)
        
        self.centroids_panel = self.create_centroids_panel()
        self.notebook.AddPage(self.centroids_panel, "Expected Centroids")
        
        self.clustering_panel = self.create_clustering_panel()
        self.notebook.AddPage(self.clustering_panel, "Clustering Settings")
        
        self.copy_numbers_panel = self.create_copy_numbers_panel()
        self.notebook.AddPage(self.copy_numbers_panel, "Copy Number Settings")

        self.visualization_panel = self.create_visualization_panel()
        self.notebook.AddPage(self.visualization_panel, "Visualization")
        
        main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        reset_cfg_btn = wx.Button(panel, label="Reset to Config")
        reset_cfg_btn.Bind(wx.EVT_BUTTON, self.on_load_from_config)
        button_sizer.Add(reset_cfg_btn, 0, wx.ALL, 5)
        
        button_sizer.AddStretchSpacer()
        
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        button_sizer.Add(cancel_btn, 0, wx.ALL, 5)
        
        save_btn = wx.Button(panel, wx.ID_OK, "Save Parameters")
        save_btn.Bind(wx.EVT_BUTTON, self.on_save)
        button_sizer.Add(save_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(main_sizer)
    
    def create_centroids_panel(self):
        """Create the centroids editing panel with matching parameters."""
        panel = wx.Panel(self.notebook)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # --- Expected Centroids Grid ---
        centroids_box = wx.StaticBox(panel, label="Expected Centroid Positions")
        centroids_sizer = wx.StaticBoxSizer(centroids_box, wx.VERTICAL)
        
        instructions = wx.StaticText(panel, 
            label="Define expected centroid positions for targets (maximum 10 chromosomes).\n"
                  "Hover over controls for detailed help and tips.")
        centroids_sizer.Add(instructions, 0, wx.ALL, 5)
        
        self.centroids_grid = wx.grid.Grid(panel)
        self.centroids_grid.CreateGrid(10, 3)
        self.centroids_grid.SetColLabelValue(0, "Target Name")
        self.centroids_grid.SetColLabelValue(1, "FAM Fluorescence")
        self.centroids_grid.SetColLabelValue(2, "HEX Fluorescence")
        self.centroids_grid.SetColSize(0, 150)
        self.centroids_grid.SetColSize(1, 140)
        self.centroids_grid.SetColSize(2, 140)
        
        # Add tooltip to the grid
        add_tooltip(self.centroids_grid, 'centroids_grid')
        
        for i in range(10):
            self.centroids_grid.SetRowLabelValue(i, f"Target {i+1}")
        centroids_sizer.Add(self.centroids_grid, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(centroids_sizer, 1, wx.EXPAND | wx.ALL, 5)

        # --- Centroid Matching Parameters ---
        matching_box = wx.StaticBox(panel, label="Centroid Matching Parameters")
        matching_sizer = wx.StaticBoxSizer(matching_box, wx.VERTICAL)
        
        form_sizer = wx.FlexGridSizer(3, 2, 10, 10)
        form_sizer.AddGrowableCol(1, 1)
        
        self.centroid_matching_controls = {}
        
        # Base Target Tolerance with tooltip
        self.centroid_matching_controls['base_tolerance'] = wx.SpinCtrl(panel, value="750", min=1, max=5000)
        create_labeled_control_with_tooltip(
            panel, "Base Target Tolerance:", 
            self.centroid_matching_controls['base_tolerance'], 
            'base_tolerance', form_sizer
        )
        
        # Scale Factor Min with tooltip
        self.centroid_matching_controls['scale_min'] = wx.TextCtrl(panel, value="0.5")
        create_labeled_control_with_tooltip(
            panel, "Scale Factor Min:", 
            self.centroid_matching_controls['scale_min'], 
            'scale_min', form_sizer
        )
        
        # Scale Factor Max with tooltip
        self.centroid_matching_controls['scale_max'] = wx.TextCtrl(panel, value="1.0")
        create_labeled_control_with_tooltip(
            panel, "Scale Factor Max:", 
            self.centroid_matching_controls['scale_max'], 
            'scale_max', form_sizer
        )
        
        matching_sizer.Add(form_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(matching_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(main_sizer)
        return panel

    def create_clustering_panel(self):
        """Create the clustering parameters panel with comprehensive tooltips."""
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        instructions = wx.StaticText(panel,
            label="HDBSCAN clustering parameters for droplet classification.\n"
                  "Hover over parameter names for detailed explanations and tips.")
        sizer.Add(instructions, 0, wx.ALL, 10)
        
        form_sizer = wx.FlexGridSizer(6, 2, 10, 10)
        form_sizer.AddGrowableCol(1, 1)
        
        self.clustering_controls = {}
        
        # Min Cluster Size with tooltip
        self.clustering_controls['min_cluster_size'] = wx.SpinCtrl(panel, value="4", min=1, max=1000)
        create_labeled_control_with_tooltip(
            panel, "HDBSCAN Min Cluster Size:", 
            self.clustering_controls['min_cluster_size'], 
            'min_cluster_size', form_sizer
        )
        
        # Min Samples with tooltip
        self.clustering_controls['min_samples'] = wx.SpinCtrl(panel, value="70", min=1, max=1000)
        create_labeled_control_with_tooltip(
            panel, "HDBSCAN Min Samples:", 
            self.clustering_controls['min_samples'], 
            'min_samples', form_sizer
        )
        
        # Epsilon with tooltip
        self.clustering_controls['epsilon'] = wx.TextCtrl(panel, value="0.06")
        create_labeled_control_with_tooltip(
            panel, "HDBSCAN Epsilon:", 
            self.clustering_controls['epsilon'], 
            'epsilon', form_sizer
        )
        
        # Metric with tooltip
        self.clustering_controls['metric'] = wx.Choice(panel, choices=['euclidean', 'manhattan', 'chebyshev', 'minkowski'])
        create_labeled_control_with_tooltip(
            panel, "HDBSCAN Metric:", 
            self.clustering_controls['metric'], 
            'metric', form_sizer
        )
        
        # Selection Method with tooltip
        self.clustering_controls['selection_method'] = wx.Choice(panel, choices=['eom', 'leaf'])
        create_labeled_control_with_tooltip(
            panel, "HDBSCAN Selection Method:", 
            self.clustering_controls['selection_method'], 
            'selection_method', form_sizer
        )
        
        # Min Points with tooltip
        self.clustering_controls['min_points'] = wx.SpinCtrl(panel, value="50", min=1, max=10000)
        create_labeled_control_with_tooltip(
            panel, "Min Points for Clustering:", 
            self.clustering_controls['min_points'], 
            'min_points', form_sizer
        )
        
        sizer.Add(form_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(sizer)
        return panel
    
    def create_copy_numbers_panel(self):
            """Create the copy number settings panel with comprehensive tooltips."""
            panel = wx.Panel(self.notebook)
            sizer = wx.BoxSizer(wx.VERTICAL)
            
            # --- General Settings ---
            general_box = wx.StaticBox(panel, label="General & Aneuploidy Settings")
            general_sizer = wx.StaticBoxSizer(general_box, wx.VERTICAL)
            form_sizer = wx.FlexGridSizer(6, 2, 10, 10)
            form_sizer.AddGrowableCol(1, 1)
            
            self.copy_number_controls = {}

            # Min Usable Droplets with tooltip
            self.copy_number_controls['min_droplets'] = wx.SpinCtrl(panel, value="3000", min=100, max=50000)
            create_labeled_control_with_tooltip(
                panel, "Min Usable Droplets:", 
                self.copy_number_controls['min_droplets'], 
                'min_droplets', form_sizer
            )
            
            # Median Deviation Threshold with tooltip
            self.copy_number_controls['median_threshold'] = wx.TextCtrl(panel, value="0.15")
            create_labeled_control_with_tooltip(
                panel, "Median Deviation Threshold:", 
                self.copy_number_controls['median_threshold'], 
                'median_threshold', form_sizer
            )
            
            # Baseline Min Chromosomes with tooltip
            self.copy_number_controls['baseline_min'] = wx.SpinCtrl(panel, value="3", min=1, max=10)
            create_labeled_control_with_tooltip(
                panel, "Baseline Min Chromosomes:", 
                self.copy_number_controls['baseline_min'], 
                'baseline_min', form_sizer
            )

            # Tolerance Multiplier with tooltip
            self.copy_number_controls['tolerance_multiplier'] = wx.SpinCtrl(panel, value="3", min=1, max=10)
            create_labeled_control_with_tooltip(
                panel, "Tolerance Multiplier:", 
                self.copy_number_controls['tolerance_multiplier'], 
                'tolerance_multiplier', form_sizer
            )

            # Aneuploidy targets with tooltips
            self.copy_number_controls['aneuploidy_targets'] = {}
            self.copy_number_controls['aneuploidy_targets']['low'] = wx.TextCtrl(panel, value="0.75")
            create_labeled_control_with_tooltip(
                panel, "Aneuploidy Deletion Target:", 
                self.copy_number_controls['aneuploidy_targets']['low'], 
                'deletion_target', form_sizer
            )

            self.copy_number_controls['aneuploidy_targets']['high'] = wx.TextCtrl(panel, value="1.25")
            create_labeled_control_with_tooltip(
                panel, "Aneuploidy Duplication Target:", 
                self.copy_number_controls['aneuploidy_targets']['high'], 
                'duplication_target', form_sizer
            )

            general_sizer.Add(form_sizer, 0, wx.EXPAND | wx.ALL, 10)
            sizer.Add(general_sizer, 0, wx.EXPAND | wx.ALL, 5)

            # --- Grids for Chromosome-specific values ---
            grid_sizer = wx.BoxSizer(wx.HORIZONTAL)
            
            copy_num_box = wx.StaticBox(panel, label="Expected Copy Numbers")
            copy_num_box_sizer = wx.StaticBoxSizer(copy_num_box, wx.VERTICAL)
            self.copy_numbers_grid = wx.grid.Grid(panel)
            self.copy_numbers_grid.CreateGrid(10, 2)
            self.copy_numbers_grid.SetColLabelValue(0, "Chromosome")
            self.copy_numbers_grid.SetColLabelValue(1, "Expected Value")
            self.copy_numbers_grid.SetColSize(0, 150)
            self.copy_numbers_grid.SetColSize(1, 150)
            
            # Add tooltip to copy numbers grid
            add_tooltip(self.copy_numbers_grid, 'copy_numbers_grid')
            
            copy_num_box_sizer.Add(self.copy_numbers_grid, 1, wx.EXPAND | wx.ALL, 5)
            grid_sizer.Add(copy_num_box_sizer, 1, wx.EXPAND | wx.ALL, 5)

            std_dev_box = wx.StaticBox(panel, label="Expected Standard Deviation")
            std_dev_box_sizer = wx.StaticBoxSizer(std_dev_box, wx.VERTICAL)
            self.std_dev_grid = wx.grid.Grid(panel)
            self.std_dev_grid.CreateGrid(10, 2)
            self.std_dev_grid.SetColLabelValue(0, "Chromosome")
            self.std_dev_grid.SetColLabelValue(1, "Std. Dev.")
            self.std_dev_grid.SetColSize(0, 150)
            self.std_dev_grid.SetColSize(1, 150)
            
            # Add tooltip to std dev grid
            add_tooltip(self.std_dev_grid, 'std_dev_grid')
            
            std_dev_box_sizer.Add(self.std_dev_grid, 1, wx.EXPAND | wx.ALL, 5)
            grid_sizer.Add(std_dev_box_sizer, 1, wx.EXPAND | wx.ALL, 5)

            sizer.Add(grid_sizer, 1, wx.EXPAND | wx.ALL, 5)
            panel.SetSizer(sizer)
            return panel

    def create_visualization_panel(self):
        """Create the visualization settings panel with comprehensive tooltips."""
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.vis_controls = {}

        # --- Axis & Grid Settings ---
        axis_box = wx.StaticBox(panel, label="Axis & Grid Settings")
        axis_sizer = wx.StaticBoxSizer(axis_box, wx.VERTICAL)
        form1 = wx.FlexGridSizer(3, 4, 10, 10)

        # X-Axis Min with tooltip
        self.vis_controls['X_AXIS_MIN'] = wx.SpinCtrl(panel, min=0, max=10000, initial=0)
        create_labeled_control_with_tooltip(
            panel, "X-Axis Min:", 
            self.vis_controls['X_AXIS_MIN'], 
            'x_axis_min', form1
        )
        
        # X-Axis Max with tooltip
        self.vis_controls['X_AXIS_MAX'] = wx.SpinCtrl(panel, min=0, max=10000, initial=3000)
        create_labeled_control_with_tooltip(
            panel, "X-Axis Max:", 
            self.vis_controls['X_AXIS_MAX'], 
            'x_axis_max', form1
        )

        # Y-Axis Min with tooltip
        self.vis_controls['Y_AXIS_MIN'] = wx.SpinCtrl(panel, min=0, max=10000, initial=0)
        create_labeled_control_with_tooltip(
            panel, "Y-Axis Min:", 
            self.vis_controls['Y_AXIS_MIN'], 
            'y_axis_min', form1
        )

        # Y-Axis Max with tooltip
        self.vis_controls['Y_AXIS_MAX'] = wx.SpinCtrl(panel, min=0, max=10000, initial=5000)
        create_labeled_control_with_tooltip(
            panel, "Y-Axis Max:", 
            self.vis_controls['Y_AXIS_MAX'], 
            'y_axis_max', form1
        )

        # X-Grid Interval with tooltip
        self.vis_controls['X_GRID_INTERVAL'] = wx.SpinCtrl(panel, min=1, max=5000, initial=500)
        create_labeled_control_with_tooltip(
            panel, "X-Grid Interval:", 
            self.vis_controls['X_GRID_INTERVAL'], 
            'x_grid_interval', form1
        )
        
        # Y-Grid Interval with tooltip
        self.vis_controls['Y_GRID_INTERVAL'] = wx.SpinCtrl(panel, min=1, max=5000, initial=1000)
        create_labeled_control_with_tooltip(
            panel, "Y-Grid Interval:", 
            self.vis_controls['Y_GRID_INTERVAL'], 
            'y_grid_interval', form1
        )

        axis_sizer.Add(form1, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(axis_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # --- DPI Settings ---
        dpi_box = wx.StaticBox(panel, label="Plot DPI Settings")
        dpi_box_sizer = wx.StaticBoxSizer(dpi_box, wx.VERTICAL)
        form2 = wx.FlexGridSizer(2, 2, 10, 10)
        
        # Individual DPI with tooltip
        self.vis_controls['INDIVIDUAL_PLOT_DPI'] = wx.SpinCtrl(panel, min=75, max=600, initial=300)
        create_labeled_control_with_tooltip(
            panel, "Individual DPI:", 
            self.vis_controls['INDIVIDUAL_PLOT_DPI'], 
            'individual_dpi', form2
        )
        
        
        dpi_box_sizer.Add(form2, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(dpi_box_sizer, 0, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(sizer)
        return panel
    
    def _get_config_attr(self, key, default):
        """Safely get attribute from config class."""
        return getattr(self.config_cls, key, default)

    def load_parameters(self):
        """Load parameters from file or use config defaults."""
        if os.path.exists(PARAMETERS_FILE):
            try:
                with open(PARAMETERS_FILE, 'r') as f:
                    params = json.load(f)
                logger.debug(f"Loaded parameters from {PARAMETERS_FILE}")
                
                # Ensure all required parameters exist with defaults if missing
                required_defaults = self._get_factory_defaults()
                for key, default_value in required_defaults.items():
                    if key not in params:
                        params[key] = default_value
                        logger.debug(f"Added missing parameter {key} with default: {default_value}")
                
                return params
            except Exception as e:
                logger.warning(f"Error loading parameters file: {e}")
        
        # Return config defaults
        return self._get_factory_defaults()
    
    def _get_factory_defaults(self):
        """Return hard-coded factory defaults (matches config.py)."""
        return {
            'EXPECTED_CENTROIDS': {
                "Negative": [1000, 900],
                "Chrom1": [1000, 2300],
                "Chrom2": [1800, 2200],
                "Chrom3": [2400, 1750],
                "Chrom4": [3100, 1300],
                "Chrom5": [3500, 900]
            },
            'BASE_TARGET_TOLERANCE': 750,
            'SCALE_FACTOR_MIN': 0.5,
            'SCALE_FACTOR_MAX': 1.0,
            'HDBSCAN_MIN_CLUSTER_SIZE': 4,
            'HDBSCAN_MIN_SAMPLES': 70,
            'HDBSCAN_EPSILON': 0.06,
            'HDBSCAN_METRIC': 'euclidean',
            'HDBSCAN_CLUSTER_SELECTION_METHOD': 'eom',
            'MIN_POINTS_FOR_CLUSTERING': 50,
            'MIN_USABLE_DROPLETS': 3000,
            'COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD': 0.15,
            'COPY_NUMBER_BASELINE_MIN_CHROMS': 3,
            'EXPECTED_COPY_NUMBERS': {
                "Chrom1": 0.9716,
                "Chrom2": 1.0052,
                "Chrom3": 1.0278,
                "Chrom4": 0.9912,
                "Chrom5": 1.0035
            },
            'TOLERANCE_MULTIPLIER': 3,
            'ANEUPLOIDY_TARGETS': {"low": 0.75, "high": 1.25},
            'EXPECTED_STANDARD_DEVIATION': {
                "Chrom1": 0.0312,
                "Chrom2": 0.0241,
                "Chrom3": 0.0290,
                "Chrom4": 0.0242,
                "Chrom5": 0.0230
            },
            'X_AXIS_MIN': 0,
            'X_AXIS_MAX': 3000,
            'Y_AXIS_MIN': 0,
            'Y_AXIS_MAX': 5000,
            'X_GRID_INTERVAL': 500,
            'Y_GRID_INTERVAL': 1000,
            'INDIVIDUAL_PLOT_DPI': 300,
        }

    def _get_config_snapshot(self):
        """Get current parameters from the live config class."""
        defaults = self._get_factory_defaults()
        for key in defaults:
            config_value = self._get_config_attr(key, defaults[key])
            defaults[key] = config_value
        return defaults

    def _get_config_file_snapshot(self):
        """Get parameters from the original config.py file on disk."""
        # Use the factory defaults as these represent the original config.py values
        # This is simpler and more reliable than trying to re-import the module
        return self._get_factory_defaults()
    
    def _populate_grid(self, grid, data):
        """Populate a grid with data dictionary."""
        grid.ClearGrid()
        row = 0
        for key, value in data.items():
            if row < grid.GetNumberRows():
                grid.SetCellValue(row, 0, str(key))
                grid.SetCellValue(row, 1, str(value))
                row += 1

    def load_values(self):
        """Load current parameter values into the GUI."""
        p = self.parameters
        
        # Load centroids
        centroids = p.get('EXPECTED_CENTROIDS', {})
        self.centroids_grid.ClearGrid()
        row = 0
        for target, coords in centroids.items():
            if row < self.centroids_grid.GetNumberRows() and len(coords) >= 2:
                self.centroids_grid.SetCellValue(row, 0, target)
                self.centroids_grid.SetCellValue(row, 1, str(coords[0]))
                self.centroids_grid.SetCellValue(row, 2, str(coords[1]))
                row += 1
        
        # Load centroid matching
        self.centroid_matching_controls['base_tolerance'].SetValue(p.get('BASE_TARGET_TOLERANCE', 750))
        self.centroid_matching_controls['scale_min'].SetValue(str(p.get('SCALE_FACTOR_MIN', 0.5)))
        self.centroid_matching_controls['scale_max'].SetValue(str(p.get('SCALE_FACTOR_MAX', 1.0)))

        # Load clustering
        self.clustering_controls['min_cluster_size'].SetValue(p.get('HDBSCAN_MIN_CLUSTER_SIZE', 4))
        self.clustering_controls['min_samples'].SetValue(p.get('HDBSCAN_MIN_SAMPLES', 70))
        self.clustering_controls['epsilon'].SetValue(str(p.get('HDBSCAN_EPSILON', 0.06)))
        self.clustering_controls['metric'].SetStringSelection(p.get('HDBSCAN_METRIC', 'euclidean'))
        self.clustering_controls['selection_method'].SetStringSelection(p.get('HDBSCAN_CLUSTER_SELECTION_METHOD', 'eom'))
        self.clustering_controls['min_points'].SetValue(p.get('MIN_POINTS_FOR_CLUSTERING', 50))
        
        # Load copy number settings
        self.copy_number_controls['min_droplets'].SetValue(p.get('MIN_USABLE_DROPLETS', 3000))
        self.copy_number_controls['median_threshold'].SetValue(str(p.get('COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD', 0.15)))
        self.copy_number_controls['baseline_min'].SetValue(p.get('COPY_NUMBER_BASELINE_MIN_CHROMS', 3))
        self.copy_number_controls['tolerance_multiplier'].SetValue(p.get('TOLERANCE_MULTIPLIER', 3))
        
        # Load aneuploidy targets
        aneuploidy_targets = p.get('ANEUPLOIDY_TARGETS', {})
        self.copy_number_controls['aneuploidy_targets']['low'].SetValue(str(aneuploidy_targets.get('low', 0.75)))
        self.copy_number_controls['aneuploidy_targets']['high'].SetValue(str(aneuploidy_targets.get('high', 1.25)))
        
        # Load grids with debug output
        expected_copy_nums = p.get('EXPECTED_COPY_NUMBERS', {})
        expected_std_devs = p.get('EXPECTED_STANDARD_DEVIATION', {})
        
        logger.debug(f"Loading copy numbers: {expected_copy_nums}")
        logger.debug(f"Loading std deviations: {expected_std_devs}")
        
        self._populate_grid(self.copy_numbers_grid, expected_copy_nums)
        self._populate_grid(self.std_dev_grid, expected_std_devs)

        # Load visualization settings
        for key, control in self.vis_controls.items():
            value = p.get(key)
            if value is not None:
                try:
                    control.SetValue(value)
                except:
                    logger.warning(f"Could not set value '{value}' for control '{key}'")

    def _collect_grid(self, grid):
        """Collect data from a grid into a dictionary."""
        data = {}
        for row in range(grid.GetNumberRows()):
            key = grid.GetCellValue(row, 0).strip()
            value_str = grid.GetCellValue(row, 1).strip()
            if key and value_str:
                try:
                    data[key] = float(value_str)
                except ValueError:
                    wx.MessageBox(f"Invalid numeric value for '{key}': '{value_str}'", "Error", wx.OK | wx.ICON_ERROR)
                    return None
        return data

    def collect_parameters(self):
        """Collect parameters from the GUI."""
        params = {}
        
        try:
            # Collect centroids
            centroids = {}
            for row in range(self.centroids_grid.GetNumberRows()):
                target = self.centroids_grid.GetCellValue(row, 0).strip()
                fam_str = self.centroids_grid.GetCellValue(row, 1).strip()
                hex_str = self.centroids_grid.GetCellValue(row, 2).strip()
                if target and fam_str and hex_str:
                    centroids[target] = [float(fam_str), float(hex_str)]
            params['EXPECTED_CENTROIDS'] = centroids
            
            # Collect centroid matching
            params['BASE_TARGET_TOLERANCE'] = self.centroid_matching_controls['base_tolerance'].GetValue()
            params['SCALE_FACTOR_MIN'] = float(self.centroid_matching_controls['scale_min'].GetValue())
            params['SCALE_FACTOR_MAX'] = float(self.centroid_matching_controls['scale_max'].GetValue())
            
        except ValueError as e:
            wx.MessageBox(f"Invalid Centroid value: {e}", "Error", wx.OK | wx.ICON_ERROR)
            return None

        try:
            # Collect clustering
            params['HDBSCAN_MIN_CLUSTER_SIZE'] = self.clustering_controls['min_cluster_size'].GetValue()
            params['HDBSCAN_MIN_SAMPLES'] = self.clustering_controls['min_samples'].GetValue()
            params['HDBSCAN_EPSILON'] = float(self.clustering_controls['epsilon'].GetValue())
            params['HDBSCAN_METRIC'] = self.clustering_controls['metric'].GetStringSelection()
            params['HDBSCAN_CLUSTER_SELECTION_METHOD'] = self.clustering_controls['selection_method'].GetStringSelection()
            params['MIN_POINTS_FOR_CLUSTERING'] = self.clustering_controls['min_points'].GetValue()
            
        except ValueError as e:
            wx.MessageBox(f"Invalid Clustering value: {e}", "Error", wx.OK | wx.ICON_ERROR)
            return None

        try:
            # Collect copy number settings
            params['MIN_USABLE_DROPLETS'] = self.copy_number_controls['min_droplets'].GetValue()
            params['COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD'] = float(self.copy_number_controls['median_threshold'].GetValue())
            params['COPY_NUMBER_BASELINE_MIN_CHROMS'] = self.copy_number_controls['baseline_min'].GetValue()
            params['TOLERANCE_MULTIPLIER'] = self.copy_number_controls['tolerance_multiplier'].GetValue()
            params['ANEUPLOIDY_TARGETS'] = {
                "low": float(self.copy_number_controls['aneuploidy_targets']['low'].GetValue()),
                "high": float(self.copy_number_controls['aneuploidy_targets']['high'].GetValue())
            }
            
            # Collect grids
            params['EXPECTED_COPY_NUMBERS'] = self._collect_grid(self.copy_numbers_grid)
            params['EXPECTED_STANDARD_DEVIATION'] = self._collect_grid(self.std_dev_grid)
            if params['EXPECTED_COPY_NUMBERS'] is None or params['EXPECTED_STANDARD_DEVIATION'] is None: 
                return None
                
        except ValueError as e:
            wx.MessageBox(f"Invalid Copy Number value: {e}", "Error", wx.OK | wx.ICON_ERROR)
            return None

        # Collect visualization settings
        for key, control in self.vis_controls.items():
            params[key] = control.GetValue()
        
        return params
    
    def on_load_from_config(self, event):
        """Reset values to what is defined in config.py on disk."""
        try:
            # Get factory defaults (original config.py values)
            self.parameters = self._get_config_file_snapshot()

            # Reload values into the GUI
            self.load_values()

            # Force UI refresh so changes are visible immediately
            self.Layout()
            self.centroids_grid.ForceRefresh()
            self.copy_numbers_grid.ForceRefresh()
            self.std_dev_grid.ForceRefresh()
            self.Refresh()

            wx.MessageBox("Parameters reset to default configuration values", "Info", wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            logger.error(f"Reset to Config failed: {e}", exc_info=True)
            wx.MessageBox(f"Reset to Config failed: {e}", "Error", wx.OK | wx.ICON_ERROR)

    def on_save(self, event):
        """Save parameters and close."""
        params = self.collect_parameters()
        if params is not None:
            self.parameters = params
            if self.save_parameters():
                self.EndModal(wx.ID_OK)
    
    def on_cancel(self, event):
        """Cancel without saving."""
        self.EndModal(wx.ID_CANCEL)
    
    def save_parameters(self):
        """Save parameters to file."""
        try:
            os.makedirs(USER_SETTINGS_DIR, exist_ok=True)
            with open(PARAMETERS_FILE, 'w') as f:
                json.dump(self.parameters, f, indent=4)
            logger.info(f"Parameters saved to {PARAMETERS_FILE}")
            wx.MessageBox("Parameters saved successfully!", "Success", wx.OK | wx.ICON_INFORMATION)
            return True
        except Exception as e:
            logger.error(f"Error saving parameters: {e}")
            wx.MessageBox(f"Error saving parameters: {e}", "Error", wx.OK | wx.ICON_ERROR)
            return False


def open_parameter_editor(config_cls):
    """
    Open the parameter editor GUI.
    
    Args:
        config_cls: The Config class to edit parameters for
        
    Returns:
        True if parameters were saved, False if cancelled
        
    Raises:
        ConfigError: If GUI cannot be opened
    """
    logger.debug("Opening parameter editor GUI")
    
    try:
        if not HAS_WX:
            raise ImportError("wxPython not available")
        
        app = None
        if not wx.GetApp():
            app = wx.App(False)
        
        with _silence_stderr():
            dialog = ParameterEditorFrame(config_cls)
            result = dialog.ShowModal()
            
            success = result == wx.ID_OK
            
            if success:
                logger.info("Parameters saved successfully")
                apply_parameters_to_config(config_cls)
            else:
                logger.debug("Parameter editing cancelled")
            
            dialog.Destroy()
            
            if app:
                app.Destroy()
            
            return success
                
    except ImportError:
        logger.error("wxPython not available for GUI parameter editor")
        return console_parameter_editor(config_cls)
    except Exception as e:
        error_msg = f"Error opening parameter editor: {str(e)}"
        logger.error(error_msg)
        logger.debug(f"Error details: {str(e)}", exc_info=True)
        raise ConfigError(error_msg) from e


def console_parameter_editor(config_cls):
    """
    Console-based parameter editor fallback.
    
    Args:
        config_cls: The Config class to edit parameters for
        
    Returns:
        True if parameters were saved, False if cancelled
    """
    print("\n" + "="*60)
    print("ddQuint Parameter Editor (Console Mode)")
    print("="*60)
    print("wxPython not available - using console input")
    print("Note: For a better experience, install wxPython: pip install wxpython")
    print()
    
    if os.path.exists(PARAMETERS_FILE):
        try:
            with open(PARAMETERS_FILE, 'r') as f:
                params = json.load(f)
        except:
            params = {}
    else:
        params = {}
    
    print("1. Expected Centroids:")
    centroids = params.get('EXPECTED_CENTROIDS', getattr(config_cls, 'EXPECTED_CENTROIDS', {}))
    
    for target, coords in centroids.items():
        print(f"   {target}: [{coords[0]}, {coords[1]}]")
    
    if input("\nModify centroids? (y/n): ").lower() == 'y':
        print("Enter centroids (format: TargetName FAM_Fluorescence HEX_Fluorescence), empty line to finish:")
        new_centroids = {}
        while True:
            line = input("> ").strip()
            if not line:
                break
            parts = line.split()
            if len(parts) >= 3:
                try:
                    target = parts[0]
                    fam = float(parts[1])
                    hex_val = float(parts[2])
                    new_centroids[target] = [fam, hex_val]
                    print(f"   Added: {target} = [{fam}, {hex_val}]")
                except ValueError:
                    print("   Invalid format, try again")
        
        if new_centroids:
            params['EXPECTED_CENTROIDS'] = new_centroids
    
    print(f"\n2. Clustering Parameters:")
    print(f"   Min Cluster Size: {params.get('HDBSCAN_MIN_CLUSTER_SIZE', getattr(config_cls, 'HDBSCAN_MIN_CLUSTER_SIZE', 4))}")
    print(f"   Min Samples: {params.get('HDBSCAN_MIN_SAMPLES', getattr(config_cls, 'HDBSCAN_MIN_SAMPLES', 70))}")
    print(f"   Epsilon: {params.get('HDBSCAN_EPSILON', getattr(config_cls, 'HDBSCAN_EPSILON', 0.06))}")
    
    if input("\nModify clustering parameters? (y/n): ").lower() == 'y':
        try:
            min_cluster = input(f"Min Cluster Size [{params.get('HDBSCAN_MIN_CLUSTER_SIZE', 4)}]: ").strip()
            if min_cluster:
                params['HDBSCAN_MIN_CLUSTER_SIZE'] = int(min_cluster)
            
            min_samples = input(f"Min Samples [{params.get('HDBSCAN_MIN_SAMPLES', 70)}]: ").strip()
            if min_samples:
                params['HDBSCAN_MIN_SAMPLES'] = int(min_samples)
            
            epsilon = input(f"Epsilon [{params.get('HDBSCAN_EPSILON', 0.06)}]: ").strip()
            if epsilon:
                params['HDBSCAN_EPSILON'] = float(epsilon)
        except ValueError:
            print("Invalid input, keeping current values")
    
    if input("\nSave parameters? (y/n): ").lower() == 'y':
        try:
            os.makedirs(USER_SETTINGS_DIR, exist_ok=True)
            with open(PARAMETERS_FILE, 'w') as f:
                json.dump(params, f, indent=2)
            print(f"Parameters saved to {PARAMETERS_FILE}")
            apply_parameters_to_config(config_cls)
            return True
        except Exception as e:
            print(f"Error saving parameters: {e}")
    
    return False


def apply_parameters_to_config(config_cls):
    """
    Apply saved parameters to the config class.
    
    Args:
        config_cls: The Config class to update
        
    Notes:
        Parameter priority order:
        1. User parameters file (highest - trumps everything)
        2. Config file specified with --config 
        3. Default config.py values (lowest)
    """
    if not os.path.exists(PARAMETERS_FILE):
        return
    
    try:
        with open(PARAMETERS_FILE, 'r') as f:
            params = json.load(f)
        
        for key, value in params.items():
            if hasattr(config_cls, key):
                old_value = getattr(config_cls, key)
                setattr(config_cls, key, value)
                logger.debug(f"Applied parameter: {key} = {value} (was: {old_value})")
            else:
                logger.warning(f"Unknown parameter key: {key}")
        
        logger.debug(f"Applied parameters from {PARAMETERS_FILE} (highest priority)")
        
    except Exception as e:
        logger.error(f"Error applying parameters: {e}")
        raise ConfigError(f"Failed to apply parameters: {e}") from e


def load_parameters_if_exist(config_cls):
    """
    Load parameters file if it exists and apply to config.
    
    This function is called during config initialization to automatically
    load user parameters if they exist. User parameters have the highest
    priority and will override any config file settings.
    
    Args:
        config_cls: The Config class to update
        
    Returns:
        True if parameters were loaded, False otherwise
    """
    if os.path.exists(PARAMETERS_FILE):
        try:
            apply_parameters_to_config(config_cls)
            logger.debug("Automatically loaded user parameters (highest priority)")
            return True
        except Exception as e:
            logger.warning(f"Failed to load user parameters: {e}")
    
    return False


def get_parameters_file_path():
    """
    Get the path to the parameters file.
    
    Returns:
        Path to the parameters file
    """
    return PARAMETERS_FILE


def parameters_exist():
    """
    Check if parameters file exists.
    
    Returns:
        True if parameters file exists
    """
    return os.path.exists(PARAMETERS_FILE)


def delete_parameters():
    """
    Delete the parameters file.
    
    Returns:
        True if file was deleted successfully
    """
    try:
        if os.path.exists(PARAMETERS_FILE):
            os.remove(PARAMETERS_FILE)
            logger.info("Parameters file deleted")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting parameters file: {e}")
        return False