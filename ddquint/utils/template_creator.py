#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plate template creation module for ddQuint.

Generates a ddPCR plate template CSV file compatible with QX Manager
from a simple list of sample names provided in a CSV or Excel file.
"""

import os
import pandas as pd
import logging
import re
import datetime
import csv
from send2trash import send2trash
from ..config import FileProcessingError

logger = logging.getLogger(__name__)

def create_template_from_file(input_file_path):
    """
    Main function to process an input file and generate the filled template.

    Args:
        input_file_path (str): Path to the input file (CSV or Excel).

    Returns:
        str: Path to the generated output CSV file.

    Raises:
        FileProcessingError: If the input file cannot be read or processed.
        ValueError: If the file format is unsupported.
    """
    logger.debug(f"Starting template creation from file: {input_file_path}")
    try:
        df = _read_input_file(input_file_path)
    except Exception as e:
        raise FileProcessingError(f"Failed to read input file: {e}", filename=input_file_path) from e

    total_rows = len(df)
    if total_rows == 0:
        raise ValueError("Input file is empty or contains no sample data.")

    logger.info(f"Processing {total_rows} samples from {os.path.basename(input_file_path)}.")

    # Generate output filename
    input_dir = os.path.dirname(input_file_path)
    name_without_ext = os.path.splitext(os.path.basename(input_file_path))[0]
    output_file_path = os.path.join(input_dir, f"{name_without_ext}.csv")

    logger.debug(f"Output template will be saved to: {output_file_path}")

    # Create header and body
    output_lines = _create_template_header()
    _fill_plate_wells(output_lines, df)

    # Save the template file
    try:
        with open(output_file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(output_lines)
        logger.info(f"Template successfully saved to: {output_file_path}")
    except IOError as e:
        raise FileProcessingError(f"Failed to write output template file: {e}", filename=output_file_path) from e

    # Move the original input file to trash if processing was successful
    # and the number of samples is a multiple of 8 (a full column)
    if total_rows % 8 == 0:
        try:
            send2trash(input_file_path)
            logger.debug(f"Moved processed input file to trash: {input_file_path}")
        except Exception as e:
            logger.warning(f"Could not move input file to trash: {e}")
    else:
        logger.warning(
            f"Number of samples ({total_rows}) is not a multiple of 8. "
            f"Input file was not moved to trash."
        )
    return output_file_path

def _read_input_file(file_path):
    """
    Read CSV or Excel file and extract sample information.
    Handles files with or without headers.
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    logger.debug(f"Reading {file_extension} file to extract sample list.")

    if file_extension == '.csv':
        df = pd.read_csv(file_path, header=None, dtype=str).fillna('')
    elif file_extension in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path, header=None, dtype=str).fillna('')
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")

    # Check if the first row looks like a header
    first_row_str = ' '.join(df.iloc[0]).lower()
    if 'sample' in first_row_str or 'description' in first_row_str:
        logger.debug("Header row detected in input file.")
        df.columns = df.iloc[0]
        df = df.drop(df.index[0]).reset_index(drop=True)
    else:
        logger.debug("No header row detected. Assigning generic column names.")
        df.columns = [f"Sample description {i+1}" for i in range(len(df.columns))]

    return df

def _fill_plate_wells(output_lines, df):
    """Fills the 96 wells of the plate with sample data."""
    total_rows = len(df)
    for row_letter in 'ABCDEFGH':
        for col_num in range(1, 13):
            well_id = f"{row_letter}{col_num:02d}"
            # Column-major mapping: data_idx = (col-1) * 8 + (row_letter_index)
            data_idx = (col_num - 1) * 8 + (ord(row_letter) - ord('A'))

            if data_idx < total_rows:
                sample_data = df.iloc[data_idx]
                sample_desc_1 = sample_data.get('Sample description 1', sample_data.iloc[0] if len(sample_data) > 0 else "")
                additional_desc = [
                    sample_data.get('Sample description 2', sample_data.iloc[1] if len(sample_data) > 1 else ""),
                    sample_data.get('Sample description 3', sample_data.iloc[2] if len(sample_data) > 2 else ""),
                    sample_data.get('Sample description 4', sample_data.iloc[3] if len(sample_data) > 3 else "")
                ]
                control_type = _detect_control_type(sample_desc_1)
                output_lines.extend(
                    _get_template_rows_for_well(well_id, sample_desc_1, additional_desc, control_type)
                )
            else:
                output_lines.append(_get_empty_template_row(well_id))

def _create_template_header():
    """Create the header lines for the template file."""
    now = datetime.datetime.now()
    return [
        [
            "ddplate - DO NOT MODIFY THIS LINE", "Version=1",
            "ApplicationName=QX Manager Standard Edition", "ApplicationVersion=2.3.0.32",
            "ApplicationEdition=ResearchEmbedded", "User=\\QX User",
            f"CreatedDate={now.strftime('%m/%d/%Y %H:%M:%S')}", ""
        ],
        [""], ["PlateSize=GCR96"], ["PlateNotes="],
        [
            "Well", "Perform Droplet Reading", "ExperimentType", "Sample description 1",
            "Sample description 2", "Sample description 3", "Sample description 4",
            "SampleType", "SupermixName", "AssayType", "TargetName", "TargetType",
            "Signal Ch1", "Signal Ch2", "Reference Copies", "Well Notes", "Plot?",
            "RdqConversionFactor"
        ]
    ]

def _get_template_rows_for_well(well_id, sample_desc, additional_desc, control_type):
    """Get the three standard data rows for a single well."""
    base_row = [
        well_id, "Yes", "Copy Number Variation (CNV)", sample_desc,
        *additional_desc, control_type, "ddPCR Supermix for Probes (No dUTP)",
        "Probe Mix Triplex"
    ]
    common_end = ["Unknown", "", "", "False", ""]

    row1 = base_row + ["chr1", "Unknown", "None", "HEX"] + common_end
    row2 = base_row + ["chr234", "Unknown", "FAM", "HEX"] + common_end
    row3 = base_row + ["chr5", "Unknown", "FAM", "None"] + common_end

    return [row1, row2, row3]

def _get_empty_template_row(well_id):
    """Get an empty template row for a well with no sample."""
    return [well_id, "No"] + [""] * 16

def _detect_control_type(sample_name):
    """Detect if a sample is a negative or positive control."""
    if not sample_name:
        return "Unknown"
    name_lower = str(sample_name).lower()
    if any(re.search(p, name_lower) for p in [r'neg\s*ctrl', r'negative', r'nc', r'blank']):
        return "NegCtrl"
    if any(re.search(p, name_lower) for p in [r'pos\s*ctrl', r'positive', r'pc']):
        return "PosCtrl"
    return "Unknown"