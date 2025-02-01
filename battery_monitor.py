from apscheduler.schedulers.background import BackgroundScheduler
import time
from datetime import datetime
import subprocess
import csv
import sys

status_file = "battery_status.log"

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr.strip()}"


def get_current_time():
    current_time = datetime.now()
    return current_time.strftime("%H:%M:%S")


def get_top_processes():
    command = "ps aux --sort=-%mem | awk 'NR>1 && $11 != \"ps\" {split($11, a, \"/\"); print a[length(a)]}' | head -n 3"
    output = run_command(command)
    return output.split("\n")
    

def get_battery_status():
    battery_output = run_command('acpi -b')
    battery_output = battery_output.split(",")
    status = battery_output[0]
    status = status[status.index(":")+2:].strip()
    level = battery_output[1].strip()
    remainder = battery_output[2].strip()
    return [level, status, remainder]


def write_to_file(data):
    with open(status_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(data)

def compare_to_previous_entry(current_status):
    
    command = "tail -n 1 {}".format(status_file)
    last_line = run_command(command)
    last_line_data = last_line.split(",")
    
    last_percentage = last_line_data[1]
    current_percentage = current_status[1]
    if last_percentage == current_percentage:
        return True
    return False

def get_status():
    status = []
    time = get_current_time()
    battery_status = get_battery_status()
    process_list = get_top_processes()
    status.append(time)
    status = status + battery_status + process_list
    return status


def monitor_battery():
    print("Function executed at:", time.strftime("%Y-%m-%d %H:%M:%S"))
    status_data = get_status()
    
    if not compare_to_previous_entry(status_data):
        write_to_file(status_data)

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(monitor_battery, 'interval', minutes=1)  # Runs every minute
    scheduler.start()
    monitor_battery()
    
    try:
        # Keep the main thread alive to allow the scheduler to run
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down scheduler...")
        scheduler.shutdown()
