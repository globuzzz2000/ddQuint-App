#!/usr/bin/env python3
"""
Single Well Regeneration Script for ddQuint Native App

This script processes a single CSV file with custom parameters.
It uses the same import pattern and execution flow as the main folder analysis.
"""

import sys
import os
import json
import tempfile

def main():
    if len(sys.argv) != 4:
        print("Usage: regenerate_single_well.py <csv_file> <well_name> <parameters_json>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    well_name = sys.argv[2] 
    parameters_json = sys.argv[3]
    
    try:
        # Add ddQuint to Python path
        ddquint_path = os.path.dirname(os.path.dirname(csv_file))
        while ddquint_path and not os.path.exists(os.path.join(ddquint_path, 'ddquint')):
            parent = os.path.dirname(ddquint_path)
            if parent == ddquint_path:  # Reached root
                break
            ddquint_path = parent
        
        if not os.path.exists(os.path.join(ddquint_path, 'ddquint')):
            # Fallback to common locations
            possible_paths = [
                '/Users/jakob/Applications/Git/ddQuint',
                os.path.expanduser('~/Applications/Git/ddQuint'),
                os.path.join(os.path.dirname(__file__), '..')
            ]
            ddquint_path = None
            for path in possible_paths:
                if os.path.exists(os.path.join(path, 'ddquint')):
                    ddquint_path = path
                    break
        
        if not ddquint_path:
            raise Exception("Cannot find ddQuint installation")
        
        sys.path.insert(0, ddquint_path)
        
        # Use exactly the same import pattern as main analysis
        from ddquint.config import Config
        from ddquint.utils.parameter_editor import load_parameters_if_exist
        from ddquint.core.file_processor import process_csv_file
        from ddquint.utils import get_sample_names
        
        # Initialize config exactly like main analysis
        config = Config.get_instance()
        load_parameters_if_exist(Config)
        
        # Load custom parameters
        if parameters_json and parameters_json != "null":
            try:
                custom_params = json.loads(parameters_json)
                for key, value in custom_params.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
                        print(f'Applied parameter: {key} = {value}')
            except json.JSONDecodeError as e:
                print(f'Warning: Could not parse parameters: {e}')
        
        config.finalize_colors()
        
        # Get sample names from folder (same as main analysis)
        folder_path = os.path.dirname(csv_file)
        sample_names = get_sample_names(folder_path)
        
        # Create output directory in temp
        output_dir = tempfile.mkdtemp(prefix='ddquint_regen_')
        
        print(f'Processing: {csv_file}')
        print(f'Output: {output_dir}')
        print(f'Well: {well_name}')
        
        # Process the single CSV file using the same method as main analysis
        result = process_csv_file(csv_file, output_dir, sample_names, verbose=True)
        
        if result:
            # Look for generated plot - try multiple naming patterns
            possible_names = [
                f'{well_name}.png',
                os.path.basename(csv_file).replace('.csv', '.png'),
                os.path.basename(csv_file).replace('_Amplitude.csv', '.png')
            ]
            
            plot_file = None
            for name in possible_names:
                candidate = os.path.join(output_dir, name)
                if os.path.exists(candidate):
                    plot_file = candidate
                    break
            
            if plot_file:
                print(f'PLOT_CREATED:{plot_file}')
                
                # Create simple result (avoid DataFrame serialization issues)
                simple_result = {
                    'well': well_name,
                    'status': 'regenerated',
                    'plot_path': plot_file
                }
                
                # Add basic data from result if it's a dict
                if isinstance(result, dict):
                    for key, value in result.items():
                        if key not in ['data', 'dataframe', 'df'] and isinstance(value, (str, int, float, bool)):
                            simple_result[key] = value
                
                print(f'UPDATED_RESULT:{json.dumps(simple_result)}')
                print('SUCCESS')
            else:
                # List what files were actually created
                files = os.listdir(output_dir) if os.path.exists(output_dir) else []
                print(f'NO_PLOT_FOUND. Files created: {files}')
                print('FAILED')
        else:
            print('PROCESSING_FAILED')
            print('FAILED')
            
    except Exception as e:
        print(f'ERROR: {str(e)}')
        import traceback
        traceback.print_exc()
        print('FAILED')
        sys.exit(1)

if __name__ == '__main__':
    main()