#!/usr/bin/env python3
"""
Script to create consolidated_todos.json from todo.yml files.

This script:
1. Finds all todo.yml files in import/websites/mls.org.in
2. Reads import/documents/documents.json
3. Identifies documents not in documents.json
4. Assigns unique names as mahmls-<num>.pdf
5. Outputs consolidated_todos.json
"""

import json
import sys
from pathlib import Path
import yaml
import datetime


def json_serializer(obj):
    """Custom JSON serializer to handle date objects."""
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def find_todo_files(base_dir):
    """Find all todo.yml files in the mls.org.in directory."""
    search_path = base_dir / 'websites' / 'mls.org.in'

    if not search_path.exists():
        print(f"Error: Directory does not exist: {search_path}")
        return []

    todo_files = list(search_path.rglob('todo.yml'))
    print(f"Found {len(todo_files)} todo.yml files")
    return todo_files


def load_todos_from_files(todo_files):
    """Load all todo entries from the yml files."""
    all_todos = []

    for todo_file in todo_files:
        try:
            with todo_file.open('r', encoding='utf-8') as f:
                todos = yaml.safe_load(f)

                if todos and isinstance(todos, list):
                    all_todos.extend(todos)
                    print(f"Loaded {len(todos)} entries from {todo_file}")
                elif todos:
                    print(f"Warning: Unexpected format in {todo_file}")
        except Exception as e:
            print(f"Error reading {todo_file}: {e}")

    print(f"\nTotal entries loaded: {len(all_todos)}")
    return all_todos


def load_existing_documents(documents_file):
    """Load existing documents from documents.json."""
    if not documents_file.exists():
        print(f"Warning: {documents_file} does not exist")
        return []

    try:
        with documents_file.open('r', encoding='utf-8') as f:
            documents = json.load(f)
            print(f"Loaded {len(documents)} existing documents from {documents_file}")
            return documents
    except Exception as e:
        print(f"Error reading {documents_file}: {e}")
        return []


def get_existing_repo_paths(documents):
    """Extract repo_paths from existing documents for comparison."""
    repo_paths = set()

    for doc in documents:
        repo_path = doc.get('repo_path', '')
        if repo_path:
            repo_paths.add(repo_path)

    return repo_paths


def find_next_number(documents):
    """Find the next available number for mahmls-<num>.pdf naming."""
    max_num = 0

    for doc in documents:
        name = doc.get('name', '')
        # Check if it matches mahmls-<num>.pdf pattern
        if name.startswith('mahmls-') and name.endswith('.pdf'):
            try:
                num_str = name[7:-4]  # Extract the number part
                num = int(num_str)
                max_num = max(max_num, num)
            except ValueError:
                continue

    return max_num + 1


def create_consolidated_todos(base_dir, output_file='consolidated_todos.json'):
    """
    Create consolidated todos from all todo.yml files.

    Args:
        base_dir: Base directory of the project
        output_file: Name of the output file
    """
    # Find all todo.yml files
    todo_files = find_todo_files(base_dir)

    if not todo_files:
        print("No todo.yml files found")
        return 1

    # Load all todos
    all_todos = load_todos_from_files(todo_files)

    # Load existing documents
    documents_file = base_dir / 'documents' / 'documents.json'
    existing_documents = load_existing_documents(documents_file)
    existing_repo_paths = get_existing_repo_paths(existing_documents)

    # Find the next available number
    next_num = find_next_number(existing_documents)

    # Filter out documents already in documents.json and assign names
    new_todos = []
    skipped_count = 0

    for todo in all_todos:
        repo_path = todo.get('repo_path', '')

        if '/Users/mukund/orgpedia/mahmls/import/' in repo_path:
            repo_path = repo_path.replace('/Users/mukund/orgpedia/mahmls/import/', '')

        # Skip if already exists
        if repo_path in existing_repo_paths:
            skipped_count += 1
            continue

        # Assign new name
        todo['name'] = f'mahmls-{next_num}.pdf'
        next_num += 1
        new_todos.append(todo)

    print(f"\nSkipped {skipped_count} documents already in documents.json")
    print(f"New documents to add: {len(new_todos)}")

    # Write consolidated todos to import directory
    output_path = base_dir / output_file

    with output_path.open('w', encoding='utf-8') as f:
        json.dump(new_todos, f, indent=2, ensure_ascii=False, default=json_serializer)

    print(f"\nWrote {len(new_todos)} entries to {output_path}")

    # Show first few assigned names as examples
    if new_todos:
        print("\nExample assigned names:")
        for todo in new_todos[:5]:
            print(f"  {todo['name']} -> {todo.get('repo_path', 'N/A')}")
        if len(new_todos) > 5:
            print(f"  ... and {len(new_todos) - 5} more")

    return 0


def main():
    """Main function to run the script."""
    # Get the base directory (go up two levels from this script)
    base_dir = Path(__file__).parent.parent.absolute()

    print(f"Base directory: {base_dir}")
    print()

    # Run the consolidation
    result = create_consolidated_todos(base_dir)
    return result


if __name__ == "__main__":
    sys.exit(main())
