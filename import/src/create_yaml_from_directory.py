#!/usr/bin/env python3
import typer
import yaml
import json
import re
import sys
import urllib.parse
from pathlib import Path
from collections import defaultdict
from typing import Optional

# Custom YAML dumper to add spacing between list items
class SpacedDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)

def infer_metadata_from_path(file_path, house, doc_type, session, year, date_suffix):
    """
    Infer metadata from the directory structure and command line arguments
    """
    # Ensure repo_path starts with '/import/'
    rel_path = str(file_path)
    if not rel_path.startswith('/import/'):
        repo_path = f"/import/{rel_path}"
    else:
        repo_path = rel_path
    
    metadata = {
        "repo_path": repo_path,
        "name": file_path.name
    }
    
    # Try to infer house and doc_type from the path
    parts = file_path.parts
    
    # Common house values
    houses = ["Council", "Assembly"]
    for h in houses:
        if h in parts:
            metadata["house"] = h
            break
    else:
        metadata["house"] = house if house else "TBD"
    
    # Common document types
    doc_types = ["Proceedings", "UnstarredQuestions", "StarredQuestions", "Bills", "Reports"]
    for dt in doc_types:
        if dt in parts:
            metadata["doc_type"] = dt
            break
    else:
        metadata["doc_type"] = doc_type if doc_type else "TBD"
    
    # Add list_num attribute if doc_type is UnstarredQuestions
    if metadata["doc_type"] == "UnstarredQuestions":
        metadata["list_num"] = "TBD"
    
    # Use command line arguments for session and year
    metadata["session"] = session if session else "TBD"
    
    # Convert year to integer if possible, otherwise keep as "TBD"
    if year and year != "TBD":
        try:
            metadata["year"] = int(year)
        except ValueError:
            metadata["year"] = "TBD"
    else:
        metadata["year"] = "TBD"
    
    # Add date attribute using year and date_suffix
    if year and year != "TBD":
        metadata["date"] = f"{year}-{date_suffix}"
    else:
        metadata["date"] = f"TBD-{date_suffix}"
    
    # Add URL field based on directory structure starting at mls.org.in
    str_path = str(file_path)
    if "mls.org.in" in str_path:
        # Extract the path part starting from mls.org.in
        url_path = str_path.split("mls.org.in/", 1)[1] if "mls.org.in/" in str_path else ""
        
        # Split the path into components
        path_components = url_path.split("/")
        
        # Remove the first two subdirectories (e.g., Assembly/StarredQuestions) if they exist
        if len(path_components) > 2:
            path_components = path_components[2:]
        
        # Join the remaining components and URL encode them
        encoded_path = "/".join(urllib.parse.quote(component) for component in path_components)
        metadata["url"] = f"http://mls.org.in/{encoded_path}"
    else:
        metadata["url"] = "TBD"
    
    return metadata

def main(
    directory: Path = typer.Argument(
        Path("."), 
        help="Directory to scan for PDFs (default: current directory)"
    ),
    house: Optional[str] = typer.Option(
        None, 
        help="House value for all documents"
    ),
    doc_type: Optional[str] = typer.Option(
        None, 
        "--doc-type", 
        help="Document type for all documents"
    ),
    session: Optional[str] = typer.Option(
        None, 
        help="Session for all documents"
    ),
    year: Optional[str] = typer.Option(
        None, 
        help="Year for all documents"
    ),
    date_suffix: str = typer.Option(
        "MM-DD", 
        "--date-suffix",
        help="Date suffix to append to year (default: MM-DD)"
    )
):
    """
    Create documents.yaml file for PDFs in a directory.
    Outputs YAML to stdout.
    """
    # Convert to absolute path
    directory = directory.resolve()
    
    if not directory.exists() or not directory.is_dir():
        print(f"Error: {directory} is not a valid directory", file=sys.stderr)
        raise typer.Exit(code=1)
    
    # Find all PDF files in the directory (non-recursive)
    pdf_files = sorted(directory.glob('*.pdf'), key=lambda p: p.name)
    
    if not pdf_files:
        print(f"No PDF files found in {directory}", file=sys.stderr)
        raise typer.Exit(code=1)
    
    print(f"Found {len(pdf_files)} PDF files", file=sys.stderr)
    
    # Process each PDF file
    documents = []
    for pdf_file in pdf_files:
        # Get relative path from the base directory
        rel_path = pdf_file.relative_to(directory)
        
        # Infer metadata from the path and command line arguments
        metadata = infer_metadata_from_path(pdf_file, house, doc_type, session, year, date_suffix)
        
        documents.append(metadata)
        print(f"Processed: {rel_path}", file=sys.stderr)
    
    # Format YAML with spacing for readability
    yaml_content = yaml.dump(
        documents, 
        Dumper=SpacedDumper,
        default_flow_style=False, 
        allow_unicode=True,
        sort_keys=False,
        width=120,
        indent=2
    )
    
    # Add an extra newline between list items for better readability
    yaml_content = yaml_content.replace('- repo_path:', '\n- repo_path:')
    # Remove the extra newline at the beginning
    if yaml_content.startswith('\n'):
        yaml_content = yaml_content[1:]
    
    # Print to stdout
    print(yaml_content)
    
    # Print usage instructions for fields that couldn't be inferred
    missing_fields = set()
    for doc in documents:
        for field, value in doc.items():
            # Skip list_num field since it's intentionally set to TBD
            if field == "list_num":
                continue
                
            # Convert value to string for comparison if it's not already a string
            if not isinstance(value, str):
                str_value = str(value)
                if str_value == "TBD":
                    missing_fields.add(field)
            elif value == "TBD" or value.startswith("TBD-"):
                missing_fields.add(field)
    
    if missing_fields:
        print("\nSome fields couldn't be automatically inferred. You can provide them using command line options:", file=sys.stderr)
        for field in missing_fields:
            option_name = f"--{field.replace('_', '-')}" if '_' in field else f"--{field}"
            print(f"  {option_name} VALUE", file=sys.stderr)

if __name__ == "__main__":
    typer.run(main)
