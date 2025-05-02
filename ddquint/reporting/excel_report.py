"""
Excel report generation module for ddQuint
Creates a detailed Excel report with copy number results
"""

import os
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Border, Side, Alignment, Font
from openpyxl.utils import get_column_letter

# Define plate layout constants for sorting
ROW_LABELS = list('ABCDEFGH')
COL_LABELS = [str(i).zfill(2) for i in range(1, 13)]  # Format as "01", "02", etc.

def create_excel_report(results, output_path):
    """
    Create an Excel report with all analysis results.
    
    Args:
        results (list): List of result dictionaries for each well
        output_path (str): Path to save the Excel report
        
    Returns:
        str: Path to the saved Excel report
    """
    print(f"Creating Excel report: {output_path}")
    
    # Create a new workbook and activate the first sheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Plate Results"
    
    # Define column headers
    headers = [
        "Well", "Sample Name", "Status", 
        "Chrom1", "Chrom2", "Chrom3", "Chrom4", "Chrom5",
        "Negative", "Total Droplets", "Notes"
    ]
    
    # Set column widths for better readability
    ws.column_dimensions['A'].width = 6       # Well
    ws.column_dimensions['B'].width = 30      # Sample Name
    ws.column_dimensions['C'].width = 12      # Status
    for col in range(4, 9):                   # Chrom1-5
        ws.column_dimensions[get_column_letter(col)].width = 10
    ws.column_dimensions['I'].width = 10      # Negative
    ws.column_dimensions['J'].width = 14      # Total Droplets
    ws.column_dimensions['K'].width = 30      # Notes
    
    # Define styles
    header_font = Font(bold=True)
    centered = Alignment(horizontal='center', vertical='center')
    light_fill = PatternFill(start_color="E6E6E6", end_color="E6E6E6", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Add headers
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.font = header_font
        cell.alignment = centered
        cell.border = thin_border
        cell.fill = light_fill
    
    # Create a mapping to sort wells by position
    well_order = {
        f"{row}{col}": (row_idx, col_idx) 
        for row_idx, row in enumerate(ROW_LABELS) 
        for col_idx, col in enumerate(COL_LABELS)
    }
    
    # Filter out results with no well coordinate
    valid_results = [r for r in results if r.get('well') is not None]
    print(f"- Including {len(valid_results)} samples in report")
    
    # Sort results by well coordinate
    sorted_results = sorted(
        valid_results,
        key=lambda r: well_order.get(r['well'], (float('inf'), float('inf')))
    )
    
    # Add data rows
    for i, result in enumerate(sorted_results):
        row_idx = i + 2  # Start from row 2 (after headers)
        
        # Extract data from result
        well = result.get('well', '')
        filename = result.get('filename', 'Unknown')
        sample_name = os.path.splitext(filename)[0] if filename else 'Unknown'
        
        # Set status based on outlier detection
        status = "REVIEW" if result.get('has_outlier', False) else "PASS"
        if result.get('has_outlier', False):
            print(f"- Well {well} ({sample_name}) marked for REVIEW due to potential abnormality")
        
        # Get counts
        counts = result.get('counts', {})
        ordered_labels = ['Negative', 'Chrom1', 'Chrom2', 'Chrom3', 'Chrom4', 'Chrom5', 'Unknown']
        negative_count = counts.get('Negative', 0)
        total_droplets = sum(counts.get(target, 0) for target in ordered_labels)
        
        # Get copy numbers
        copy_numbers = result.get('copy_numbers', {})
        
        # Fill in the row
        row_data = [
            well,                                      # Well
            sample_name,                               # Sample Name
            status                                     # Status
        ]
        
        # Add copy numbers for Chrom1-5 (or 'N/A' if not available)
        for chrom in ['Chrom1', 'Chrom2', 'Chrom3', 'Chrom4', 'Chrom5']:
            value = copy_numbers.get(chrom, np.nan)
            if np.isnan(value):
                row_data.append('N/A')
            else:
                row_data.append(f"{value:.2f}")
        
        # Add negative count and total droplets
        row_data.extend([
            negative_count,                            # Negative
            total_droplets,                            # Total Droplets
            "Potential chromosomal abnormality detected" if result.get('has_outlier', False) else ""  # Notes
        ])
        
        # Write the data to the worksheet
        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col)
            cell.value = value
            cell.border = thin_border
            
            # Center align numeric columns
            if 3 < col < 11:  # Chrom1-5, Negative, Total Droplets
                cell.alignment = Alignment(horizontal='center')
            
            # Highlight rows with outliers
            if status == "REVIEW":
                cell.fill = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
    
    # Save the workbook
    try:
        wb.save(output_path)
        print(f"Excel report saved successfully to {output_path}")
        return output_path
    except Exception as e:
        print(f"Error saving Excel report: {str(e)}")
        return None