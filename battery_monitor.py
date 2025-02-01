#!/usr/bin/env python3
from datetime import datetime
import subprocess
import csv
import time
from apscheduler.schedulers.background import BackgroundScheduler

class BatteryMonitor:
    def __init__(self, log_file="battery_status.log"):
        self.log_file = log_file
        
    def run_command(self, command):
        """Execute shell command and return output"""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e}")
            return None

    def get_battery_info(self):
        """Get battery status using acpi"""
        battery_output = self.run_command('acpi -b')
        if not battery_output:
            return None
            
        try:
            # Parse battery info
            parts = battery_output.split(",")
            status_part = parts[0].split(":")
            status = status_part[1].strip()
            percentage = parts[1].strip().rstrip("%")
            time_remaining = parts[2].strip() if len(parts) > 2 else "Unknown"
            
            return {
                "status": status,
                "percentage": int(percentage),
                "time_remaining": time_remaining
            }
        except (IndexError, ValueError) as e:
            print(f"Error parsing battery info: {e}")
            return None

    def get_top_processes(self, count=3):
        """Get top processes by memory usage"""
        cmd = f"ps aux --sort=-%mem | awk 'NR>1 && $11 != \"ps\" {{print $11}}' | head -n {count}"
        output = self.run_command(cmd)
        if not output:
            return []
        
        processes = output.split("\n")
        return [p.split("/")[-1] for p in processes]  # Get just the process name

    def log_status(self):
        """Log current battery status and system info"""
        battery_info = self.get_battery_info()
        if not battery_info:
            return
            
        processes = self.get_top_processes()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        data = [
            timestamp,
            battery_info["percentage"],
            battery_info["status"],
            battery_info["time_remaining"]
        ] + processes

        # Only log if there's a change in battery percentage or status
        if self._should_log(data):
            with open(self.log_file, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(data)
            
            self._print_status(battery_info, processes)

    def _should_log(self, current_data):
        """Check if we should log this entry"""
        try:
            with open(self.log_file, 'r') as file:
                last_line = file.readlines()[-1].strip()
                last_data = last_line.split(',')
                
                # Log if battery percentage or status changed
                return (current_data[1] != int(last_data[1]) or 
                        current_data[2] != last_data[2])
        except (FileNotFoundError, IndexError):
            return True  # Log if file doesn't exist or is empty

    def _print_status(self, battery_info, processes):
        """Print current status to console"""
        status = f"""
Battery Status:
    Level:     {battery_info['percentage']}%
    State:     {battery_info['status']}
    Remaining: {battery_info['time_remaining']}

Top Processes:
    {chr(8226)} {processes[0] if len(processes) > 0 else 'N/A'}
    {chr(8226)} {processes[1] if len(processes) > 1 else 'N/A'}
    {chr(8226)} {processes[2] if len(processes) > 2 else 'N/A'}
        """
        print(status)

def main():
    monitor = BatteryMonitor()
    
    # Schedule monitoring every minute
    scheduler = BackgroundScheduler()
    scheduler.add_job(monitor.log_status, 'interval', minutes=1)
    scheduler.start()
    
    # Initial status check
    monitor.log_status()
    
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("\nShutting down battery monitor...")
        scheduler.shutdown()

if __name__ == "__main__":
    main()
