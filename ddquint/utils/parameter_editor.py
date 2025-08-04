#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parameter editor GUI for ddQuint with user-friendly interface.

Provides a graphical interface for editing frequently modified parameters
like EXPECTED_CENTROIDS, clustering parameters, copy number settings,
and visualization options. Stores settings in a separate parameters
file for easy management.
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

# Optional import for wxPython GUI
try:
    import wx
    import wx.grid
    import wx.lib.colourselect as csel
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
        load_btn = wx.Button(panel, label="Load from Config")
        load_btn.Bind(wx.EVT_BUTTON, self.on_load_from_config)
        button_sizer.Add(load_btn, 0, wx.ALL, 5)
        
        reset_btn = wx.Button(panel, label="Reset to Defaults")
        reset_btn.Bind(wx.EVT_BUTTON, self.on_reset_defaults)
        button_sizer.Add(reset_btn, 0, wx.ALL, 5)
        
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
                  "Format: [FAM fluorescence, HEX fluorescence]")
        centroids_sizer.Add(instructions, 0, wx.ALL, 5)
        
        self.centroids_grid = wx.grid.Grid(panel)
        self.centroids_grid.CreateGrid(10, 3)
        self.centroids_grid.SetColLabelValue(0, "Target Name")
        self.centroids_grid.SetColLabelValue(1, "FAM Fluorescence")
        self.centroids_grid.SetColLabelValue(2, "HEX Fluorescence")
        self.centroids_grid.SetColSize(0, 150)
        self.centroids_grid.SetColSize(1, 140)
        self.centroids_grid.SetColSize(2, 140)
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
        
        form_sizer.Add(wx.StaticText(panel, label="Base Target Tolerance:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.centroid_matching_controls['base_tolerance'] = wx.SpinCtrl(panel, value="750", min=1, max=5000)
        form_sizer.Add(self.centroid_matching_controls['base_tolerance'], 1, wx.EXPAND)
        
        form_sizer.Add(wx.StaticText(panel, label="Scale Factor Min:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.centroid_matching_controls['scale_min'] = wx.TextCtrl(panel, value="0.5")
        form_sizer.Add(self.centroid_matching_controls['scale_min'], 1, wx.EXPAND)
        
        form_sizer.Add(wx.StaticText(panel, label="Scale Factor Max:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.centroid_matching_controls['scale_max'] = wx.TextCtrl(panel, value="1.0")
        form_sizer.Add(self.centroid_matching_controls['scale_max'], 1, wx.EXPAND)
        
        matching_sizer.Add(form_sizer, 1, wx.EXPAND | wx.ALL, 10)
        main_sizer.Add(matching_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(main_sizer)
        return panel

    def create_clustering_panel(self):
        """Create the clustering parameters panel."""
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        instructions = wx.StaticText(panel,
            label="HDBSCAN clustering parameters for droplet classification.\n"
                  "Adjust these values based on your data density and cluster characteristics.")
        sizer.Add(instructions, 0, wx.ALL, 10)
        
        form_sizer = wx.FlexGridSizer(6, 2, 10, 10)
        form_sizer.AddGrowableCol(1, 1)
        
        self.clustering_controls = {}
        
        form_sizer.Add(wx.StaticText(panel, label="HDBSCAN Min Cluster Size:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.clustering_controls['min_cluster_size'] = wx.SpinCtrl(panel, value="4", min=1, max=1000)
        form_sizer.Add(self.clustering_controls['min_cluster_size'], 1, wx.EXPAND)
        
        form_sizer.Add(wx.StaticText(panel, label="HDBSCAN Min Samples:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.clustering_controls['min_samples'] = wx.SpinCtrl(panel, value="70", min=1, max=1000)
        form_sizer.Add(self.clustering_controls['min_samples'], 1, wx.EXPAND)
        
        form_sizer.Add(wx.StaticText(panel, label="HDBSCAN Epsilon:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.clustering_controls['epsilon'] = wx.TextCtrl(panel, value="0.06")
        form_sizer.Add(self.clustering_controls['epsilon'], 1, wx.EXPAND)
        
        form_sizer.Add(wx.StaticText(panel, label="HDBSCAN Metric:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.clustering_controls['metric'] = wx.Choice(panel, choices=['euclidean', 'manhattan', 'chebyshev', 'minkowski'])
        form_sizer.Add(self.clustering_controls['metric'], 1, wx.EXPAND)
        
        form_sizer.Add(wx.StaticText(panel, label="HDBSCAN Selection Method:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.clustering_controls['selection_method'] = wx.Choice(panel, choices=['eom', 'leaf'])
        form_sizer.Add(self.clustering_controls['selection_method'], 1, wx.EXPAND)
        
        form_sizer.Add(wx.StaticText(panel, label="Min Points for Clustering:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.clustering_controls['min_points'] = wx.SpinCtrl(panel, value="50", min=1, max=10000)
        form_sizer.Add(self.clustering_controls['min_points'], 1, wx.EXPAND)
        
        sizer.Add(form_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(sizer)
        return panel
    
    def create_copy_numbers_panel(self):
        """Create the copy number settings panel."""
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # --- General Settings ---
        general_box = wx.StaticBox(panel, label="General & Aneuploidy Settings")
        general_sizer = wx.StaticBoxSizer(general_box, wx.VERTICAL)
        form_sizer = wx.FlexGridSizer(6, 2, 10, 10)
        form_sizer.AddGrowableCol(1, 1)
        
        self.copy_number_controls = {}

        form_sizer.Add(wx.StaticText(panel, label="Min Usable Droplets:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.copy_number_controls['min_droplets'] = wx.SpinCtrl(panel, value="3000", min=100, max=50000)
        form_sizer.Add(self.copy_number_controls['min_droplets'], 1, wx.EXPAND)
        
        form_sizer.Add(wx.StaticText(panel, label="Median Deviation Threshold:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.copy_number_controls['median_threshold'] = wx.TextCtrl(panel, value="0.15")
        form_sizer.Add(self.copy_number_controls['median_threshold'], 1, wx.EXPAND)
        
        form_sizer.Add(wx.StaticText(panel, label="Baseline Min Chromosomes:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.copy_number_controls['baseline_min'] = wx.SpinCtrl(panel, value="3", min=1, max=10)
        form_sizer.Add(self.copy_number_controls['baseline_min'], 1, wx.EXPAND)

        form_sizer.Add(wx.StaticText(panel, label="Tolerance Multiplier:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.copy_number_controls['tolerance_multiplier'] = wx.SpinCtrl(panel, value="3", min=1, max=10)
        form_sizer.Add(self.copy_number_controls['tolerance_multiplier'], 1, wx.EXPAND)

        self.copy_number_controls['aneuploidy_targets'] = {}
        form_sizer.Add(wx.StaticText(panel, label="Aneuploidy Deletion Target:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.copy_number_controls['aneuploidy_targets']['low'] = wx.TextCtrl(panel, value="0.75")
        form_sizer.Add(self.copy_number_controls['aneuploidy_targets']['low'], 1, wx.EXPAND)

        form_sizer.Add(wx.StaticText(panel, label="Aneuploidy Duplication Target:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.copy_number_controls['aneuploidy_targets']['high'] = wx.TextCtrl(panel, value="1.25")
        form_sizer.Add(self.copy_number_controls['aneuploidy_targets']['high'], 1, wx.EXPAND)

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
        std_dev_box_sizer.Add(self.std_dev_grid, 1, wx.EXPAND | wx.ALL, 5)
        grid_sizer.Add(std_dev_box_sizer, 1, wx.EXPAND | wx.ALL, 5)

        sizer.Add(grid_sizer, 1, wx.EXPAND | wx.ALL, 5)
        panel.SetSizer(sizer)
        return panel

    def create_visualization_panel(self):
        """Create the visualization settings panel."""
        panel = wx.Panel(self.notebook)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.vis_controls = {}

        # --- Axis & Grid Settings ---
        axis_box = wx.StaticBox(panel, label="Axis & Grid Settings")
        axis_sizer = wx.StaticBoxSizer(axis_box, wx.VERTICAL)
        form1 = wx.FlexGridSizer(3, 4, 10, 10)

        form1.Add(wx.StaticText(panel, label="X-Axis Min:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.vis_controls['X_AXIS_MIN'] = wx.SpinCtrl(panel, min=0, max=10000, initial=0)
        form1.Add(self.vis_controls['X_AXIS_MIN'], 1, wx.EXPAND)
        
        form1.Add(wx.StaticText(panel, label="X-Axis Max:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.vis_controls['X_AXIS_MAX'] = wx.SpinCtrl(panel, min=0, max=10000, initial=3000)
        form1.Add(self.vis_controls['X_AXIS_MAX'], 1, wx.EXPAND)

        form1.Add(wx.StaticText(panel, label="Y-Axis Min:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.vis_controls['Y_AXIS_MIN'] = wx.SpinCtrl(panel, min=0, max=10000, initial=0)
        form1.Add(self.vis_controls['Y_AXIS_MIN'], 1, wx.EXPAND)

        form1.Add(wx.StaticText(panel, label="Y-Axis Max:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.vis_controls['Y_AXIS_MAX'] = wx.SpinCtrl(panel, min=0, max=10000, initial=5000)
        form1.Add(self.vis_controls['Y_AXIS_MAX'], 1, wx.EXPAND)

        form1.Add(wx.StaticText(panel, label="X-Grid Interval:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.vis_controls['X_GRID_INTERVAL'] = wx.SpinCtrl(panel, min=1, max=5000, initial=500)
        form1.Add(self.vis_controls['X_GRID_INTERVAL'], 1, wx.EXPAND)
        
        form1.Add(wx.StaticText(panel, label="Y-Grid Interval:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.vis_controls['Y_GRID_INTERVAL'] = wx.SpinCtrl(panel, min=1, max=5000, initial=1000)
        form1.Add(self.vis_controls['Y_GRID_INTERVAL'], 1, wx.EXPAND)

        axis_sizer.Add(form1, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(axis_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # --- DPI & Colors ---
        other_sizer = wx.BoxSizer(wx.HORIZONTAL)

        dpi_box = wx.StaticBox(panel, label="Plot DPI Settings")
        dpi_box_sizer = wx.StaticBoxSizer(dpi_box, wx.VERTICAL)
        form2 = wx.FlexGridSizer(2, 2, 10, 10)
        form2.Add(wx.StaticText(panel, label="Individual DPI:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.vis_controls['INDIVIDUAL_PLOT_DPI'] = wx.SpinCtrl(panel, min=75, max=600, initial=300)
        form2.Add(self.vis_controls['INDIVIDUAL_PLOT_DPI'], 1, wx.EXPAND)
        form2.Add(wx.StaticText(panel, label="Composite DPI:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.vis_controls['COMPOSITE_PLOT_DPI'] = wx.SpinCtrl(panel, min=75, max=600, initial=200)
        form2.Add(self.vis_controls['COMPOSITE_PLOT_DPI'], 1, wx.EXPAND)
        dpi_box_sizer.Add(form2, 1, wx.EXPAND | wx.ALL, 10)
        other_sizer.Add(dpi_box_sizer, 1, wx.EXPAND | wx.ALL, 5)

        color_box = wx.StaticBox(panel, label="Highlight Colors")
        color_box_sizer = wx.StaticBoxSizer(color_box, wx.VERTICAL)
        form3 = wx.FlexGridSizer(2, 2, 10, 10)
        form3.Add(wx.StaticText(panel, label="Aneuploidy Fill:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.vis_controls['ANEUPLOIDY_FILL_COLOR'] = csel.ColourSelect(panel, colour="#E6B8E6")
        form3.Add(self.vis_controls['ANEUPLOIDY_FILL_COLOR'], 1, wx.EXPAND)
        form3.Add(wx.StaticText(panel, label="Buffer Zone Fill:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.vis_controls['BUFFER_ZONE_FILL_COLOR'] = csel.ColourSelect(panel, colour="#B0B0B0")
        form3.Add(self.vis_controls['BUFFER_ZONE_FILL_COLOR'], 1, wx.EXPAND)
        color_box_sizer.Add(form3, 1, wx.EXPAND | wx.ALL, 10)
        other_sizer.Add(color_box_sizer, 1, wx.EXPAND | wx.ALL, 5)

        sizer.Add(other_sizer, 0, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(sizer)
        return panel
    
    def _get_config_attr(self, key, default):
        return getattr(self.config_cls, key, default)

    def load_parameters(self):
        """Load parameters from file or use config defaults."""
        if os.path.exists(PARAMETERS_FILE):
            try:
                with open(PARAMETERS_FILE, 'r') as f:
                    params = json.load(f)
                logger.debug(f"Loaded parameters from {PARAMETERS_FILE}")
                return params
            except Exception as e:
                logger.warning(f"Error loading parameters file: {e}")
        
        # Return config defaults
        return {
            'EXPECTED_CENTROIDS': self._get_config_attr('EXPECTED_CENTROIDS', {}),
            'BASE_TARGET_TOLERANCE': self._get_config_attr('BASE_TARGET_TOLERANCE', 750),
            'SCALE_FACTOR_MIN': self._get_config_attr('SCALE_FACTOR_MIN', 0.5),
            'SCALE_FACTOR_MAX': self._get_config_attr('SCALE_FACTOR_MAX', 1.0),
            'HDBSCAN_MIN_CLUSTER_SIZE': self._get_config_attr('HDBSCAN_MIN_CLUSTER_SIZE', 4),
            'HDBSCAN_MIN_SAMPLES': self._get_config_attr('HDBSCAN_MIN_SAMPLES', 70),
            'HDBSCAN_EPSILON': self._get_config_attr('HDBSCAN_EPSILON', 0.06),
            'HDBSCAN_METRIC': self._get_config_attr('HDBSCAN_METRIC', 'euclidean'),
            'HDBSCAN_CLUSTER_SELECTION_METHOD': self._get_config_attr('HDBSCAN_CLUSTER_SELECTION_METHOD', 'eom'),
            'MIN_POINTS_FOR_CLUSTERING': self._get_config_attr('MIN_POINTS_FOR_CLUSTERING', 50),
            'MIN_USABLE_DROPLETS': self._get_config_attr('MIN_USABLE_DROPLETS', 3000),
            'COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD': self._get_config_attr('COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD', 0.15),
            'COPY_NUMBER_BASELINE_MIN_CHROMS': self._get_config_attr('COPY_NUMBER_BASELINE_MIN_CHROMS', 3),
            'EXPECTED_COPY_NUMBERS': self._get_config_attr('EXPECTED_COPY_NUMBERS', {}),
            'TOLERANCE_MULTIPLIER': self._get_config_attr('TOLERANCE_MULTIPLIER', 3),
            'ANEUPLOIDY_TARGETS': self._get_config_attr('ANEUPLOIDY_TARGETS', {"low": 0.75, "high": 1.25}),
            'EXPECTED_STANDARD_DEVIATION': self._get_config_attr('EXPECTED_STANDARD_DEVIATION', {}),
            'X_AXIS_MIN': self._get_config_attr('X_AXIS_MIN', 0),
            'X_AXIS_MAX': self._get_config_attr('X_AXIS_MAX', 3000),
            'Y_AXIS_MIN': self._get_config_attr('Y_AXIS_MIN', 0),
            'Y_AXIS_MAX': self._get_config_attr('Y_AXIS_MAX', 5000),
            'X_GRID_INTERVAL': self._get_config_attr('X_GRID_INTERVAL', 500),
            'Y_GRID_INTERVAL': self._get_config_attr('Y_GRID_INTERVAL', 1000),
            'INDIVIDUAL_PLOT_DPI': self._get_config_attr('INDIVIDUAL_PLOT_DPI', 300),
            'COMPOSITE_PLOT_DPI': self._get_config_attr('COMPOSITE_PLOT_DPI', 200),
            'ANEUPLOIDY_FILL_COLOR': self._get_config_attr('ANEUPLOIDY_FILL_COLOR', "#E6B8E6"),
            'BUFFER_ZONE_FILL_COLOR': self._get_config_attr('BUFFER_ZONE_FILL_COLOR', "#B0B0B0"),
        }
    
    def _populate_grid(self, grid, data):
        row = 0
        for key, value in data.items():
            if row < grid.GetNumberRows():
                grid.SetCellValue(row, 0, str(key))
                grid.SetCellValue(row, 1, str(value))
                row += 1

    def load_values(self):
        """Load current parameter values into the GUI."""
        p = self.parameters
        
        centroids = p.get('EXPECTED_CENTROIDS', {})
        row = 0
        for target, coords in centroids.items():
            if row < self.centroids_grid.GetNumberRows():
                self.centroids_grid.SetCellValue(row, 0, target)
                self.centroids_grid.SetCellValue(row, 1, str(coords[0]))
                self.centroids_grid.SetCellValue(row, 2, str(coords[1]))
                row += 1
        self.centroid_matching_controls['base_tolerance'].SetValue(p.get('BASE_TARGET_TOLERANCE', 750))
        self.centroid_matching_controls['scale_min'].SetValue(str(p.get('SCALE_FACTOR_MIN', 0.5)))
        self.centroid_matching_controls['scale_max'].SetValue(str(p.get('SCALE_FACTOR_MAX', 1.0)))

        self.clustering_controls['min_cluster_size'].SetValue(p.get('HDBSCAN_MIN_CLUSTER_SIZE', 4))
        self.clustering_controls['min_samples'].SetValue(p.get('HDBSCAN_MIN_SAMPLES', 70))
        self.clustering_controls['epsilon'].SetValue(str(p.get('HDBSCAN_EPSILON', 0.06)))
        self.clustering_controls['metric'].SetStringSelection(p.get('HDBSCAN_METRIC', 'euclidean'))
        self.clustering_controls['selection_method'].SetStringSelection(p.get('HDBSCAN_CLUSTER_SELECTION_METHOD', 'eom'))
        self.clustering_controls['min_points'].SetValue(p.get('MIN_POINTS_FOR_CLUSTERING', 50))
        
        self.copy_number_controls['min_droplets'].SetValue(p.get('MIN_USABLE_DROPLETS', 3000))
        self.copy_number_controls['median_threshold'].SetValue(str(p.get('COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD', 0.15)))
        self.copy_number_controls['baseline_min'].SetValue(p.get('COPY_NUMBER_BASELINE_MIN_CHROMS', 3))
        self.copy_number_controls['tolerance_multiplier'].SetValue(p.get('TOLERANCE_MULTIPLIER', 3))
        aneuploidy_targets = p.get('ANEUPLOIDY_TARGETS', {})
        self.copy_number_controls['aneuploidy_targets']['low'].SetValue(str(aneuploidy_targets.get('low', 0.75)))
        self.copy_number_controls['aneuploidy_targets']['high'].SetValue(str(aneuploidy_targets.get('high', 1.25)))
        self._populate_grid(self.copy_numbers_grid, p.get('EXPECTED_COPY_NUMBERS', {}))
        self._populate_grid(self.std_dev_grid, p.get('EXPECTED_STANDARD_DEVIATION', {}))

        for key, control in self.vis_controls.items():
            value = p.get(key)
            if isinstance(control, csel.ColourSelect):
                if value and isinstance(value, str) and value.startswith('#'):
                    control.SetColour(value)
                else:
                    control.SetColour("#FF0000")
                    logger.warning(f"Invalid color '{value}' for '{key}' in parameters. Using fallback.")
            elif value is not None:
                control.SetValue(value)

    def _collect_grid(self, grid):
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
            centroids = {}
            for row in range(self.centroids_grid.GetNumberRows()):
                target = self.centroids_grid.GetCellValue(row, 0).strip()
                fam_str = self.centroids_grid.GetCellValue(row, 1).strip()
                hex_str = self.centroids_grid.GetCellValue(row, 2).strip()
                if target and fam_str and hex_str:
                    centroids[target] = [float(fam_str), float(hex_str)]
            params['EXPECTED_CENTROIDS'] = centroids
            params['BASE_TARGET_TOLERANCE'] = self.centroid_matching_controls['base_tolerance'].GetValue()
            params['SCALE_FACTOR_MIN'] = float(self.centroid_matching_controls['scale_min'].GetValue())
            params['SCALE_FACTOR_MAX'] = float(self.centroid_matching_controls['scale_max'].GetValue())
        except ValueError as e:
            wx.MessageBox(f"Invalid Centroid value: {e}", "Error", wx.OK | wx.ICON_ERROR)
            return None

        params['HDBSCAN_MIN_CLUSTER_SIZE'] = self.clustering_controls['min_cluster_size'].GetValue()
        params['HDBSCAN_MIN_SAMPLES'] = self.clustering_controls['min_samples'].GetValue()
        params['HDBSCAN_EPSILON'] = float(self.clustering_controls['epsilon'].GetValue())
        params['HDBSCAN_METRIC'] = self.clustering_controls['metric'].GetStringSelection()
        params['HDBSCAN_CLUSTER_SELECTION_METHOD'] = self.clustering_controls['selection_method'].GetStringSelection()
        params['MIN_POINTS_FOR_CLUSTERING'] = self.clustering_controls['min_points'].GetValue()

        try:
            params['MIN_USABLE_DROPLETS'] = self.copy_number_controls['min_droplets'].GetValue()
            params['COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD'] = float(self.copy_number_controls['median_threshold'].GetValue())
            params['COPY_NUMBER_BASELINE_MIN_CHROMS'] = self.copy_number_controls['baseline_min'].GetValue()
            params['TOLERANCE_MULTIPLIER'] = self.copy_number_controls['tolerance_multiplier'].GetValue()
            params['ANEUPLOIDY_TARGETS'] = {
                "low": float(self.copy_number_controls['aneuploidy_targets']['low'].GetValue()),
                "high": float(self.copy_number_controls['aneuploidy_targets']['high'].GetValue())
            }
            params['EXPECTED_COPY_NUMBERS'] = self._collect_grid(self.copy_numbers_grid)
            params['EXPECTED_STANDARD_DEVIATION'] = self._collect_grid(self.std_dev_grid)
            if params['EXPECTED_COPY_NUMBERS'] is None or params['EXPECTED_STANDARD_DEVIATION'] is None: return None
        except ValueError as e:
            wx.MessageBox(f"Invalid Copy Number value: {e}", "Error", wx.OK | wx.ICON_ERROR)
            return None

        for key, control in self.vis_controls.items():
            if isinstance(control, csel.ColourSelect):
                params[key] = control.GetColour().GetAsString(wx.C2S_HTML_SYNTAX)
            else:
                params[key] = control.GetValue()
        
        return params
    
    def on_load_from_config(self, event):
        """Load values from current config."""
        self.parameters = self.load_parameters()
        self.load_values()
        wx.MessageBox("Parameters loaded from current configuration", "Info", wx.OK | wx.ICON_INFORMATION)
    
    def on_reset_defaults(self, event):
        """Reset to default values."""
        if wx.MessageBox("Reset all parameters to defaults?", "Confirm", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
            class DefaultConfig:
                from ..config import Config
                EXPECTED_CENTROIDS = Config.EXPECTED_CENTROIDS
                BASE_TARGET_TOLERANCE = Config.BASE_TARGET_TOLERANCE
                SCALE_FACTOR_MIN = Config.SCALE_FACTOR_MIN
                SCALE_FACTOR_MAX = Config.SCALE_FACTOR_MAX
                HDBSCAN_MIN_CLUSTER_SIZE = Config.HDBSCAN_MIN_CLUSTER_SIZE
                HDBSCAN_MIN_SAMPLES = Config.HDBSCAN_MIN_SAMPLES
                HDBSCAN_EPSILON = Config.HDBSCAN_EPSILON
                HDBSCAN_METRIC = Config.HDBSCAN_METRIC
                HDBSCAN_CLUSTER_SELECTION_METHOD = Config.HDBSCAN_CLUSTER_SELECTION_METHOD
                MIN_POINTS_FOR_CLUSTERING = Config.MIN_POINTS_FOR_CLUSTERING
                MIN_USABLE_DROPLETS = Config.MIN_USABLE_DROPLETS
                COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD = Config.COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD
                COPY_NUMBER_BASELINE_MIN_CHROMS = Config.COPY_NUMBER_BASELINE_MIN_CHROMS
                EXPECTED_COPY_NUMBERS = Config.EXPECTED_COPY_NUMBERS
                TOLERANCE_MULTIPLIER = Config.TOLERANCE_MULTIPLIER
                ANEUPLOIDY_TARGETS = Config.ANEUPLOIDY_TARGETS
                EXPECTED_STANDARD_DEVIATION = Config.EXPECTED_STANDARD_DEVIATION
                X_AXIS_MIN = Config.X_AXIS_MIN
                X_AXIS_MAX = Config.X_AXIS_MAX
                Y_AXIS_MIN = Config.Y_AXIS_MIN
                Y_AXIS_MAX = Config.Y_AXIS_MAX
                X_GRID_INTERVAL = Config.X_GRID_INTERVAL
                Y_GRID_INTERVAL = Config.Y_GRID_INTERVAL
                INDIVIDUAL_PLOT_DPI = Config.INDIVIDUAL_PLOT_DPI
                COMPOSITE_PLOT_DPI = Config.COMPOSITE_PLOT_DPI
                ANEUPLOIDY_FILL_COLOR = Config.ANEUPLOIDY_FILL_COLOR
                BUFFER_ZONE_FILL_COLOR = Config.BUFFER_ZONE_FILL_COLOR

            original_config_cls = self.config_cls
            self.config_cls = DefaultConfig
            self.parameters = self.load_parameters()
            self.config_cls = original_config_cls
            
            self.centroids_grid.ClearGrid()
            self.copy_numbers_grid.ClearGrid()
            self.std_dev_grid.ClearGrid()
            
            self.load_values()
            wx.MessageBox("Parameters have been reset to their default values.", "Info", wx.OK | wx.ICON_INFORMATION)

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
        
        logger.info(f"Applied parameters from {PARAMETERS_FILE}")
        
    except Exception as e:
        logger.error(f"Error applying parameters: {e}")
        raise ConfigError(f"Failed to apply parameters: {e}") from e


def load_parameters_if_exist(config_cls):
    """
    Load parameters file if it exists and apply to config.
    
    This function is called during config initialization to automatically
    load user parameters if they exist.
    
    Args:
        config_cls: The Config class to update
        
    Returns:
        True if parameters were loaded, False otherwise
    """
    if os.path.exists(PARAMETERS_FILE):
        try:
            apply_parameters_to_config(config_cls)
            logger.debug("Automatically loaded user parameters")
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