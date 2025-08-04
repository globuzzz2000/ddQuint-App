"""
Utility modules for ddQuint
"""

from .file_io import (
    ensure_directory, 
    list_csv_files, 
    read_csv_with_header_detection
)
from .gui import select_directory, select_file, find_default_directory, mark_selection_complete, select_multiple_directories
from .well_utils import (
    extract_well_coordinate, 
    is_valid_well, 
    format_well_id, 
    get_all_wells
)
from .template_parser import (
    find_template_file,
    find_header_row,
    parse_template_file,
    get_sample_names
)

from .template_creator import (
    create_template_from_file
)

from .parameter_editor import (
    open_parameter_editor,
    load_parameters_if_exist,
    apply_parameters_to_config,
    parameters_exist,
    get_parameters_file_path,
    console_parameter_editor
)

__all__ = [
    # File I/O utilities
    'ensure_directory',
    'list_csv_files',
    'read_csv_with_header_detection',
    
    # GUI utilities
    'select_directory',
    'select_file',
    'find_default_directory',
    'mark_selection_complete',
    'select_multiple_directories',
    
    # Well utilities
    'extract_well_coordinate',
    'is_valid_well',
    'format_well_id',
    'get_all_wells',

    # Template utilities
    'find_template_file',
    'find_header_row',
    'parse_template_file',
    'get_sample_names',
    'create_template_from_file',

    # Parameter editor
    'open_parameter_editor',
    'load_parameters_if_exist',
    'apply_parameters_to_config',
    'parameters_exist',
    'get_parameters_file_path',
    'console_parameter_editor'
]