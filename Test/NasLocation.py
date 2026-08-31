import os
import time
from datetime import datetime, timedelta
from pathlib import Path


def check_file_exists(file_path):
    """
    Check if a particular file exists at the given location.

    Args:
        file_path (str): Full path to the file including filename

    Returns:
        bool: True if file exists, False otherwise
    """
    try:
        return os.path.exists(file_path)
    except Exception as e:
        print(f"Error checking file existence: {e}")
        return False


def count_updated_files(folder_path, hours=24):
    """
    Count how many files in a folder have been updated within the specified hours.

    Args:
        folder_path (str): Path to the folder to check
        hours (int): Number of hours to look back (default: 24 hours)

    Returns:
        dict: Dictionary containing:
            - 'total_files': Total number of files in folder
            - 'updated_files_count': Number of files updated in the time period
            - 'updated_files': List of updated files with their modification time
    """
    try:
        if not os.path.isdir(folder_path):
            print(f"Folder does not exist: {folder_path}")
            return None

        current_time = time.time()
        time_threshold = current_time - (hours * 3600)  # Convert hours to seconds

        total_files = 0
        updated_files = []

        # Walk through the folder
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                total_files += 1
                file_path = os.path.join(root, file)

                try:
                    # Get file modification time
                    mod_time = os.path.getmtime(file_path)

                    # Check if file was modified within the time threshold
                    if mod_time > time_threshold:
                        mod_datetime = datetime.fromtimestamp(mod_time)
                        updated_files.append({
                            'file': file,
                            'path': file_path,
                            'modified_time': mod_datetime.strftime('%Y-%m-%d %H:%M:%S')
                        })
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")

        return {
            'total_files': total_files,
            'updated_files_count': len(updated_files),
            'updated_files': updated_files
        }

    except Exception as e:
        print(f"Error checking folder: {e}")
        return None


def check_file_and_folder_updates(file_path, hours=24):
    """
    Combined function to:
    1. Check if a particular file exists
    2. Count updated files two directories up from the file location

    Args:
        file_path (str): Full path to the file to check
        hours (int): Number of hours to look back for file updates

    Returns:
        dict: Combined results
    """
    file_exists = check_file_exists(file_path)
    # Go back two folders from the file location
    folder_path = os.path.dirname(os.path.dirname(file_path))
    folder_updates = count_updated_files(folder_path, hours) if file_exists else None

    return {
        'file_path': file_path,
        'file_exists': file_exists,
        'folder_path': folder_path,
        'folder_updates': folder_updates
    }


# ============== USAGE EXAMPLES ==============

if __name__ == "__main__":
    # Example 1: Check if specific file exists
    nas_file_path = r"\\NAS_SERVER\shared_folder\data\myfile.csv"
    file_exists = check_file_exists(nas_file_path)
    print(f"File exists: {file_exists}")
    print()

    # Example 2: Check file + get updated files two folders back
    result = check_file_and_folder_updates(nas_file_path, hours=24)
    print(f"File path: {result['file_path']}")
    print(f"File exists: {result['file_exists']}")

    if result['file_exists'] and result['folder_updates']:
        print(f"\nChecking folder (2 levels up): {result['folder_path']}")
        print(f"Total files in folder: {result['folder_updates']['total_files']}")
        print(f"Files updated in last 24 hours: {result['folder_updates']['updated_files_count']}")
        print("\nUpdated files:")
        for file_info in result['folder_updates']['updated_files']:
            print(f"  - {file_info['file']} (Modified: {file_info['modified_time']})")
