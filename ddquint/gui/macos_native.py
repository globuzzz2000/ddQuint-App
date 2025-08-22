#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Native macOS GUI Application for ddQuint

Uses Tkinter with macOS-specific styling and behaviors for a native look and feel.
This version is optimized for .app bundle distribution.
"""

import sys
import os
import threading
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib
matplotlib.use('TkAgg')  # Set backend before importing pyplot
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import pandas as pd

# Configure matplotlib for macOS app bundle
plt.rcParams['figure.max_open_warning'] = 50

# Import ddQuint components
try:
    from ..core import process_directory, create_list_report
    from ..visualization import create_composite_image, create_well_plot
    from ..config import Config, setup_logging
    from ..utils import get_sample_names
    from ..utils.parameter_editor import open_parameter_editor
except ImportError:
    # Fallback for direct execution
    import ddquint
    from ddquint.core import process_directory, create_list_report
    from ddquint.visualization import create_composite_image, create_well_plot
    from ddquint.config import Config, setup_logging
    from ddquint.utils import get_sample_names
    from ddquint.utils.parameter_editor import open_parameter_editor

logger = logging.getLogger(__name__)


class ddQuintMacOSNativeApp:
    """Native macOS application for ddQuint pipeline."""
    
    def __init__(self):
        # Initialize logging
        setup_logging(debug=False)
        
        # Create root window with macOS styling
        self.root = tk.Tk()
        self.setup_macos_window()
        
        # Application state
        self.selected_folder = None
        self.analysis_results = []
        self.current_plot_index = 0
        self.analysis_thread = None
        self.config = Config.get_instance()
        
        # Setup UI
        self.setup_ui()
        
        # Show folder selection after UI is ready
        self.root.after(500, self.show_initial_folder_selection)
    
    def setup_macos_window(self):
        """Configure window for native macOS appearance."""
        self.root.title("ddQuint")
        self.root.geometry("1400x900")
        
        # macOS specific styling
        if sys.platform == 'darwin':
            # Use system appearance
            try:
                self.root.tk.call('::tk::unsupported::MacWindowStyle', 
                                self.root._w, 'document')
            except tk.TclError:
                pass
        
        # Configure colors for macOS
        self.root.configure(bg='#f6f6f6')
        
        # Configure ttk styles
        self.style = ttk.Style()
        if sys.platform == 'darwin':
            self.style.theme_use('aqua')
        
        # Custom styles
        self.style.configure('Title.TLabel', font=('SF Pro Display', 24, 'bold'))
        self.style.configure('Subtitle.TLabel', font=('SF Pro Display', 14))
        self.style.configure('Large.TButton', font=('SF Pro Display', 12))
    
    def setup_ui(self):
        """Initialize the main application UI."""
        # Main container with padding
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)
        
        # Setup different views
        self.setup_welcome_view()
        self.setup_progress_view()
        self.setup_results_view()
        
        # Start with welcome view
        self.show_welcome_view()
    
    def setup_welcome_view(self):
        """Setup the welcome screen."""
        self.welcome_frame = ttk.Frame(self.main_frame)
        
        # Centered container
        welcome_container = ttk.Frame(self.welcome_frame)
        welcome_container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # App icon placeholder (you can add an icon here)
        icon_frame = ttk.Frame(welcome_container)
        icon_frame.pack(pady=(0, 30))
        
        # Title
        title_label = ttk.Label(
            welcome_container,
            text="ddQuint",
            style='Title.TLabel'
        )
        title_label.pack(pady=(0, 10))
        
        # Subtitle
        subtitle_label = ttk.Label(
            welcome_container,
            text="Digital Droplet PCR Analysis",
            style='Subtitle.TLabel'
        )
        subtitle_label.pack(pady=(0, 40))
        
        # Description
        desc_label = ttk.Label(
            welcome_container,
            text="Select a folder containing ddPCR CSV files to begin analysis",
            font=('SF Pro Display', 12)
        )
        desc_label.pack(pady=(0, 30))
        
        # Folder selection area
        folder_frame = ttk.LabelFrame(welcome_container, text="Select Data Folder", padding="20")
        folder_frame.pack(pady=(0, 20), fill=tk.X)
        
        # Folder path entry
        path_frame = ttk.Frame(folder_frame)
        path_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.folder_path_var = tk.StringVar()
        self.folder_path_var.trace_add("write", self.on_folder_entry_change)
        self.folder_entry = ttk.Entry(
            path_frame,
            textvariable=self.folder_path_var,
            font=('SF Pro Display', 11),
            width=50
        )
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # Browse button
        self.browse_button = ttk.Button(
            path_frame,
            text="Browse...",
            command=self.browse_folder,
            width=12
        )
        self.browse_button.pack(side=tk.RIGHT)
        
        # Folder info label
        self.folder_info_label = ttk.Label(
            folder_frame,
            text="Select a folder containing ddPCR CSV files",
            foreground='#666666',
            font=('SF Pro Display', 10)
        )
        self.folder_info_label.pack(pady=(0, 10))
        
        # Start analysis button
        self.start_button = ttk.Button(
            welcome_container,
            text="Start Analysis",
            command=self.start_analysis,
            style='Large.TButton',
            state='disabled'
        )
        self.start_button.pack(pady=10)
    
    def setup_progress_view(self):
        """Setup the analysis progress view."""
        self.progress_frame = ttk.Frame(self.main_frame)
        
        # Centered progress container
        progress_container = ttk.Frame(self.progress_frame)
        progress_container.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Progress title
        progress_title = ttk.Label(
            progress_container,
            text="Analyzing Files",
            style='Title.TLabel'
        )
        progress_title.pack(pady=(0, 40))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_container,
            variable=self.progress_var,
            maximum=100,
            length=400,
            mode='determinate'
        )
        self.progress_bar.pack(pady=(0, 20))
        
        # Status label
        self.status_label = ttk.Label(
            progress_container, 
            text="Initializing...",
            font=('SF Pro Display', 12)
        )
        self.status_label.pack(pady=(0, 40))
        
        # Cancel button
        self.cancel_button = ttk.Button(
            progress_container,
            text="Cancel",
            command=self.cancel_analysis
        )
        self.cancel_button.pack()
    
    def setup_results_view(self):
        """Setup the results viewing interface."""
        self.results_frame = ttk.Frame(self.main_frame)
        
        # Create paned window for resizable panels
        self.paned_window = ttk.PanedWindow(self.results_frame, orient=tk.HORIZONTAL)
        self.paned_window.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid
        self.results_frame.columnconfigure(0, weight=1)
        self.results_frame.rowconfigure(0, weight=1)
        
        # Left panel - controls and file list
        self.left_panel = ttk.Frame(self.paned_window, padding="10")
        self.paned_window.add(self.left_panel, weight=1)
        
        # Right panel - plot display
        self.right_panel = ttk.Frame(self.paned_window, padding="10")
        self.paned_window.add(self.right_panel, weight=3)
        
        self.setup_control_panel()
        self.setup_plot_panel()
    
    def setup_control_panel(self):
        """Setup the left control panel."""
        # Title
        title_label = ttk.Label(
            self.left_panel,
            text="Results",
            font=('SF Pro Display', 16, 'bold')
        )
        title_label.pack(pady=(0, 15))
        
        # File list with scrollbar
        list_frame = ttk.Frame(self.left_panel)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Listbox with scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=('SF Pro Display', 11),
            selectmode=tk.SINGLE
        )
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)
        
        # Parameters section
        params_label = ttk.Label(
            self.left_panel,
            text="Parameters",
            font=('SF Pro Display', 14, 'bold')
        )
        params_label.pack(pady=(10, 5))
        
        self.param_frame = ttk.Frame(self.left_panel)
        self.param_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Export section
        export_label = ttk.Label(
            self.left_panel,
            text="Export",
            font=('SF Pro Display', 14, 'bold')
        )
        export_label.pack(pady=(10, 5))
        
        # Export buttons
        export_frame = ttk.Frame(self.left_panel)
        export_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.export_excel_button = ttk.Button(
            export_frame,
            text="Export Excel Report",
            command=self.export_excel
        )
        self.export_excel_button.pack(fill=tk.X, pady=2)
        
        self.export_plots_button = ttk.Button(
            export_frame,
            text="Export All Plots",
            command=self.export_plots
        )
        self.export_plots_button.pack(fill=tk.X, pady=2)
        
        self.export_individual_plots_button = ttk.Button(
            export_frame,
            text="Export Individual Plots",
            command=self.export_individual_plots
        )
        self.export_individual_plots_button.pack(fill=tk.X, pady=2)
        
        # Configuration section
        config_label = ttk.Label(
            self.left_panel,
            text="Configuration",
            font=('SF Pro Display', 14, 'bold')
        )
        config_label.pack(pady=(10, 5))
        
        config_frame = ttk.Frame(self.left_panel)
        config_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.global_params_button = ttk.Button(
            config_frame,
            text="Global Parameters",
            command=self.open_parameters
        )
        self.global_params_button.pack(fill=tk.X, pady=2)
        
        # New analysis button
        self.new_button = ttk.Button(
            self.left_panel,
            text="New Analysis",
            command=self.new_analysis,
            style='Large.TButton'
        )
        self.new_button.pack(pady=(20, 0))
    
    def setup_plot_panel(self):
        """Setup the plot display area."""
        # Plot container
        plot_container = ttk.Frame(self.right_panel)
        plot_container.pack(fill=tk.BOTH, expand=True)
        
        # Create matplotlib figure with macOS-friendly settings
        self.fig, self.ax = plt.subplots(figsize=(10, 8), dpi=100)
        self.fig.patch.set_facecolor('#f6f6f6')
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, plot_container)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add navigation toolbar
        toolbar_frame = ttk.Frame(plot_container)
        toolbar_frame.pack(fill=tk.X)
        
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()
        
        # Initial empty plot
        self.show_empty_plot()
    
    def show_empty_plot(self):
        """Show empty plot with instructions."""
        self.ax.clear()
        self.ax.text(0.5, 0.5, 'Select a file from the list to view results', 
                    ha='center', va='center', transform=self.ax.transAxes,
                    fontsize=14, color='#666666')
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.canvas.draw()
    
    def show_initial_folder_selection(self):
        """Don't auto-show folder selection - integrate it into main window."""
        pass
    
    def browse_folder(self):
        """Handle folder browsing with native dialog."""
        folder = filedialog.askdirectory(
            title="Choose folder with ddPCR CSV files",
            mustexist=True
        )
        
        if folder:
            self.folder_path_var.set(folder)
            self.update_folder_selection(folder)
    
    def update_folder_selection(self, folder):
        """Update the folder selection and validate it."""
        self.selected_folder = folder
        
        # Validate folder has CSV files
        csv_files = list(Path(folder).glob("*.csv"))
        
        if csv_files:
            self.folder_info_label.config(
                text=f"✅ Found {len(csv_files)} CSV files",
                foreground='#4CAF50'
            )
            self.start_button.config(state='normal')
            logger.info(f"Selected folder: {folder} with {len(csv_files)} CSV files")
        else:
            self.folder_info_label.config(
                text="⚠️ No CSV files found in this folder",
                foreground='#FF9800'
            )
            self.start_button.config(state='disabled')
            
    def on_folder_entry_change(self, *args):
        """Handle manual folder path entry."""
        folder = self.folder_path_var.get()
        if folder and os.path.isdir(folder):
            self.update_folder_selection(folder)
    
    def start_analysis(self):
        """Start the analysis process."""
        if not self.selected_folder:
            messagebox.showerror("Error", "Please select a folder first")
            return
        
        # Validate folder has CSV files
        csv_files = list(Path(self.selected_folder).glob("*.csv"))
        if not csv_files:
            messagebox.showwarning("No CSV Files", 
                                 f"No CSV files found in the selected folder:\n{self.selected_folder}")
            return
        
        logger.info(f"Starting analysis of {len(csv_files)} CSV files")
        self.show_progress_view()
        
        # Start analysis in separate thread
        self.analysis_thread = threading.Thread(target=self.run_analysis, daemon=True)
        self.analysis_thread.start()
    
    def run_analysis(self):
        """Run the ddQuint analysis pipeline."""
        try:
            self.update_progress(10, "Loading sample names...")
            sample_names = get_sample_names(self.selected_folder)
            logger.info(f"Loaded {len(sample_names)} sample names")
            
            self.update_progress(30, "Processing CSV files...")
            self.analysis_results = process_directory(
                self.selected_folder,
                self.selected_folder,
                sample_names,
                verbose=True
            )
            logger.info(f"Processed {len(self.analysis_results)} files")
            
            self.update_progress(80, "Preparing visualizations...")
            # Add sample names to results
            for result in self.analysis_results:
                well_id = result.get('well')
                if well_id and sample_names and well_id in sample_names:
                    result['sample_name'] = sample_names[well_id]
            
            self.update_progress(100, "Analysis complete!")
            
            # Show results after a brief pause
            self.root.after(1000, self.show_results_view)
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            error_msg = f"Analysis failed:\n{str(e)}"
            self.root.after(0, lambda: messagebox.showerror("Analysis Error", error_msg))
            self.root.after(0, self.show_welcome_view)
    
    def update_progress(self, value, status):
        """Update progress bar and status."""
        self.root.after(0, lambda: self.progress_var.set(value))
        self.root.after(0, lambda: self.status_label.config(text=status))
    
    def cancel_analysis(self):
        """Cancel the running analysis."""
        logger.info("Analysis cancelled by user")
        self.show_welcome_view()
    
    def show_welcome_view(self):
        """Display the welcome view."""
        self.hide_all_views()
        self.welcome_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def show_progress_view(self):
        """Display the progress view."""
        self.hide_all_views()
        self.progress_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def show_results_view(self):
        """Display the results view."""
        self.hide_all_views()
        self.results_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.populate_results()
    
    def hide_all_views(self):
        """Hide all views."""
        for frame in [self.welcome_frame, self.progress_frame, self.results_frame]:
            frame.grid_remove()
    
    def populate_results(self):
        """Populate the results view with analysis data."""
        self.file_listbox.delete(0, tk.END)
        
        if not self.analysis_results:
            self.file_listbox.insert(tk.END, "No results to display")
            return
        
        for i, result in enumerate(self.analysis_results):
            well = result.get('well', f'Result {i+1}')
            sample_name = result.get('sample_name', '')
            
            if sample_name:
                display_name = f"{well}: {sample_name}"
            else:
                display_name = well
            
            self.file_listbox.insert(tk.END, display_name)
        
        # Select first item
        if self.analysis_results:
            self.file_listbox.selection_set(0)
            self.display_plot(0)
    
    def on_file_select(self, event):
        """Handle file selection in listbox."""
        selection = self.file_listbox.curselection()
        if selection and self.analysis_results:
            index = selection[0]
            self.display_plot(index)
    
    def display_plot(self, index):
        """Display the plot for the selected result with proper clustering and annotations."""
        if not (0 <= index < len(self.analysis_results)):
            return
        
        result = self.analysis_results[index]
        self.current_plot_index = index
        self.ax.clear()
        
        # Get the data
        df_filtered = result.get('df_filtered')
        df_raw = result.get('dataframe')
        counts = result.get('counts', {})
        copy_numbers = result.get('copy_numbers', {})
        
        well = result.get('well', 'Unknown')
        sample_name = result.get('sample_name', '')
        title = f"{well}: {sample_name}" if sample_name else well
        
        # Set up plot styling
        self.ax.set_xlabel('HEX Amplitude')
        self.ax.set_ylabel('FAM Amplitude')
        self.ax.set_title(title, fontsize=14, pad=20)
        
        # Set axis limits from config
        axis_limits = self.config.get_axis_limits()
        self.ax.set_xlim(axis_limits['x'])
        self.ax.set_ylim(axis_limits['y'])
        
        # Add grid
        self.ax.grid(True, alpha=0.3)
        
        # Display clustered data if available
        if df_filtered is not None and not df_filtered.empty:
            # Get color mapping
            label_color_map = self.config.TARGET_COLORS
            
            # Use the correct column names
            x_col = 'Ch2Amplitude' if 'Ch2Amplitude' in df_filtered.columns else 'Ch2 Amplitude'
            y_col = 'Ch1Amplitude' if 'Ch1Amplitude' in df_filtered.columns else 'Ch1 Amplitude'
            
            # Plot clustered droplets with colors
            df_filtered_copy = df_filtered.copy()
            df_filtered_copy['color'] = df_filtered_copy['TargetLabel'].map(label_color_map)
            colors = df_filtered_copy['color'].fillna('#c7c7c7').astype(str).tolist()
            
            self.ax.scatter(df_filtered_copy[x_col], df_filtered_copy[y_col],
                          c=colors, s=20, alpha=0.7)
            
            # Add copy number annotations if available
            if copy_numbers:
                for target, color in label_color_map.items():
                    if target in copy_numbers and target != 'Negative':
                        # Get cluster centroid
                        target_points = df_filtered_copy[df_filtered_copy['TargetLabel'] == target]
                        if not target_points.empty:
                            cx = target_points[x_col].mean()
                            cy = target_points[y_col].mean()
                            cn_value = copy_numbers[target]
                            
                            self.ax.text(cx, cy, f"{cn_value:.2f}", 
                                        color='black', fontsize=10, fontweight='bold',
                                        ha='center', va='center',
                                        bbox=dict(facecolor='white', alpha=0.8, pad=2))
            
            # Create legend for clusters
            legend_elements = []
            for target in ['Negative', 'Chrom1', 'Chrom2', 'Chrom3', 'Chrom4', 'Chrom5']:
                if target in counts and counts[target] > 0:
                    color = label_color_map.get(target, '#c7c7c7')
                    legend_elements.append(plt.Line2D([0], [0], marker='o', color='w', 
                                                    markerfacecolor=color, markersize=8, label=target))
            
            if legend_elements:
                self.ax.legend(handles=legend_elements, loc='upper right', fontsize=8)
                
        elif df_raw is not None and not df_raw.empty:
            # Show raw data if no clustering available
            x_col_raw = 'Ch2Amplitude' if 'Ch2Amplitude' in df_raw.columns else 'Ch2 Amplitude'
            y_col_raw = 'Ch1Amplitude' if 'Ch1Amplitude' in df_raw.columns else 'Ch1 Amplitude'
            self.ax.scatter(df_raw[x_col_raw], df_raw[y_col_raw], 
                          c='gray', alpha=0.5, s=20)
            self.ax.text(0.5, 0.95, 'Raw Data (No Clustering)', 
                        transform=self.ax.transAxes, ha='center', 
                        bbox=dict(boxstyle="round,pad=0.3", facecolor='yellow', alpha=0.7))
        else:
            # No data available
            self.ax.text(0.5, 0.5, 'No data available for this file', 
                        ha='center', va='center', transform=self.ax.transAxes,
                        fontsize=12, color='#666666')
        
        self.canvas.draw()
        self.setup_parameter_controls(result)
    
    def setup_parameter_controls(self, result):
        """Setup parameter controls for the selected result."""
        # Clear existing controls
        for widget in self.param_frame.winfo_children():
            widget.destroy()
        
        # Add some basic parameter controls
        clustering_results = result.get('clustering_results', {})
        
        if clustering_results:
            # Example parameter control
            ttk.Label(self.param_frame, text="Min Cluster Size:").pack(anchor=tk.W)
            
            cluster_size_var = tk.IntVar(value=clustering_results.get('min_cluster_size', 50))
            cluster_size_scale = ttk.Scale(
                self.param_frame,
                from_=10, to=200,
                variable=cluster_size_var,
                orient=tk.HORIZONTAL
            )
            cluster_size_scale.pack(fill=tk.X, pady=(2, 10))
    
    def export_excel(self):
        """Export results to Excel file."""
        if not self.analysis_results:
            messagebox.showwarning("No Data", "No analysis results to export")
            return
        
        try:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="Save Excel Report"
            )
            
            if filepath:
                create_list_report(self.analysis_results, filepath)
                messagebox.showinfo("Export Successful", 
                                  f"Excel report saved to:\n{os.path.basename(filepath)}")
                logger.info(f"Excel report exported to: {filepath}")
                
        except Exception as e:
            logger.error(f"Excel export failed: {e}", exc_info=True)
            messagebox.showerror("Export Error", f"Failed to export Excel file:\n{str(e)}")
    
    def export_plots(self):
        """Export all plots as images."""
        if not self.analysis_results:
            messagebox.showwarning("No Data", "No analysis results to export")
            return
        
        try:
            folder = filedialog.askdirectory(title="Choose folder to save plots")
            
            if folder:
                composite_path = os.path.join(folder, "composite_plot.png")
                create_composite_image(self.analysis_results, composite_path)
                
                messagebox.showinfo("Export Successful", 
                                  f"Plots saved to:\n{os.path.basename(folder)}")
                logger.info(f"Plots exported to: {folder}")
                
        except Exception as e:
            logger.error(f"Plot export failed: {e}", exc_info=True)
            messagebox.showerror("Export Error", f"Failed to export plots:\n{str(e)}")
    
    def export_individual_plots(self):
        """Export individual well plots as separate images."""
        if not self.analysis_results:
            messagebox.showwarning("No Data", "No analysis results to export")
            return
        
        try:
            folder = filedialog.askdirectory(title="Choose folder to save individual plots")
            
            if folder:
                saved_count = 0
                for result in self.analysis_results:
                    well = result.get('well')
                    if well:
                        # Create individual plot
                        plot_path = os.path.join(folder, f"{well}_plot.png")
                        
                        # Get raw data
                        df_raw = result.get('dataframe')
                        clustering_results = {
                            'df_filtered': result.get('df_filtered'),
                            'target_mapping': result.get('target_mapping'),
                            'counts': result.get('counts', {}),
                            'copy_numbers': result.get('copy_numbers', {}),
                            'copy_number_states': result.get('copy_number_states', {}),
                            'has_aneuploidy': result.get('has_aneuploidy', False),
                            'has_buffer_zone': result.get('has_buffer_zone', False),
                            'error': result.get('error')
                        }
                        
                        sample_name = result.get('sample_name')
                        created_path = create_well_plot(
                            df_raw, clustering_results, well, plot_path, 
                            for_composite=False, add_copy_numbers=True, sample_name=sample_name
                        )
                        
                        if created_path:
                            saved_count += 1
                
                messagebox.showinfo("Export Successful", 
                                  f"Saved {saved_count} individual plots to:\n{os.path.basename(folder)}")
                logger.info(f"Individual plots exported to: {folder}")
                
        except Exception as e:
            logger.error(f"Individual plot export failed: {e}", exc_info=True)
            messagebox.showerror("Export Error", f"Failed to export individual plots:\n{str(e)}")
    
    def open_parameters(self):
        """Open the global parameters editor."""
        try:
            # Open parameter editor
            success = open_parameter_editor(Config)
            
            if success:
                # Reload config and refresh current plot
                self.config = Config.get_instance()
                if hasattr(self, 'current_plot_index') and self.current_plot_index is not None:
                    self.display_plot(self.current_plot_index)
                messagebox.showinfo("Success", "Parameters updated successfully!")
            
        except Exception as e:
            logger.error(f"Parameter editor failed: {e}", exc_info=True)
            messagebox.showerror("Parameter Error", f"Failed to open parameter editor:\n{str(e)}")
    
    def new_analysis(self):
        """Start a new analysis."""
        self.analysis_results = []
        self.selected_folder = None
        self.folder_path_var.set("")
        self.start_button.config(state='disabled')
        self.show_welcome_view()
        logger.info("Started new analysis")
    
    def run(self):
        """Start the application main loop."""
        logger.info("Starting ddQuint macOS application")
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start the main loop
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        except Exception as e:
            logger.error(f"Application error: {e}", exc_info=True)
        finally:
            logger.info("Application closed")
    
    def on_closing(self):
        """Handle application closing."""
        if self.analysis_thread and self.analysis_thread.is_alive():
            # Analysis is running, confirm exit
            if messagebox.askokcancel("Quit", "Analysis is running. Do you want to quit?"):
                self.root.quit()
        else:
            self.root.quit()


def main():
    """Main entry point for the macOS GUI application."""
    try:
        app = ddQuintMacOSNativeApp()
        app.run()
    except Exception as e:
        print(f"Failed to start application: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()