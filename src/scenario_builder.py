"""
Scenario Builder Module
Writes LLM-generated Gherkin scenarios to output files.
"""

import os
from pathlib import Path
from datetime import datetime


class ScenarioBuilder:
    """Writes Gherkin scenarios to feature files."""
    
    def __init__(self, output_dir: str = "src/output"):
        """
        Initialize the scenario builder.
        
        Args:
            output_dir: Directory to write feature files (default: src/output)
        """
        self.output_dir = Path(output_dir)
    
    def write_feature_file(self, content: str, filename: str = "generated.feature") -> str:
        """
        Write Gherkin content to a feature file.
        
        Args:
            content: Gherkin scenario content
            filename: Output filename (default: generated.feature)
            
        Returns:
            Full path to the written file
            
        Raises:
            Exception: If file writing fails
        """
        try:
            # Ensure output directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Build full file path
            file_path = self.output_dir / filename
            
            # Add header comment with generation timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            header = f"# Auto-generated Gherkin scenarios\n# Generated: {timestamp}\n\n"
            full_content = header + content
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            print(f"\n✓ Wrote Gherkin scenarios to: {file_path}")
            print(f"  File size: {len(full_content)} characters")
            
            return str(file_path)
            
        except Exception as e:
            raise Exception(f"Failed to write feature file: {str(e)}")
    
    def write_feature_with_timestamp(self, content: str, base_name: str = "generated") -> str:
        """
        Write feature file with timestamp in filename.
        
        Args:
            content: Gherkin scenario content
            base_name: Base name for file (default: generated)
            
        Returns:
            Full path to the written file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{base_name}_{timestamp}.feature"
        return self.write_feature_file(content, filename)


def write_scenarios(content: str, output_dir: str = "src/output", 
                   filename: str = "generated.feature") -> str:
    """
    Convenience function to write Gherkin scenarios.
    
    Args:
        content: Gherkin scenario content
        output_dir: Directory to write to (default: src/output)
        filename: Output filename (default: generated.feature)
        
    Returns:
        Full path to the written file
    """
    builder = ScenarioBuilder(output_dir=output_dir)
    return builder.write_feature_file(content, filename)

