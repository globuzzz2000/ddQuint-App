#!/usr/bin/env python3
"""
ddQuint Well Regeneration Script

Processes a single CSV file with custom parameters for well regeneration.
"""

import sys
import os
import json
import argparse

def regenerate_well(csv_path, output_dir, parameters_file=None):
    """
    Regenerate a single well with optional custom parameters.
    
    Args:
        csv_path: Path to the CSV file to process
        output_dir: Output directory for the plot
        parameters_file: Optional JSON file with custom parameters
        
    Returns:
        Processing result dictionary
    """
    try:
        # Import ddQuint modules
        from ddquint.config import Config
        from ddquint.utils.parameter_editor import load_parameters_if_exist
        from ddquint.core.file_processor import process_csv_file
        from ddquint.utils import get_sample_names
        
        # Initialize config
        config = Config.get_instance()
        load_parameters_if_exist(Config)
        
        # Load custom parameters if provided
        if parameters_file and os.path.exists(parameters_file):
            with open(parameters_file, 'r') as f:
                custom_params = json.load(f)
            
            # Apply custom parameters to config
            for key, value in custom_params.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                    print(f'Applied parameter: {key} = {value}')
        
        config.finalize_colors()
        
        # Get sample names from the folder containing the CSV
        folder_path = os.path.dirname(csv_path)
        sample_names = get_sample_names(folder_path)
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Process the single CSV file
        result = process_csv_file(csv_path, output_dir, sample_names, verbose=True)
        
        if result:
            # Extract well name from CSV filename
            well_name = os.path.basename(csv_path).split('_')[-2]  # Get part before '_Amplitude.csv'
            
            # Look for generated plot
            plot_path = os.path.join(output_dir, f'{well_name}.png')
            
            if os.path.exists(plot_path):
                print(f'PLOT_CREATED:{plot_path}')
                
                # Create serializable result
                serializable_result = {
                    'well': well_name,
                    'status': 'regenerated',
                    'plot_path': plot_path
                }
                
                # Add basic analysis data
                if isinstance(result, dict):
                    for key, value in result.items():
                        if isinstance(value, (str, int, float, bool, list)):
                            serializable_result[key] = value
                
                print(f'UPDATED_RESULT:{json.dumps(serializable_result)}')
                return serializable_result
            else:
                print('NO_PLOT_GENERATED')
                return None
        else:
            print('PROCESSING_FAILED')
            return None
            
    except Exception as e:
        print(f'ERROR: {str(e)}')
        import traceback
        traceback.print_exc()
        return None

def main():
    parser = argparse.ArgumentParser(description='Regenerate a single well with custom parameters')
    parser.add_argument('csv_path', help='Path to CSV file to process')
    parser.add_argument('output_dir', help='Output directory for plots')
    parser.add_argument('--parameters', help='JSON file with custom parameters')
    
    args = parser.parse_args()
    
    result = regenerate_well(args.csv_path, args.output_dir, args.parameters)
    if result:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()