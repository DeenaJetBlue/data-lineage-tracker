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


def count_updated_files(folder_path, reference_file_time=None, hours=24):
    """
    Count how many files in a folder have been updated after a reference file's modification time.

    Args:
        folder_path (str): Path to the folder to check
        reference_file_time (float): Reference modification time (unix timestamp).
                                     Only files modified after this time will be counted.
        hours (int): Number of hours to look back (default: 24 hours) - used if reference_file_time is None

    Returns:
        dict: Dictionary containing:
            - 'total_files': Total number of files in folder
            - 'updated_files_count': Number of files updated after reference time
            - 'updated_files': List of updated files with their modification time
    """
    try:
        if not os.path.isdir(folder_path):
            print(f"Folder does not exist: {folder_path}")
            return None

        # Use reference file time if provided, otherwise use hours threshold
        if reference_file_time is not None:
            time_threshold = reference_file_time
        else:
            current_time = time.time()
            time_threshold = current_time - (hours * 3600)  # Convert hours to seconds

        total_files = 0
        updated_files = []
        max_depth = 0

        print(f"Scanning folder: {folder_path}")

        # Walk through the folder with depth tracking
        for root, dirs, files in os.walk(folder_path):
            # Calculate depth to prevent infinite loops
            depth = root.replace(folder_path, '').count(os.sep)
            if depth > 10:  # Safety limit
                continue

            max_depth = max(max_depth, depth)

            for file in files:
                total_files += 1
                file_path = os.path.join(root, file)

                # Print progress every 1000 files
                if total_files % 1000 == 0:
                    print(f"{total_files} files checked...")

                try:
                    # Get file modification time
                    mod_time = os.path.getmtime(file_path)

                    # Check if file was modified after the reference time
                    if mod_time > time_threshold:
                        mod_datetime = datetime.fromtimestamp(mod_time)
                        updated_files.append({
                            'file': file,
                            'path': file_path,
                            'modified_time': mod_datetime.strftime('%Y-%m-%d %H:%M:%S')
                        })

                except Exception as e:
                    pass

        return {
            'total_files': total_files,
            'updated_files_count': len(updated_files),
            'updated_files': updated_files,
            'max_folder_depth': max_depth
        }

    except Exception as e:
        print(f"Error checking folder: {e}")
        return None


def check_file_and_folder_updates(file_path, hours=24):
    """
    Combined function to:
    1. Check if a particular file exists
    2. Get reference file's modification time
    3. Count updated files two directories up from the file location that were modified AFTER the reference file

    Args:
        file_path (str): Full path to the file to check
        hours (int): Fallback hours to look back if file doesn't exist

    Returns:
        dict: Combined results
    """
    file_exists = check_file_exists(file_path)
    reference_file_time = None

    if file_exists:
        try:
            # Get the modification time of the reference file
            reference_file_time = os.path.getmtime(file_path)
            ref_time_str = datetime.fromtimestamp(reference_file_time).strftime('%Y-%m-%d %H:%M:%S')
            print(f"Particular file exists: {file_path}")
            print(f"Modified time: {ref_time_str}")
            print()
        except Exception as e:
            print(f"Error getting file modification time: {e}")

    # Go back two folders from the file location
    folder_path = os.path.dirname(os.path.dirname(file_path))
    folder_updates = count_updated_files(folder_path, reference_file_time, hours) if file_exists else None

    return {
        'file_path': file_path,
        'file_exists': file_exists,
        'reference_file_time': reference_file_time,
        'folder_path': folder_path,
        'folder_updates': folder_updates
    }


# ============== USAGE EXAMPLES ==============

if __name__ == "__main__":
    # Example: Check file + get files updated AFTER reference file time
    nas_file_path = r"\\NAS_SERVER\shared_folder\data\myfile.csv"

    result = check_file_and_folder_updates(nas_file_path, hours=24)

    if result['file_exists'] and result['folder_updates']:
        print(f"{result['folder_updates']['updated_files_count']} files found after the updated time")
        print()

        if result['folder_updates']['updated_files']:
            print("Updated files:")
            for i, file_info in enumerate(result['folder_updates']['updated_files'], 1):
                print(f"  {i}. {file_info['file']}")
                print(f"     Path: {file_info['path']}")
                print(f"     Modified: {file_info['modified_time']}")
    elif result['file_exists'] and not result['folder_updates']:
        print("Could not scan folder for updates.")
    else:
        print("File does not exist.")
