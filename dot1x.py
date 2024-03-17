#!/usr/bin/env python3

#### __author__ = "Gaur Samal" ####
#### __email__ = "gsamal@cisco.com" ####
#### __version__ = "1.0" ####


import subprocess
import csv
import sys
import os
import getpass

backup_file_name = "interface_backup.txt"
#username = "sdaadmin"
#password = "cisco@123"
device_ips = []
all_device_ips = set()
failed_device_ips = set()
processed_device_ips = set()
unreachable_device_ips = set()
count = 0
count_device_fail = 0
count_device_unreachable=0
modified_interfaces = 0
failed_interfaces = 0
modified_interfaces_count = {}
failed_interfaces_count = {}

def is_pingable(device_ip):
    try:
        subprocess.run(['ping', '-c', '1', device_ip], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
    
def check_authentication(device_ip, username, password):
    try:
        subprocess.run([
            "sshpass", "-p", password, "ssh", "-o", "StrictHostKeyChecking=no",
            f"{username}@{device_ip}", "exit"
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False
    
def backup_interface_config(device_ip, port_name):
    global count, count_device_fail
    global count_device_unreachable
    print(f"Connecting to {device_ip}")
    if not is_pingable(device_ip):
        print(f"The device with IP {device_ip} is not reachable.")
        unreachable_device_ips.add(device_ip)
        count_device_unreachable=len(unreachable_device_ips)
        return False, None
    all_device_ips.add(device_ip)
    count = len(all_device_ips)
    if not check_authentication(device_ip, username, password):
        print(f"Authentication failed for device {device_ip}. Please check your username and password.")
        failed_device_ips.add(device_ip)
        #print(f"{failed_device_ips}")
        count_device_fail=len(failed_device_ips)
        #print(f"{count_device_fail}")
        return False, None
    print(f"Backing up interface config for port: {port_name}")

    try:
        subprocess.run([
            "sshpass", "-p", password, "ssh", "-o", "StrictHostKeyChecking=no",
            f"{username}@{device_ip}", "term len 0"
        ], check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        output_bytes = subprocess.check_output([
            "sshpass", "-p", password, "ssh", "-o", "StrictHostKeyChecking=no",
            f"{username}@{device_ip}", f"show running-config interface {port_name}"
        ], stderr=subprocess.DEVNULL)
        output = output_bytes.decode('utf-8')
        #print(f"{output}")
        if output:
            native_vlan_lines = [line for line in output.split("\n") if 'switchport trunk native vlan' in line]
            if native_vlan_lines:
                vlan_id = ''.join(filter(str.isdigit, native_vlan_lines[0]))
                print(f"Native Vlan is {vlan_id}")
                with open(backup_file_name, "a") as backup_file:
                    backup_file.write(output)
                return True, vlan_id
            else:
                print("Native VLAN line not found in the output.")
                return False, None
        else:
            print(f"Error backing up interface config for port {port_name}")
            return False, None

    except subprocess.CalledProcessError:
        print("Error: SSH connection failed")
        failed_device_ips.add(device_ip)
        #print(f"{failed_device_ips}")
        count_device_fail=len(failed_device_ips)
        #print(f"{count_device_fail}")
        return False, None

    return True

def modify_interface_config(device_ip, port_name, action, vlan_id):
    global modified_interfaces, failed_interfaces
    print(f"Modifying interface config for port {port_name}")
    command = f"term len 0\nconf t\ninterface {port_name}\n"
    if action == "1":
        command += f"authentication event fail action next-method\n" \
                   f"authentication event server dead action authorize vlan {vlan_id}\n" \
                   f"authentication event server dead action authorize voice\n" \
                   f"authentication event server alive action reinitialize\n" \
                   f"authentication host-mode multi-host\n" \
                   f"authentication order mab dot1x\n" \
                   f"authentication priority dot1x mab\n" \
                   f"authentication port-control auto\n" \
                   f"authentication violation restrict\n" \
                   f"mab\n" \
                   f"dot1x pae authenticator\n" \
                   f"end\n" \
                   f"exit\n"
    elif action == "2":
        command += f"no authentication event fail action next-method\n" \
                   f"no authentication event server dead action authorize vlan {vlan_id}\n" \
                   f"no authentication event server dead action authorize voice\n" \
                   f"no authentication event server alive action reinitialize\n" \
                   f"no authentication host-mode multi-host\n" \
                   f"no authentication order mab dot1x\n" \
                   f"no authentication priority dot1x mab\n" \
                   f"no authentication port-control auto\n" \
                   f"no authentication violation restrict\n" \
                   f"no mab\n" \
                   f"no dot1x pae authenticator\n" \
                   f"end\n" \
                   f"exit\n"
    else:
        print("Invalid action. Please choose 1 or 2.")
        return

    try:
        subprocess.run([
            "sshpass", "-p", password, "ssh", "-o", "StrictHostKeyChecking=no",
            f"{username}@{device_ip}"
        ], input=bytes(command, 'utf-8'), stderr=subprocess.DEVNULL, check=True, stdout=subprocess.DEVNULL)
        modified_interfaces += 1
        modified_interfaces_count[port_name] = modified_interfaces_count.get(port_name, 0) + 1
        print(f"Interface config modified for port {port_name}")
    except subprocess.CalledProcessError:
        failed_interfaces += 1
        failed_interfaces_count[port_name] = failed_interfaces_count.get(port_name, 0) + 1
        print(f"Error: An error occurred while modifying interface config for port {port_name}")

def process_csv(csv_file, action):
    global failed_interfaces
    with open(csv_file, newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)
        for row in reader:
            device_ip, port_name = row
            print("=======================================================")
            if device_ip not in failed_device_ips and device_ip not in unreachable_device_ips:
                backup_success, vlan_id = backup_interface_config(device_ip, port_name)
                if backup_success:
                    modify_interface_config(device_ip, port_name, action, vlan_id)
                else:
                    print(f"Skipping modification of interface config due to backup failure for port {port_name}")
                    failed_interfaces += 1
                    failed_interfaces_count[port_name] = failed_interfaces_count.get(port_name, 0) + 1
            else:
                print(f"This device {device_ip} would not be tried as it failed authentication or SSH connectivity atleast once")

def process_failed_devices(csv_file):
    global failed_device_ips
    global failed_interfaces
    with open(csv_file, newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)
        
        for row in reader:
            device_ip, port_name = row
            if (device_ip in failed_device_ips or device_ip in unreachable_device_ips) and device_ip not in processed_device_ips:
                print("=======================================================")
                backup_success, vlan_id = backup_interface_config(device_ip, port_name)
                if backup_success:
                    modify_interface_config(device_ip, port_name, action, vlan_id)
                else:
                    print(f"Skipping modification of interface config due to backup failure for port {port_name}")
                    failed_interfaces += 1
                    failed_interfaces_count[port_name] = failed_interfaces_count.get(port_name, 0) + 1
                    processed_device_ips.add(device_ip)
            else:
                if device_ip in all_device_ips:
                    continue
                else:
                    print("=======================================================")
                    print(f"This device {device_ip} would not be tried as it failed authentication or SSH connectivity atleast once")

def retry_failed_devices(csv_file):
    while True:
        retry_option = input("\nDo you want to retry the operation for failed devices? (yes/no): ").lower()
        if retry_option == "yes":
            process_failed_devices(csv_file)
            break
        elif retry_option == "no":
            print("Exiting...")
            break 
        else:
            print("Please enter 'yes' or 'no'.")

def get_action():
    while True:
        action = input("\nEnter the action (1 to add dot1x config, 2 to remove dot1x config): ")
        if action in ['1', '2']:
            return action
        else:
            print("Invalid action. Please enter 1 or 2.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 dot1x.py <interface_csv_file> OR \n")
        print("Usage: ./dot1x.py <interface_csv_file>")
        sys.exit(1)
    csv_file = sys.argv[1]
    action = get_action()
    print("Enter the device credentials: ( Please note, use the credential which is used by DNAC for managing devices, the credential should be same for all the devices mentioned in csv file)")
    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")
    process_csv(csv_file, action)
    retry_failed_devices(csv_file)
    print("\n=======================================================")
    print("Summary of device login attempted and ports configured:")
    print("=======================================================\n")
    print(f"Unique device IP addresses login attempted: {count}")
    for ip in all_device_ips:
        print(ip)
    print(f"Modified interfaces: {modified_interfaces}")
    print(f"failed logins due to reachability: {count_device_unreachable}")
    for ip in unreachable_device_ips:
        print(ip)
    print(f"failed logins: {count_device_fail}")
    for ip in failed_device_ips:
        print(ip)
    print(f"Failed interfaces: {failed_interfaces}")
    print("\n=======================================================")
    print("Summary of input/backup files and option provided:")
    print("=======================================================\n")
    print(f"CSV file: {csv_file}")
    print(f"Action: {action}")
    backup_file_path = os.path.join(os.getcwd(), backup_file_name)
    print("Backup file created at:", backup_file_path)