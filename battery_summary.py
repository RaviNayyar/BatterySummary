from datetime import datetime
import subprocess
import csv
import sys

status_file = "/home/ravi/.RaviNayyar/Programs/battery/battery_status.log"

charging_string = "Charging"
discharging_string = "Discharging"

#Graph settings
max_height = 25
max_width = 100
height_reducer = int(100/max_height)

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr.strip()}"


def get_battery_delta(section):
    delta = section['h'] - section['l']
    if delta < 0:
        return -1*delta
    return delta


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

# TODO: Processes cannot be what is current, it needs to be the top processes found
def get_status():
    status = []
    time = get_current_time()
    battery_status = get_battery_status()
    process_list = get_top_processes()
    status.append(time)
    status = status + battery_status + process_list

    print_status = '''
    Time            {0}
    Current Level:  {1}
    Current Status: {2}
    Remainder:      {3}

    Top Processes
    \t{4}
    \t{5}
    \t{6}
    '''.format(time,battery_status[0], battery_status[1], battery_status[2], process_list[0], process_list[1], process_list[2])

    return [status, print_status]

    #write_to_file(status)


def print_histogram(data):
    height_denotion = '| '
    print_point = '#'
    empty_point = ' '*len(print_point)
    # Print the histogram
    for height in range(max_height, 0, -1):
        line = height_denotion
        for value in data:
            if value >= height:
                line += print_point
            else:
                line += empty_point
        print(line)
    print("-"*max_width)


def generate_battery_graph(og):
    def extract_data(section):
        high = section["h"]
        low = section["l"]
        direction = section["d"]
        graph_section = []
        
        start = low
        end = high
        iteration = 1
        if direction == discharging_string:
            iteration = 1 * -1
            start = high 
            end = low 
        
        for x in range(start, end, iteration):
            reduced_x = int(x/height_reducer)
            graph_section.append(reduced_x)

        return graph_section

    def extract_data_old(section):
        bd = get_battery_delta(section)
        
        iteration = 0
        if bd >= 70:
            iteration = 2
        elif bd >= 35 and bd < 70:
            iteration = 4
        else:
            iteration = 6
        
        high = section["h"]
        low = section["l"]
        direction = section["d"]
        graph_section = []
        
        start = low
        end = high

        if direction == discharging_string:
            iteration = iteration * -1
            start = high 
            end = low 
        
        for x in range(start, end, iteration):
            reduced_x = int(x/height_reducer)
            graph_section.append(reduced_x)

        return graph_section

    extracted = []
    for s in og:
        extracted += extract_data(s)

    if len(extracted) > 100:
        extracted = extracted[len(extracted)-100:]

    print_histogram(extracted)


def organize_battery_data():
    def set_top_processes(proc, p_ds):
        for p in proc:
            if p not in p_ds:
                p_ds[p] = 1
            else:
                p_ds[p] += 1

    def add_proccesses_to_section(current_section, process_dict):
        sorted_processes = sorted(process_dict.items(), key=lambda x: x[1], reverse=True)
        top_processes = [p[0] for p in sorted_processes[:3]]
        try:
            current_section["p1"] = top_processes[0]
            current_section["p2"] = top_processes[1]
            current_section["p3"] = top_processes[2]
        except:
            pass


    organized_graph = []
    with open(status_file, 'r') as f:
        lines = f.readlines()
    
    current_section = {"h":0, "l":0, "d":"", "p1": "N/A", "p2": "N/A", "p3": "N/A"}
    current_section_processes = {}
    for line in lines:
        data = line.strip().split(",")
        level = int(data[1].strip("%"))
        level = max(level, 1)  # Ensure level is at least 1
        direction = data[2]
        processes = [data[4], data[5], data[6]]
        if current_section["d"] == "":
            current_section["h"] = level
            current_section["l"] = level
            current_section["d"] = direction

        if direction == current_section["d"]:
            if direction == charging_string:
                current_section["h"] = level
            else:
                current_section["l"] = level

            set_top_processes(processes, current_section_processes)            
        
        else:
            add_proccesses_to_section(current_section, current_section_processes)
            organized_graph.append(current_section.copy())

            current_section_processes = {}
            current_section = {"h":0, "l":0, "d":"", "p1": "N/A", "p2": "N/A", "p3": "N/A"}

            current_section["h"] = level
            current_section["l"] = level
            current_section["d"] = direction
            set_top_processes(processes, current_section_processes)


    add_proccesses_to_section(current_section, current_section_processes)
    organized_graph.append(current_section.copy())

    # Condensing battery data
    remaining_data_points = max_width
    bat_data = []

    for s in range(len(organized_graph)-1, -1, -1):
        bat_delta = get_battery_delta(organized_graph[s])
        if (remaining_data_points - bat_delta) >= 0:
            remaining_data_points -= bat_delta
            bat_data = [organized_graph[s]] + bat_data
        else:
            direction = organized_graph[s]["d"]
            if direction == discharging_string:
                organized_graph[s]["l"] = max_width - (organized_graph[s]["h"] - remaining_data_points)
                bat_data = [organized_graph[s]] + bat_data
                return bat_data

    return bat_data


def print_status():
    status = get_status()


if __name__ == '__main__':
    og = organize_battery_data()
    generate_battery_graph(og)

    printable_status = get_status()[1]
    print(printable_status)


