#!/usr/bin/env python3

import os
import sys
import subprocess
import shutil
import pwd
import grp
import zipfile
import tarfile
import ast
from packages.scripts.wget import downloads
from packages.scripts.symlink import get_executables

SIMULATION_MODE = "--simulation" in sys.argv
VERBOSE_MODE = "--verbose" in sys.argv
pki_path = os.path.dirname(os.path.realpath(__file__))
sudo_user = os.getenv("SUDO_USER") or os.getlogin()
user_home = os.path.expanduser(f"~{sudo_user}")
total_steps = 7
completed_steps = 0

def logo():
    print("\033[92m")
    print("""
 _______  ___  ____   _____   _____   
|_   __ \|_  ||_  _| |_   _| / ___ `. 
  | |__) | | |_/ /     | |  |_/___) | 
  |  ___/  |  __'.     | |   .'____.' 
 _| |_    _| |  \ \_  _| |_ / /_____  
|_____|  |____||____||_____||_______| 
                                      
    """)
    print("\033[0m")
    
logo()
print("PostKaliInstaller2\n\n")

def display_help():
    help_text = """
    PKI2 (PostKaliInstaller2)

    Usage: sudo python3 pki.py [options]

    Options:
    --help          Display this help message and exit.
    --simulation    Run the script in debug mode. This mode checks if the script runs smoothly without actually installing anything.
    --verbose       Output all information the script normally does "behind the scenes".

    This script automates the installation of software from various sources including apt, git, pip, snap, and wget.
    """
    print(help_text)
    sys.exit()

if "--help" in sys.argv:
    display_help()

if os.geteuid() != 0:
    sys.exit("This script must be run as root. Please use sudo. To view help without sudo \"python3 pki.py --help\"")

if "rene" in sudo_user:
    print("Ja, vi fant dæ i fjæra!")
    sys.exit(1)

def run_command(command):
    log_file = "pki_installed.log"
    with open(log_file, "a") as log:
        log.write(f"Running command: {command}\n")
        if VERBOSE_MODE or SIMULATION_MODE:
            print(f"Running command: {command}")

        if SIMULATION_MODE:
            log.write("Simulation mode: Command not actually executed.\n")
            return

        process_args = {'shell': True, 'check': True, 'stdout': subprocess.PIPE, 'stderr': subprocess.STDOUT}

        try:
            completed_process = subprocess.run(command, **process_args)
            output = completed_process.stdout.decode("utf-8")
            log.write(output + "\n")
            if VERBOSE_MODE:
                print(output)
        except subprocess.CalledProcessError as e:
            error_message = f"An error occurred: {e}\n"
            log.write(error_message)
            if VERBOSE_MODE:
                print(error_message)

def count_installation_items():
    total = 0
    with open("packages/scripts/apt", "r") as file:
        total += sum(1 for _ in file)
    with open("packages/scripts/git", "r") as file:
        total += sum(1 for _ in file)
    with open("packages/scripts/pip", "r") as file:
        total += sum(1 for _ in file)
    with open("packages/scripts/snap", "r") as file:
        total += sum(1 for _ in file)
    with open("packages/scripts/wget.py", "r") as file:
        content = file.read()
        downloads = ast.literal_eval(content.split("downloads = ")[1].strip())
        total += len(downloads)
    total += 3 
    return total

total_steps = count_installation_items()
completed_steps = 0

def update_progress():
    global completed_steps
    completed_steps += 1
    percentage = (completed_steps / total_steps) * 100
    print("\033[92m" f"Progress: {percentage:.2f}% completed" "\033[0m")
    
continueInstall = input("Proceed to installation? Y/n: ")
if continueInstall.lower() == "y" or continueInstall.lower() == "yes" or continueInstall == "":
    print("\033[92m""Starting progress""\033[0m")
else:
    print("Exiting.")
    sys.exit()

def change_ownership(path, user, group):
    try:
        pwd.getpwnam(user)
        grp.getgrnam(group)
    except KeyError:
        print(f"User or group '{user}/{group}' not found. Skipping ownership change.")
        return
    run_command(f"chown -R {user}:{group} {path}")

def install_from_apt():
    print("Starting installation from apt.")
    run_command(f"apt-get update -y")
    with open("packages/scripts/apt", "r") as file:
        for package in file:
            print(f"Installing {package}")
            run_command(f"apt-get install -y {package.strip()}")
            update_progress()

def install_from_git():
    print("Starting installation from git.")
    with open("packages/scripts/git", "r") as file:
        repos = file.read().splitlines()
        for repo in repos:
            repo_name = repo.split('/')[-1].replace('.git', '')
            target_dir = f"/opt/{repo_name}"
            print(f"Downloading and installing {repo_name}")
            run_command(f"git clone {repo} {target_dir}")
            change_ownership(target_dir, os.getenv("SUDO_USER"), os.getenv("SUDO_USER"))
            print(f"Installed {repo_name} in {target_dir}")
            update_progress()

def install_from_pip():
    print("Starting installation from pip.")
    with open("packages/scripts/pip", "r") as file:
        packages = file.read().splitlines()
        for package in packages:
            run_command(f"su {sudo_user} -c 'pip install {package}'")
            print(f"Installed Python package: {package}")
            update_progress()

def install_from_snap():
    print("Starting installation from Snap.")
    with open("packages/scripts/snap", "r") as file:
        packages = file.read().splitlines()
        for package in packages:
            print(f"Installing {package} via Snap")
            run_command(f"snap install {package}")
            update_progress()

def install_from_wget():
    print("Starting download and installation from wget.")
    try:
        with open("packages/scripts/wget.py", "r") as file:
            content = file.read()
            downloads = ast.literal_eval(content.split("downloads = ")[1].strip())
    except (FileNotFoundError, ValueError, SyntaxError) as e:
        print(f"Error reading or parsing wget.py: {e}")
        return
    for url, target_dir in downloads:
        file_name = url.split('/')[-1]
        target_path = f"/opt/{file_name}"
        try:
            if VERBOSE_MODE:
                run_command(f"wget -O {target_path} {url}")
                print(f"Downloaded {file_name} to {target_path}")
            else:
                run_command(f"wget -O {target_path} {url}")
                print(f"Downloaded {file_name} to {target_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error downloading {file_name}: {e}")
            continue

        extract_path = f"/opt/{target_dir}"
        try:
            if file_name.endswith('.zip'):
                with zipfile.ZipFile(target_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                    print(f"Extracted {file_name} to {extract_path}")
                    run_command(f"rm -rf /opt/{file_name}")
                    update_progress()
            elif file_name.endswith('.tar.gz') or file_name.endswith('.tgz'):
                with tarfile.open(target_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(extract_path)
                    print(f"Extracted {file_name} to {extract_path}")
                    run_command(f"rm -rf /opt/{file_name}")
                    update_progress()
            if file_name.endswith('.sh'):
                run_command(f"chmod +x {target_path}")
                run_command(target_path)
                print(f"Executed {file_name}")
                update_progress()
            change_ownership(extract_path, os.getenv("SUDO_USER"), os.getenv("SUDO_USER"))
        except Exception as e:
            print(f"Error handling {file_name}: {e}")

def make_build_kiterunner():
    kiterunner_path = "/opt/kiterunner"
    print(f"Installing {kiterunner_path}...")
    try:
        os.chdir(kiterunner_path)
        run_command("make build")
        print(f"Completed installation successfully in {kiterunner_path}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def update_zshrc(user, line_operations):
    zshrc_path = os.path.join(user_home, ".zshrc")
    if not os.path.exists(zshrc_path):
        print(f".zshrc not found for user {user}.")
        return
    with open(zshrc_path, 'r') as file:
        lines = file.readlines()
    for operation in sorted(line_operations, key=lambda x: x['line_number']):
        line_number = operation['line_number']
        text = operation['text'] + '\n'
        if operation['operation'] == 'replace':
            if line_number <= len(lines):
                lines[line_number - 1] = text
            else:
                print(f"Line {line_number} does not exist for replacement in .zshrc.")
        elif operation['operation'] == 'insert':
            if line_number <= len(lines) + 1:
                lines.insert(line_number - 1, text)
            else:
                print(f"Line {line_number} is out of range for insertion in .zshrc.")
    with open(zshrc_path, 'w') as file:
        file.writelines(lines)

line_operations = [
    {'operation': 'replace', 'line_number': 100, 'text': "		PROMPT=$'%F{%(#.blue.green)}┌──[%F{%(#.red.blue)}%D{%Y/%b/%f} %D{%H:%M:%S}%F{%(#.blue.green)}] '$'\n%F{%(#.blue.green)}├──${debian_chroot:+($debian_chroot)─}${VIRTUAL_ENV:+($(basename $VIRTUAL_ENV))─}(%B%F{%(#.red.blue)}%n'$prompt_symbol$'%m%b%F{%(#.blue.green)})-[%B%F{reset}%(6~.%-1~/…/%4~.%5~)%b%F{%(#.blue.green)}]\n└─%B%(#.%F{red}#.%F{blue}$)%b%F{reset} '"},
    {'operation': 'insert', 'line_number': 245, 'text': "alias ls='ls -la'"}
#Syntax to replace line 100:    {'operation': 'replace', 'line_number': 100, 'text': "Text to replace with"},
#Syntax to add new line 245:    {'operation': 'insert', 'line_number': 245, 'text': "New line text here"}
]

def add_sym_link():
    print("Starting to add symbolic links.")
    os.chdir(user_home)
    for exe_path, link_name in get_executables():
        link_path = f"/usr/bin/{link_name}"
        if os.path.exists(exe_path):
            if not os.access(exe_path, os.X_OK):
                if not SIMULATION_MODE:
                    run_command(f"chmod +x {exe_path}")
                print(f"Set executable permission for {exe_path}")
            run_command(f"ln -sf {exe_path} {link_path}")
            print(f"Created symbolic link for {link_name} in /usr/bin/")
        else:
            print(f"Executable {exe_path} not found.")

install_from_apt()
install_from_git()
install_from_pip()
install_from_snap()
install_from_wget()
make_build_kiterunner()
update_progress()
update_zshrc(sudo_user, line_operations)
update_progress()
add_sym_link()
update_progress()

print("\033[92m""Installation completed successfully. \n Open a new terminal for shell changes.""\033[0m")
