# ddQuint Coding Standards

## Logging Standards

### Logger Initialization
- **Use module-level loggers only**: `logger = logging.getLogger(__name__)` at module top
- **Remove class-level loggers**: No `self.logger` or class attributes like `logger = logging.getLogger("ddQuint.module_name")`
- **Remove hardcoded names**: Replace `"ddQuint.module_name"` with `__name__`

### Error Logging Patterns
```python
# Standard error logging with context
logger.error(f"Operation failed during {operation_name}: {context}")
logger.debug(f"Error details: {str(e)}", exc_info=True)

# Before raising custom exceptions
logger.error(error_msg)
raise CustomException(error_msg) from e

# For warnings about recoverable issues
logger.warning(f"Issue detected but continuing: {details}")
```

### Debug Message Structure
```python
# Debug sections for major operations
logger.debug("=== SECTION NAME DEBUG ===")
# ... debug content ...
logger.debug("=== END SECTION NAME DEBUG ===")

# Consistent formatting with relevant data
logger.debug(f"Processing {count} wells with param={value}")
logger.debug(f"Results: success={success_count}, failed={fail_count}")
```

### Performance Considerations
```python
# Guard expensive debug operations
if logger.isEnabledFor(logging.DEBUG):
    expensive_debug_info = generate_complex_debug_data()
    logger.debug(f"Complex analysis: {expensive_debug_info}")

# Avoid logging in tight loops unless critical
```

### What NOT to Change
- **Never modify existing `.info()` calls**
- **Don't add new `.info()` calls** 
- **Don't remove existing `.info()` calls**
- **Don't change existing progress reporting**

## Docstring Standards

### Function/Method Docstrings
```python
def analyze_droplets(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze droplet data using enhanced density-based clustering.
    
    Performs HDBSCAN clustering on droplet amplitude data and calculates
    copy numbers for each chromosome target. Includes buffer zone and
    aneuploidy detection.
    
    Args:
        df: DataFrame containing Ch1Amplitude and Ch2Amplitude columns
        
    Returns:
        Dictionary containing clustering results, copy numbers, and aneuploidy status
        
    Raises:
        ValueError: If required columns are missing from DataFrame
        ClusteringError: If clustering fails or insufficient data points
        ConfigError: If configuration parameters are invalid
        
    Example:
        >>> df = pd.DataFrame({'Ch1Amplitude': [800, 900], 'Ch2Amplitude': [700, 800]})
        >>> results = analyze_droplets(df)
        >>> results['has_aneuploidy']
        False
    """
```

### Class Docstrings
```python
class Config:
    """
    Central configuration settings for the ddQuint pipeline with singleton pattern.
    
    This class provides configuration management for clustering parameters,
    visualization settings, copy number thresholds, and file management.
    Implements singleton pattern to ensure consistent settings across modules.
    
    Attributes:
        DEBUG_MODE: Enable debug logging mode
        EXPECTED_CENTROIDS: Target centroids for clustering
        HDBSCAN_MIN_CLUSTER_SIZE: Minimum cluster size for HDBSCAN
        
    Example:
        >>> config = Config.get_instance()
        >>> config.DEBUG_MODE = True
        >>> chroms = config.get_chromosome_keys()
    """
```

### Module Docstrings
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clustering module for ddQuint with dynamic chromosome support and buffer zone detection.

Contains functionality for:
1. HDBSCAN-based droplet clustering
2. Copy number calculation and normalization
3. Aneuploidy and buffer zone detection
4. Target assignment based on expected centroids

This module integrates with the broader ddQuint pipeline to provide
robust clustering capabilities for digital droplet PCR analysis.
"""
```

## Error Handling Standards

### Custom Exception Usage
```python
# Use specific exception types
raise ClusteringError(f"Insufficient data points for clustering: {len(df)} < {min_points}")
raise ConfigError(f"Invalid chromosome configuration: {chrom_name}")
raise FileProcessingError(f"CSV file processing failed: {filename}")

# Chain exceptions to preserve context
try:
    risky_operation()
except ValueError as e:
    error_msg = f"Data validation failed for well {well_id}"
    logger.error(error_msg)
    raise ClusteringError(error_msg) from e
```

### Error Context Requirements
- **Always include what was being attempted**: "Failed to process well A01"
- **Include relevant identifiers**: well IDs, file names, chromosome names
- **Provide actionable information**: what the user could check or fix
- **Log before raising**: ensure errors are captured even if exceptions are caught upstream

### Exception Documentation
```python
def process_csv_file(file_path: str, graphs_dir: str) -> Optional[Dict[str, Any]]:
    """
    Process a single CSV file and return the results.
    
    Args:
        file_path: Path to the CSV file
        graphs_dir: Directory to save graphs
        
    Returns:
        Results dictionary or None if processing failed
        
    Raises:
        FileProcessingError: If CSV file cannot be read or parsed
        ClusteringError: If droplet clustering fails
        ConfigError: If configuration parameters are invalid
    """
```

## ddQuint-Specific Standards

### Well ID Handling
```python
# Always validate well IDs
def process_well(well_id: str) -> Dict[str, Any]:
    """Process data for a single well."""
    if not is_valid_well(well_id):
        error_msg = f"Invalid well identifier: {well_id}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.debug(f"Processing well {well_id}")
    # ... processing logic
```

### Copy Number State Classification
```python
# Use Config methods for consistent classification
def classify_chromosome_state(chrom_name: str, copy_number: float) -> str:
    """
    Classify chromosome copy number state.
    
    Args:
        chrom_name: Chromosome identifier (e.g., 'Chrom1')
        copy_number: Calculated copy number value
        
    Returns:
        Classification: 'euploid', 'aneuploidy', or 'buffer_zone'
        
    Raises:
        ConfigError: If chromosome not found in configuration
    """
    config = Config.get_instance()
    
    if chrom_name not in config.EXPECTED_COPY_NUMBERS:
        error_msg = f"Unknown chromosome: {chrom_name}"
        logger.error(error_msg)
        raise ConfigError(error_msg)
    
    state = config.classify_copy_number_state(chrom_name, copy_number)
    logger.debug(f"{chrom_name} classified as {state}: {copy_number:.3f}")
    
    return state
```

### DataFrame Handling
```python
# Always create copies to avoid SettingWithCopyWarning
def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Process droplet amplitude data."""
    # Make explicit copy to avoid warnings
    df_clean = df.copy()
    
    # Check for required columns
    required_cols = ['Ch1Amplitude', 'Ch2Amplitude']
    missing_cols = [col for col in required_cols if col not in df_clean.columns]
    
    if missing_cols:
        error_msg = f"Missing required columns: {missing_cols}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Filter NaN values
    df_filtered = df_clean[required_cols].dropna()
    logger.debug(f"Filtered data: {len(df_filtered)} droplets from {len(df_clean)}")
    
    return df_filtered
```

## Migration Checklist

### Logging Updates
- [ ] Replace hardcoded logger names with `logger = logging.getLogger(__name__)`
- [ ] Remove class-level logger attributes
- [ ] Add context to all error messages (well IDs, file names, etc.)
- [ ] Add `exc_info=True` to debug logging for exceptions
- [ ] Standardize debug section formatting
- [ ] Guard expensive debug operations
- [ ] Preserve all existing `.info()` calls

### Docstring Updates  
- [ ] Add missing function/method docstrings
- [ ] Include all parameters in Args section with types
- [ ] Document return values with types and structure
- [ ] List all possible exceptions in Raises section
- [ ] Add usage examples for complex functions
- [ ] Update class docstrings with attributes and examples

### Error Handling Updates
- [ ] Use specific custom exception types (ClusteringError, ConfigError, etc.)
- [ ] Chain exceptions with `from e` 
- [ ] Log errors before raising
- [ ] Include relevant context (well IDs, chromosome names, file paths)
- [ ] Document all exceptions in docstrings

### ddQuint-Specific Updates
- [ ] Validate well IDs using `is_valid_well()`
- [ ] Use Config methods for copy number classification
- [ ] Create explicit DataFrame copies with `.copy()`
- [ ] Handle missing columns gracefully
- [ ] Use consistent chromosome naming conventions

## Example Conversion

### Before
```python
class FileProcessor:
    logger = logging.getLogger("ddQuint.file_processor")
    
    def process_csv(self, file_path):
        try:
            df = pd.read_csv(file_path)
            return self.analyze(df)
        except Exception as e:
            self.logger.error("CSV Error")
            return None
```

### After
```python
logger = logging.getLogger(__name__)

class FileProcessor:
    """Handles CSV file processing for ddQuint analysis."""
    
    def process_csv(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Process a CSV file containing droplet amplitude data.
        
        Args:
            file_path: Path to the CSV file to process
            
        Returns:
            Dictionary with analysis results, or None if processing failed
            
        Raises:
            FileProcessingError: If CSV file cannot be read or parsed
            ValueError: If required columns are missing
        """
        if not os.path.exists(file_path):
            error_msg = f"CSV file not found: {file_path}"
            logger.error(error_msg)
            raise FileProcessingError(error_msg)
            
        try:
            # Find header row and load data
            header_row = find_header_row(file_path)
            if header_row is None:
                error_msg = f"Could not find header row in {file_path}"
                logger.error(error_msg)
                raise FileProcessingError(error_msg)
                
            df = pd.read_csv(file_path, skiprows=header_row)
            logger.debug(f"Loaded CSV with {len(df)} rows from {file_path}")
            
            return self.analyze(df)
            
        except Exception as e:
            error_msg = f"CSV processing failed for {os.path.basename(file_path)}: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Error details: {str(e)}", exc_info=True)
            raise FileProcessingError(error_msg) from e
```

## Configuration Integration

### Using Config Singleton
```python
def setup_analysis_parameters():
    """Configure analysis parameters from Config singleton."""
    config = Config.get_instance()
    
    # Get clustering parameters
    hdbscan_params = config.get_hdbscan_params()
    logger.debug(f"HDBSCAN parameters: {hdbscan_params}")
    
    # Get chromosome configuration
    chromosome_keys = config.get_chromosome_keys()
    logger.debug(f"Active chromosomes: {chromosome_keys}")
    
    # Get visualization settings
    colors = config.TARGET_COLORS
    axis_limits = config.get_axis_limits()
    
    return {
        'clustering': hdbscan_params,
        'chromosomes': chromosome_keys,
        'visualization': {'colors': colors, 'limits': axis_limits}
    }
```

### Buffer Zone Handling
```python
def detect_buffer_zones(copy_numbers: Dict[str, float]) -> Tuple[bool, Dict[str, str]]:
    """
    Detect buffer zone samples based on copy number states.
    
    Buffer zones are samples where copy numbers fall between euploid
    and aneuploidy ranges, indicating uncertain classification.
    
    Args:
        copy_numbers: Dictionary of chromosome copy numbers
        
    Returns:
        Tuple of (has_buffer_zone, chromosome_states)
    """
    config = Config.get_instance()
    chromosome_states = {}
    has_buffer_zone = False
    
    for chrom_name, copy_number in copy_numbers.items():
        if chrom_name.startswith('Chrom'):
            state = config.classify_copy_number_state(chrom_name, copy_number)
            chromosome_states[chrom_name] = state
            
            if state == 'buffer_zone':
                has_buffer_zone = True
                logger.debug(f"{chrom_name} detected as buffer zone: {copy_number:.3f}")
    
    return has_buffer_zone, chromosome_states
```