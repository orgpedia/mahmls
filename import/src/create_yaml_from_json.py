#!/usr/bin/env python3
import json
import yaml
from pathlib import Path
from collections import defaultdict

# Custom YAML dumper to add spacing between list items
class SpacedDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)

def main():
    # Path to the JSON file
    json_file_path = Path('/Users/mukund/orgpedia/mahmls/import/documents/documents.json')
    
    # Read the JSON file
    documents = json.loads(json_file_path.read_text(encoding='utf-8'))
    
    # Group documents by directory
    dir_to_docs = defaultdict(list)
    
    for doc in documents:
        repo_path = doc['repo_path']
        # Extract directory from repo_path
        directory = str(Path(repo_path).parent)
        dir_to_docs[directory].append(doc)
    
    # Create YAML files in each directory
    for directory, docs in dir_to_docs.items():
        # Create the full path - remove the first character to make it relative
        relative_dir = directory[1:]  # Remove the first '/' character
        
        # Create directory if it doesn't exist
        dir_path = Path('/Users/mukund/orgpedia/mahmls') / relative_dir
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Path for the YAML file
        yaml_path = dir_path / 'documents.yaml'
        
        # Write the YAML file with improved formatting
        yaml_content = yaml.dump(
            docs, 
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
            
        yaml_path.write_text(yaml_content, encoding='utf-8')
        
        print(f"Created YAML file at: {yaml_path}")

if __name__ == "__main__":
    main()
