#!/usr/bin/env python3
"""
Script to merge consolidated_todos.json into documents.json and create soft links.

This script:
1. Reads consolidated_todos.json
2. Creates soft links in import/documents for each file
3. Merges the entries into documents.json
"""

import json
import os
import sys
from pathlib import Path
import datetime


def json_serializer(obj):
    """Custom JSON serializer to handle date objects."""
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def create_soft_link(source_path, target_dir, target_name):
    """Create a soft link from source to target."""
    # Ensure the source file exists

    assert target_dir.exists()
    os.chdir(target_dir)

    if not source_path.exists():
        print(f"Warning: Source file does not exist: {source_path}")
        return False

    target_name = Path(target_name)
    
    # Create the soft link if it doesn't already exist
    if not target_name.exists():
        try:
            target_name.symlink_to(source_path)
            print(f"Created soft link: {target_name} -> {source_path}")
            return True
        except OSError as e:
            print(f"Error creating soft link: {e}")
            return False
    else:
        print(f"Soft link already exists: {target_name}")
        return True


def merge_and_link(todos_file, documents_file, base_dir):
    """
    Merge todos into documents and create soft links.
    
    Args:
        todos_file: Path to consolidated_todos.json
        documents_file: Path to documents.json
        base_dir: Base directory for the project
    """
    # Read the consolidated todos
    with todos_file.open('r', encoding='utf-8') as f:
        todos = json.load(f)
    
    # Read the existing documents
    with documents_file.open('r', encoding='utf-8') as f:
        documents = json.load(f)
    
    # Create a set of existing document names to avoid duplicates
    existing_names = {doc.get('name') for doc in documents}
    
    # Process each todo item
    added_count = 0
    linked_count = 0

    target_dir = base_dir / 'import' / 'documents'
    
    for todo in todos:
        # Skip if this document is already in documents.json
        if todo.get('name') in existing_names:
            print(f"Skipping duplicate document: {todo.get('name')}")
            continue
        
        # Fix repo_path if needed
        repo_path = todo.get('repo_path', '')
        assert repo_path.startswith('/import')
        repo_path = repo_path[1:]  # Remove leading slash

        # Create soft link
        source_path = Path('..') / '..' / repo_path
        target_name = todo.get('name')

        if create_soft_link(source_path, target_dir, target_name):
            linked_count += 1
            documents.append(todo)
            added_count += 1
        existing_names.add(todo.get('name'))
    
    # Write the updated documents back to the file
    with documents_file.open('w', encoding='utf-8') as f:
        json.dump(documents, f, indent=2, default=json_serializer)
       
    print(f"Added {added_count} documents to {documents_file}")
    print(f"Created {linked_count} soft links in import/documents")


def main():
    """Main function to run the script."""
    if len(sys.argv) < 2:
        print("Usage: python merge_and_link.py [consolidated_todos.json]")
        print("Default: consolidated_todos.json")
        todos_file = "consolidated_todos.json"
    else:
        todos_file = sys.argv[1]
    
    # Get the base directory
    base_dir = Path(__file__).parent.absolute()
    
    # Set paths
    todos_path = base_dir / todos_file
    documents_path = base_dir / "import" / "documents" / "documents.json"
    
    # Check if files exist
    if not todos_path.exists():
        print(f"Error: {todos_path} does not exist")
        return 1
    
    if not documents_path.exists():
        print(f"Error: {documents_path} does not exist")
        return 1
    
    # Run the merge and link process
    merge_and_link(todos_path, documents_path, base_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
