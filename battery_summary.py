#!/usr/bin/env python3
from datetime import datetime
import csv
from collections import defaultdict
import sys

class BatterySummary:
    def __init__(self, log_file="battery_status.log"):
        self.log_file = log_file
        self.max_width = 100
        self.max_height = 25
        self.height_scale = 100 // self.max_height

    def load_data(self):
        """Load and parse battery log data"""
        try:
            with open(self.log_file, 'r') as file:
                reader = csv.reader(file)
                return list(reader)
        except FileNotFoundError:
            print(f"Error: Could not find log file: {self.log_file}")
            return []

    def analyze_battery_sections(self):
        """Analyze battery data into charging/discharging sections"""
        data = self.load_data()
        if not data:
            return []

        sections = []
        current_section = {
            'start_time': None,
            'end_time': None,
            'start_level': None,
            'end_level': None,
            'direction': None,
            'processes': defaultdict(int)
        }

        for row in data:
            try:
                timestamp = row[0]
                level = int(row[1].rstrip('%'))  # Strip % before converting to int
                status = row[2]
                processes = row[4:7] if len(row) >= 7 else []

                if current_section['direction'] != status:
                    if current_section['direction'] is not None:
                        current_section['end_time'] = timestamp
                        current_section['end_level'] = level
                        sections.append(current_section.copy())

                    current_section = {
                        'start_time': timestamp,
                        'start_level': level,
                        'direction': status,
                        'processes': defaultdict(int)
                    }

                # Track process frequency
                for process in processes:
                    current_section['processes'][process] += 1

            except (IndexError, ValueError) as e:
                print(f"Warning: Skipping malformed data row: {row}")
                continue

        # Add final section
        if current_section['direction'] is not None:
            current_section['end_time'] = timestamp
            current_section['end_level'] = level
            sections.append(current_section)

        return sections

    def generate_graph(self):
        """Generate ASCII battery graph"""
        sections = self.analyze_battery_sections()
        if not sections:
            return

        # Generate points for graph
        points = []
        for section in sections:
            start_level = section['start_level']
            end_level = section['end_level']
            step = 1 if start_level <= end_level else -1
            
            section_points = list(range(start_level, end_level + step, step))
            points.extend([p // self.height_scale for p in section_points])

        # Trim to max width if needed
        if len(points) > self.max_width:
            points = points[-self.max_width:]

        # Print graph
        self._print_graph(points)
        self._print_summary(sections[-1])  # Print latest section summary

    def _print_graph(self, points):
        """Print ASCII battery graph"""
        print("\nBattery Level History:")
        print("-" * 50)  # Shorter separator line

        # Use fewer height levels (10 instead of 25)
        self.max_height = 10
        self.height_scale = 100 // self.max_height

        # Use lighter characters for visualization
        for height in range(self.max_height, -1, -1):
            if height % 2 == 0:  # Only show every other percentage label
                line = f"{height*self.height_scale:3}% "
            else:
                line = "    "
            
            for value in points:
                # Use lighter characters: '·' for empty, '▪' for filled
                line += "▪" if value >= height else "·"
            print(line)

        print("-" * 50)

    def _print_summary(self, latest_section):
        """Print summary of latest battery section"""
        # Get top 3 processes
        top_processes = sorted(
            latest_section['processes'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        summary = f"""Battery Status: {latest_section['direction']} ({latest_section['start_level']}% → {latest_section['end_level']}%)
Time: {latest_section['start_time']} → {latest_section['end_time']}
Top Processes: {', '.join(f'{proc}({count})' for proc, count in top_processes)}"""

        print(summary)

def main():
    summary = BatterySummary()
    summary.generate_graph()

if __name__ == "__main__":
    main()


