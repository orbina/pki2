#!/usr/bin/env python3
# List of executables and their symbolic link names
# Add more as needed

import os
import subprocess
import stat

package_main_scripts = {
    "autorecon": "main.py",
    # Add names of other packages installed with pip and their main scripts here if needed
    # Syntax: "name_of_pip_download": "name_of_main_file",
}

def get_package_install_location(package_name):
    sudo_user = os.environ.get('SUDO_USER') or os.getlogin()
    try:
        output = subprocess.check_output(['sudo', '-u', sudo_user, 'pip', 'show', package_name], text=True)
        for line in output.splitlines():
            if line.startswith('Location:'):
                return line.split(':')[1].strip()
    except subprocess.CalledProcessError:
        print(f"Failed to find the installation location for {package_name}.")
        return None

def find_package_paths(package_names):
    paths = {}
    for package_name in package_names:
        package_location = get_package_install_location(package_name)
        if package_location:
            main_script_name = package_main_scripts.get(package_name)
            main_script = os.path.join(package_location, package_name, main_script_name)
            if os.path.exists(main_script):
                os.chmod(main_script, os.stat(main_script).st_mode | stat.S_IEXEC)
                paths[package_name] = main_script
    return paths

def get_executables():
    package_names = list(package_main_scripts.keys())
    package_paths = find_package_paths(package_names)

    executables = [
        ("/opt/kiterunner/dist/kr", "kr"),
        ("/opt/jwt_tool/jwt_tool.py", "jwt_tool")
        # List of executables with known paths, usually installed with git, add more if needed
        # Syntax: ("/path/to/file", "preferred_shortcut_name"),
    ]

    for package_name in package_names:
        if package_name in package_paths:
            main_script_path = package_paths[package_name]
            symlink_path = f"/usr/bin/{package_name}"
            if not os.path.exists(symlink_path):
                os.symlink(main_script_path, symlink_path)
                print(f"Created symbolic link for {package_name} in /usr/bin/")
            else:
                print(f"Symbolic link for {package_name} already exists in /usr/bin/")
        else:
            print(f"{package_name} not found.")
    
    return executables