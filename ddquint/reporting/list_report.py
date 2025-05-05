"""
List report generation module for ddQuint with tabular format
"""

import os
import numpy as np
import traceback
import logging
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Border, Side, Alignment, Font
from openpyxl.utils import get_column_letter

from ..config.config import Config

def create_list_report(results, output_path):
    """
    Create a list-format Excel report with chromosome data in columns.
    
    Args:
        results (list): List of result dictionaries for each well
        output_path (str): Path to save the Excel report
        
    Returns:
        str: Path to the saved Excel report
    """
    logger = logging.getLogger("ddQuint")
    config = Config.get_instance()
    
    # Get the number of chromosomes from config
    chromosome_keys = config.get_chromosome_keys()
    num_chromosomes = len(chromosome_keys)
    
    logger.debug(f"Creating list report for {len(results)} results with {num_chromosomes} chromosomes")
    logger.debug(f"Output path: {output_path}")
    
    try:
        # Create a new workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "List Results"
        logger.debug("Created new workbook")
        
        # Sort results by well ID for consistent ordering
        sorted_results = sorted(results, key=lambda x: x.get('well', ''))
        
        # Set up headers with proper structure
        setup_headers(ws, chromosome_keys)
        
        # Fill in data for each well
        fill_well_data(ws, sorted_results, chromosome_keys, config)
        
        # Apply formatting
        apply_formatting(ws, len(sorted_results), chromosome_keys)
        
        # Save the workbook
        try:
            wb.save(output_path)
            logger.debug(f"List report saved successfully to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error saving list report: {str(e)}")
            logger.debug("Error details:", exc_info=True)
            return None
    except Exception as e:
        logger.error(f"Error creating list report: {str(e)}")
        logger.debug("Error details:", exc_info=True)
        return None


def setup_headers(ws, chromosome_keys):
    """
    Set up headers with proper merging and structure.
    """
    num_chromosomes = len(chromosome_keys)
    
    # Row 1: Main headers
    # Well (A1-A2 merged)
    ws.cell(row=1, column=1, value="Well")
    ws.cell(row=2, column=1, value="")
    
    # Sample (B1-B2 merged)
    ws.cell(row=1, column=2, value="Sample")
    ws.cell(row=2, column=2, value="")
    
    # Relative Copy Number section (C1 to C+num_chromosomes merged)
    rel_start = 3
    rel_end = 2 + num_chromosomes
    ws.cell(row=1, column=rel_start, value="Relative Copy Number")
    for i in range(rel_start, rel_end + 1):
        ws.cell(row=1, column=i + 1, value="")
    
    # Absolute Copy Number section (starts after Relative)
    abs_start = rel_end + 1
    abs_end = abs_start + num_chromosomes - 1
    ws.cell(row=1, column=abs_start, value="Absolute Copy Number")
    for i in range(abs_start, abs_end + 1):
        ws.cell(row=1, column=i + 1, value="")
    
    # Merge cells for headers
    ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=1)  # Well
    ws.merge_cells(start_row=1, start_column=2, end_row=2, end_column=2)  # Sample
    ws.merge_cells(start_row=1, start_column=rel_start, end_row=1, end_column=rel_end)  # Relative Copy Number
    ws.merge_cells(start_row=1, start_column=abs_start, end_row=1, end_column=abs_end)  # Absolute Copy Number
    
    # Row 2: Chromosome headers
    for i, chrom_key in enumerate(chromosome_keys):
        chrom_label = f"Chr{chrom_key.replace('Chrom', '')}"
        # Relative columns
        ws.cell(row=2, column=rel_start + i, value=chrom_label)
        # Absolute columns
        ws.cell(row=2, column=abs_start + i, value=chrom_label)
    
    # Apply formatting to headers
    for cell in ws[1]:
        if cell.value:
            cell.font = Font(bold=True, size=12)
            cell.alignment = Alignment(horizontal='center', vertical='center')
    
    for cell in ws[2]:
        if cell.value:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center', vertical='center')


def fill_well_data(ws, sorted_results, chromosome_keys, config):
    """
    Fill in data for each well with aneuploidy highlighting.
    """
    num_chromosomes = len(chromosome_keys)
    rel_start = 3
    abs_start = rel_start + num_chromosomes
    
    for row_idx, result in enumerate(sorted_results, start=3):
        well_id = result.get('well', '')
        
        # Well ID
        well_cell = ws.cell(row=row_idx, column=1, value=well_id)
        well_cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Sample name
        sample_name = result.get('sample_name', '')
        if not sample_name:
            filename = result.get('filename', '')
            sample_name = os.path.splitext(filename)[0] if filename else well_id
        
        sample_cell = ws.cell(row=row_idx, column=2, value=sample_name)
        sample_cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Get data for this well
        counts = result.get('counts', {})
        copy_numbers = result.get('copy_numbers', {})
        has_aneuploidy = result.get('has_aneuploidy', False)
        
        # Apply highlighting to Well and Sample cells if aneuploidy
        if has_aneuploidy:
            well_cell.fill = PatternFill(start_color="E6B8E6", end_color="E6B8E6", fill_type="solid")
            sample_cell.fill = PatternFill(start_color="E6B8E6", end_color="E6B8E6", fill_type="solid")
        
        # Fill in relative copy numbers
        for i, chrom_key in enumerate(chromosome_keys):
            cell = ws.cell(row=row_idx, column=rel_start + i)
            rel_count = copy_numbers.get(chrom_key)
            if rel_count is not None:
                cell.value = round(rel_count, 2)
                cell.number_format = '0.00'
            else:
                cell.value = ""
            cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Highlight aneuploidies
            if has_aneuploidy and rel_count is not None:
                if abs(rel_count - 1.0) > config.ANEUPLOIDY_DEVIATION_THRESHOLD:
                    cell.fill = PatternFill(start_color="D070D0", end_color="D070D0", fill_type="solid")
                else:
                    cell.fill = PatternFill(start_color="E6B8E6", end_color="E6B8E6", fill_type="solid")
        
        # Fill in absolute copy numbers
        for i, chrom_key in enumerate(chromosome_keys):
            cell = ws.cell(row=row_idx, column=abs_start + i)
            abs_count = counts.get(chrom_key, 0)
            cell.value = abs_count if abs_count > 0 else ""
            cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Highlight aneuploidies
            if has_aneuploidy:
                cell.fill = PatternFill(start_color="E6B8E6", end_color="E6B8E6", fill_type="solid")


def apply_formatting(ws, num_results, chromosome_keys):
    """
    Apply borders, column widths, and freeze panes.
    """
    num_chromosomes = len(chromosome_keys)
    rel_start = 3
    abs_start = rel_start + num_chromosomes
    max_col = abs_start + num_chromosomes - 1
    max_row = num_results + 2
    
    # Border styles
    thick = Side(style='thick')
    
    # Apply borders - only thick borders, no thin ones
    for row in range(1, max_row + 1):
        for col in range(1, max_col + 1):
            cell = ws.cell(row=row, column=col)
            
            # Start with no borders
            left_border = None
            right_border = None
            top_border = None
            bottom_border = None
            
            # Thick borders for table outline
            if row == 1:
                top_border = thick
            if row == max_row:
                bottom_border = thick
            if col == 1:
                left_border = thick
            if col == max_col:
                right_border = thick
            
            # Thick borders around Relative Copy Number section
            if col == rel_start and row >= 1:
                left_border = thick
            if col == rel_start + num_chromosomes - 1 and row >= 1:
                right_border = thick
                
            # Thick borders at the bottom of row 2 (header row)
            if row == 2:
                bottom_border = thick
                
            # Only apply border if at least one side has a style
            if any([left_border, right_border, top_border, bottom_border]):
                cell.border = Border(left=left_border, right=right_border, 
                                   top=top_border, bottom=bottom_border)
    
    # Set column widths
    ws.column_dimensions['A'].width = 8  # Well
    ws.column_dimensions['B'].width = 15  # Sample
    
    # Set widths for chromosome columns
    for col in range(rel_start, max_col + 1):
        ws.column_dimensions[get_column_letter(col)].width = 8
    
    # Freeze panes (freeze top 2 rows and first 2 columns)
    ws.freeze_panes = ws.cell(row=3, column=3)