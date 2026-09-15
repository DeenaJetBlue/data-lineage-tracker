import os
from datetime import datetime
from configparser import ConfigParser


def read_config():
    config = ConfigParser()
    config.read('.config')
    return config.get('DEFAULT', 'NAS_Root_Folder').strip()


def get_nas_status(folder_path):
    if not os.path.isdir(folder_path):
        return {'error': f"Folder does not exist: {folder_path}"}

    total_files = 0
    most_recent_file = None
    most_recent_time = 0

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            total_files += 1
            file_path = os.path.join(root, file)

            try:
                mod_time = os.path.getmtime(file_path)
                if mod_time > most_recent_time:
                    most_recent_time = mod_time
                    most_recent_file = {
                        'name': file,
                        'path': file_path,
                        'modified': datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
                    }
            except Exception as e:
                pass

    return {
        'folder_path': folder_path,
        'total_files': total_files,
        'most_recent_file': most_recent_file
    }


if __name__ == "__main__":
    nas_root = read_config()
    result = get_nas_status(nas_root)

    if 'error' in result:
        print(result['error'])
    else:
        print(f"Folder: {result['folder_path']}")
        print(f"Total files: {result['total_files']}")
        if result['most_recent_file']:
            print(f"\nMost recent file:")
            print(f"  Name: {result['most_recent_file']['name']}")
            print(f"  Path: {result['most_recent_file']['path']}")
            print(f"  Modified: {result['most_recent_file']['modified']}")
