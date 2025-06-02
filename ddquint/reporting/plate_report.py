"""
Excel report generation module for ddQuint with dynamic chromosome support
"""

import os
import numpy as np
import traceback
import logging
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Border, Side, Alignment, Font
from openpyxl.utils import get_column_letter

from ..config.config import Config

# Define plate layout constants - swapped for column-first layout
COL_LABELS = list('ABCDEFGH')  # Now these are the vertical labels (columns)
ROW_LABELS = [str(i) for i in range(1, 13)]  # Now these are the horizontal labels (rows)

# Define cell colors
NORMAL_FILL = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
ANEUPLOIDY_FILL = PatternFill(start_color="E6B8E6", end_color="E6B8E6", fill_type="solid")
ANEUPLOIDY_VALUE_FILL = PatternFill(start_color="D070D0", end_color="D070D0", fill_type="solid")
BUFFER_ZONE_FILL = PatternFill(start_color="E6E6E6", end_color="E6E6E6", fill_type="solid")
BUFFER_ZONE_VALUE_FILL = PatternFill(start_color="B0B0B0", end_color="B0B0B0", fill_type="solid")

# Define border styles
thin = Side(style='thin')
thick = Side(style='thick')

# Standard borders
thin_border = Border(left=thin, right=thin, top=thin, bottom=thin)
thick_border = Border(left=thick, right=thick, top=thick, bottom=thick)

def create_plate_report(results, output_path, template_path=None):
    """
    Create an Excel report with all analysis results.
    
    Args:
        results (list): List of result dictionaries for each well
        output_path (str): Path to save the Excel report
        template_path (str, optional): Not used, kept for API compatibility
        
    Returns:
        str: Path to the saved Excel report
    """
    logger = logging.getLogger("ddQuint")
    config = Config.get_instance()
    
    # Get the number of chromosomes from config
    chromosome_keys = config.get_chromosome_keys()
    num_chromosomes = len(chromosome_keys)
    
    logger.debug(f"Creating Excel report for {len(results)} results with {num_chromosomes} chromosomes")
    logger.debug(f"Output path: {output_path}")
    
    try:
        # Create a new workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Plate Results"
        logger.debug("Created new workbook")

        # Create the full grid layout without any merging first
        create_grid_layout_without_merging(ws, results, num_chromosomes)
        
        # Apply all cell merges AFTER setting values
        apply_cell_merges(ws, num_chromosomes)
        
        # Apply formatting and borders
        apply_formatting(ws, num_chromosomes)
        
        # Save the workbook
        try:
            wb.save(output_path)
            logger.debug(f"Excel report saved successfully to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error saving Excel report: {str(e)}")
            logger.debug("Error details:", exc_info=True)
            # Try to save with a different name if there was an error
            try:
                alt_path = os.path.join(os.path.dirname(output_path), "Plate_Results_alt.xlsx")
                wb.save(alt_path)
                logger.info(f"Saved alternative report to: {alt_path}")
                return alt_path
            except Exception as e2:
                logger.error(f"Error saving alternative report: {str(e2)}")
                logger.debug("Error details:", exc_info=True)
                return None
    except Exception as e:
        logger.error(f"Error creating Excel report: {str(e)}")
        logger.debug("Error details:", exc_info=True)
        return None

def create_grid_layout_without_merging(ws, results, num_chromosomes):
    """
    Create the grid layout for the 96-well plate without any cell merging.
    Now arranged in column-first order.
    
    Args:
        ws: Worksheet to modify
        results: List of result dictionaries
        num_chromosomes: Number of chromosomes to display
    """
    logger = logging.getLogger("ddQuint")
    config = Config.get_instance()
    
    logger.debug(f"Creating grid layout for {len(results)} results with {num_chromosomes} chromosomes")
    
    # Set header row values
    setup_header_values(ws)
    
    # Convert results list to a dictionary keyed by well ID for easy lookup
    result_dict = {r.get('well', ''): r for r in results if r.get('well') is not None}
    logger.debug(f"Created result dictionary with {len(result_dict)} valid wells")
    
    # Process each column (A-H) - now these are the vertical divisions
    for col_idx, col_label in enumerate(COL_LABELS):
        logger.debug(f"Processing column {col_label}")
        # Starting row for this plate column (each well takes num_chromosomes+1 rows)
        start_row = col_idx * (num_chromosomes + 1) + 3  # Start from row 3 (after headers)
        
        # Add column label in column A
        col_label_cell = ws.cell(row=start_row, column=1)
        col_label_cell.value = col_label
        col_label_cell.font = Font(bold=True)
        col_label_cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Process each row (1-12) - now these are the horizontal divisions
        for row_idx, row_label in enumerate(ROW_LABELS):
            well_id = f"{col_label}{row_label.zfill(2)}"
            logger.debug(f"Processing well {well_id}")
            
            # Starting column for this well (each well takes 3 columns)
            start_col = row_idx * 3 + 2  # Start from column B (column 2)
            
            # Fill in data for this well without merging
            add_well_data(ws, start_row, start_col, well_id, result_dict.get(well_id), num_chromosomes)

def setup_header_values(ws):
    """
    Set up the header row values without merging.
    Now arranged for column-first layout (1-12 across the top).
    """
    logger = logging.getLogger("ddQuint")
    logger.debug("Setting up header values")
    
    # Row 1: Row numbers (1-12) - now these are horizontal headers
    for row_idx in range(1, 13):
        # Each well takes 3 columns
        cell_col = (row_idx - 1) * 3 + 2  # Start at column B (column 2)
        
        # Set row number in the first column of the well
        cell = ws.cell(row=1, column=cell_col)
        cell.value = row_idx
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
        logger.debug(f"Set row header {row_idx} at column {cell_col}")
    
    # Row 2: "abs." and "rel." labels
    for row_idx in range(1, 13):
        base_col = (row_idx - 1) * 3 + 2
        
        # First column is blank (for chromosome name)
        first_cell = ws.cell(row=2, column=base_col)
        first_cell.value = ""
        
        # Second column: "abs."
        abs_cell = ws.cell(row=2, column=base_col + 1)
        abs_cell.value = "abs."
        abs_cell.font = Font(size=9)
        abs_cell.alignment = Alignment(horizontal='center')
        
        # Third column: "rel."
        rel_cell = ws.cell(row=2, column=base_col + 2)
        rel_cell.value = "rel."
        rel_cell.font = Font(size=9)
        rel_cell.alignment = Alignment(horizontal='center')
        
        logger.debug(f"Set subheaders for row {row_idx}")

def add_well_data(ws, start_row, start_col, well_id, result, num_chromosomes):
    """
    Add data for a single well without merging.
    
    Args:
        ws: Worksheet to modify
        start_row: Starting row for this well
        start_col: Starting column for this well
        well_id: Well identifier (e.g., 'A1')
        result: Result dictionary for this well, or None if no data
        num_chromosomes: Number of chromosomes to display
    """
    logger = logging.getLogger("ddQuint")
    config = Config.get_instance()
    
    logger.debug(f"Adding data for well {well_id} at position ({start_row}, {start_col})")
    
    # Add the sample name to the first row (which will be merged later)
    name_cell = ws.cell(row=start_row, column=start_col)
    
    if result:
        # Get the sample name from the result or fallback to filename or well_id
        sample_name = result.get('sample_name')
        if not sample_name:
            filename = result.get('filename', '')
            sample_name = os.path.splitext(filename)[0] if filename else well_id
            
        name_cell.value = sample_name
        name_cell.alignment = Alignment(horizontal='center', wrap_text=True)
        name_cell.font = Font(size=9)
        logger.debug(f"Added sample name: {sample_name}")
    else:
        # For empty wells, show the well ID
        name_cell.value = well_id
        name_cell.alignment = Alignment(horizontal='center')
        name_cell.font = Font(size=9, color='C0C0C0')  # Light gray for empty wells
        logger.debug(f"No data for well, using well ID as placeholder")
    
    # Will set blank values to cells that will be merged with the name cell
    ws.cell(row=start_row, column=start_col+1).value = ""
    ws.cell(row=start_row, column=start_col+2).value = ""
    
    # If we have a result for this well, fill in the chromosome data
    if result:
        # Get count data and copy numbers
        counts = result.get('counts', {})
        copy_numbers = result.get('copy_numbers', {})
        copy_number_states = result.get('copy_number_states', {})
        has_aneuploidy = result.get('has_aneuploidy', False)
        has_buffer_zone = result.get('has_buffer_zone', False)
        
        logger.debug(f"Well has aneuploidy: {has_aneuploidy}")
        logger.debug(f"Well has buffer zone: {has_buffer_zone}")
        logger.debug(f"Counts: {counts}")
        logger.debug(f"Copy numbers: {copy_numbers}")
        logger.debug(f"Copy number states: {copy_number_states}")
        
        # Get chromosome keys dynamically
        chromosome_keys = config.get_chromosome_keys()
        
        # Create cells for each chromosome
        for chrom_idx, chrom_key in enumerate(chromosome_keys):
            # Row for this chromosome
            chrom_row = start_row + 1 + chrom_idx
            chrom_label = f"Chr{chrom_key.replace('Chrom', '')}"
            
            # Chromosome name cell
            chrom_cell = ws.cell(row=chrom_row, column=start_col)
            chrom_cell.value = chrom_label
            chrom_cell.font = Font(size=9)
            
            # Absolute count cell
            abs_cell = ws.cell(row=chrom_row, column=start_col+1)
            abs_count = counts.get(chrom_key, 0)
            abs_cell.value = abs_count if abs_count > 0 else None
            abs_cell.font = Font(size=9)
            abs_cell.alignment = Alignment(horizontal='center')
            
            # Relative count cell
            rel_cell = ws.cell(row=chrom_row, column=start_col+2)
            rel_count = copy_numbers.get(chrom_key)
            if rel_count is not None:
                rel_cell.value = round(rel_count, 2)
                rel_cell.number_format = '0.00'
                rel_cell.font = Font(size=9)
                rel_cell.alignment = Alignment(horizontal='center')
            
            # Apply highlighting for buffer zones and aneuploidies
            # Buffer zone trumps aneuploidy
            if has_buffer_zone:
                # Dark grey fill for buffer zone samples (entire well)
                chrom_cell.fill = PatternFill(start_color="B0B0B0", end_color="B0B0B0", fill_type="solid")
                abs_cell.fill = PatternFill(start_color="B0B0B0", end_color="B0B0B0", fill_type="solid")
                rel_cell.fill = PatternFill(start_color="B0B0B0", end_color="B0B0B0", fill_type="solid")
                logger.debug(f"Applied buffer zone highlighting to {chrom_label}")
            elif has_aneuploidy:
                # Light purple fill for aneuploidy samples (entire well)
                chrom_cell.fill = ANEUPLOIDY_FILL
                abs_cell.fill = ANEUPLOIDY_FILL
                rel_cell.fill = ANEUPLOIDY_FILL
                
                # Darker purple fill for individual aneuploidy chromosomes
                if rel_count is not None:
                    chrom_state = copy_number_states.get(chrom_key, 'euploid')
                    if chrom_state == 'aneuploidy':
                        # Individual chromosome aneuploidy highlighting (darker purple)
                        chrom_cell.fill = ANEUPLOIDY_VALUE_FILL
                        abs_cell.fill = ANEUPLOIDY_VALUE_FILL
                        rel_cell.fill = ANEUPLOIDY_VALUE_FILL
                        logger.debug(f"{chrom_label} has aneuploidy value: {rel_count:.2f}")
                    elif not copy_number_states and abs(rel_count - 1.0) > 0.15:
                        # Fallback for legacy detection
                        chrom_cell.fill = ANEUPLOIDY_VALUE_FILL
                        abs_cell.fill = ANEUPLOIDY_VALUE_FILL
                        rel_cell.fill = ANEUPLOIDY_VALUE_FILL
                        logger.debug(f"{chrom_label} has legacy aneuploidy value: {rel_count:.2f}")
            
            logger.debug(f"Added {chrom_label} data: abs={abs_count}, rel={rel_count}")
    else:
        # If no data for this well, just add the chromosome labels
        chromosome_keys = config.get_chromosome_keys()
        for chrom_idx, chrom_key in enumerate(chromosome_keys):
            chrom_label = f"Chr{chrom_key.replace('Chrom', '')}"
            chrom_row = start_row + 1 + chrom_idx
            chrom_cell = ws.cell(row=chrom_row, column=start_col)
            chrom_cell.value = chrom_label
            chrom_cell.font = Font(size=9, color='C0C0C0')  # Light gray for empty wells
        logger.debug("Added empty chromosome labels")

def apply_cell_merges(ws, num_chromosomes):
    """
    Apply all cell merges after setting all cell values.
    Updated for column-first layout.
    
    Args:
        ws: Worksheet to modify
        num_chromosomes: Number of chromosomes per well
    """
    logger = logging.getLogger("ddQuint")
    logger.debug("Applying cell merges")
    
    # Merge cells in header row (1-12 across the top)
    for row_idx in range(1, 13):
        cell_col = (row_idx - 1) * 3 + 2
        ws.merge_cells(start_row=1, start_column=cell_col, end_row=1, end_column=cell_col + 2)
        logger.debug(f"Merged header for row {row_idx}")
    
    # Each well takes num_chromosomes+1 rows now
    well_height = num_chromosomes + 1
    
    # Merge column labels (A-H down the left side)
    for col_idx in range(len(COL_LABELS)):
        start_row = col_idx * well_height + 3
        ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row+well_height-1, end_column=1)
        logger.debug(f"Merged column label for column {COL_LABELS[col_idx]}")
    
    # Merge well name cells
    for col_idx in range(len(COL_LABELS)):
        for row_idx in range(len(ROW_LABELS)):
            start_row = col_idx * well_height + 3
            start_col = row_idx * 3 + 2
            
            # Merge the name cell (first row of well)
            ws.merge_cells(start_row=start_row, start_column=start_col, end_row=start_row, end_column=start_col+2)
            logger.debug(f"Merged name cell for well {COL_LABELS[col_idx]}{ROW_LABELS[row_idx]}")

def apply_formatting(ws, num_chromosomes):
    """
    Apply formatting to the entire worksheet with proper borders.
    
    Args:
        ws: Worksheet to modify
        num_chromosomes: Number of chromosomes per well
    """
    logger = logging.getLogger("ddQuint")
    logger.debug("Applying formatting")
    
    # Get maximum row and column in use
    well_height = num_chromosomes + 1
    max_row = 8 * well_height + 2  # 8 columns of wells (A-H), each with well_height rows
    max_col = 37  # 12 wells × 3 columns each + 1 for column labels
    
    logger.debug(f"Worksheet dimensions: {max_row}x{max_col}")
    
    # First pass: apply thin borders to all cells
    for row in range(1, max_row + 1):
        for col in range(1, max_col + 1):
            cell = ws.cell(row=row, column=col)
            cell.border = thin_border
    
    # Second pass: apply thick borders for plate boundaries
    apply_plate_boundaries(ws, num_chromosomes)
    
    # Set column widths
    ws.column_dimensions['A'].width = 3  # Column labels
    logger.debug("Set column A width to 3")
    
    # Each well takes 3 columns
    for i in range(1, 37):  # 12 wells × 3 columns each = 36 columns
        col_letter = get_column_letter(i+1)  # +1 because we start at column B
        if i % 3 == 1:  # First column of each well (chromosome name)
            ws.column_dimensions[col_letter].width = 5
        else:  # Data columns
            ws.column_dimensions[col_letter].width = 6
        logger.debug(f"Set column {col_letter} width to {5 if i % 3 == 1 else 6}")
    
    # Freeze the header rows and first column
    ws.freeze_panes = ws.cell(row=3, column=2)
    logger.debug("Set freeze panes at row 3, column 2")

def apply_plate_boundaries(ws, num_chromosomes):
    """
    Apply thick borders around each well and at the plate boundaries.
    Updated for column-first layout.
    
    Args:
        ws: Worksheet to modify
        num_chromosomes: Number of chromosomes per well
    """
    logger = logging.getLogger("ddQuint")
    logger.debug("Applying plate boundaries")
    
    well_height = num_chromosomes + 1
    
    # For each column of wells (A-H) - now these are vertical divisions
    for col_idx, col_label in enumerate(COL_LABELS):
        # Start row for this plate column (each well takes well_height rows)
        start_row = col_idx * well_height + 3
        end_row = start_row + well_height - 1  # End row for this plate column
        
        # For each row of wells (1-12) - now these are horizontal divisions
        for row_idx, row_label in enumerate(ROW_LABELS):
            # Start and end columns for this well (each well is 3 columns wide)
            start_col = row_idx * 3 + 2
            end_col = start_col + 2
            
            # Apply appropriate borders to each cell in this well
            for r in range(start_row, end_row + 1):
                for c in range(start_col, end_col + 1):
                    # Get existing cell and its current border
                    cell = ws.cell(row=r, column=c)
                    
                    # Create a new border with appropriate sides
                    left_side = thick if c == start_col else thin
                    right_side = thick if c == end_col else thin
                    top_side = thick if r == start_row else thin
                    bottom_side = thick if r == end_row else thin
                    
                    # Apply the new border
                    cell.border = Border(
                        left=left_side,
                        right=right_side,
                        top=top_side,
                        bottom=bottom_side
                    )
    
    logger.debug("Finished applying plate boundaries")