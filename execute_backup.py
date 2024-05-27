import os
import shutil
from datetime import datetime, timedelta
import time
import sys
import configparser
import tkinter as tk
from tkinter import messagebox

def check_disk_space(destination_folder, required_space_gb):
    """Checks available disk space in the drive containing the destination folder."""
    total, used, free = shutil.disk_usage(destination_folder)
    free_space_gb = free / (1024 * 1024 * 1024)
    return free_space_gb >= required_space_gb

def backup_folder(source_folder, destination_folder):
    """Backs up the source folder into the destination folder."""
    current_date = datetime.now()
    backup_folder_path = os.path.join(destination_folder, current_date.strftime("%Y-%m-%d"))

    if not os.path.exists(backup_folder_path):
        os.makedirs(backup_folder_path)

    # Count the total number of files
    total_files = sum(len(files) for _, _, files in os.walk(source_folder))
    files_copied = 0

    for root, dirs, files in os.walk(source_folder):
        for dir_name in dirs:
            relative_path = os.path.relpath(os.path.join(root, dir_name), source_folder)
            os.makedirs(os.path.join(backup_folder_path, relative_path), exist_ok=True)

        for file_name in files:
            source_file_path = os.path.join(root, file_name)
            relative_path = os.path.relpath(source_file_path, source_folder)
            destination_file_path = os.path.join(backup_folder_path, relative_path)
            os.makedirs(os.path.dirname(destination_file_path), exist_ok=True)
            shutil.copy2(source_file_path, destination_file_path)
            files_copied += 1

            # Calculate completion percentage and print progress
            completion_percentage = (files_copied / total_files) * 100
            progress_bar = "#" * int(completion_percentage // 2) + "-" * (50 - int(completion_percentage // 2))
            sys.stdout.write(f"\rBackup progress: [{progress_bar}] {completion_percentage:.2f}% ({files_copied}/{total_files} files)")
            sys.stdout.flush()

    print(f"\nBackup completed for the date: {current_date.strftime('%Y-%m-%d')}")

def remove_old_backups(destination_folder, current_date, delete_weekly, delete_monthly, delete_yearly):
    """Removes old backups keeping only the most recent ones for each week, month, and year based on settings."""
    backups = sorted(os.listdir(destination_folder))
    backups = [datetime.strptime(backup, "%Y-%m-%d") for backup in backups if os.path.isdir(os.path.join(destination_folder, backup))]

    if delete_weekly:
        # Remove excess weekly backups in the current month
        weeks_in_month = {}
        for backup in backups:
            if backup.year == current_date.year and backup.month == current_date.month:
                week_num = backup.isocalendar()[1]
                if week_num in weeks_in_month:
                    if backup > weeks_in_month[week_num]:
                        shutil.rmtree(os.path.join(destination_folder, weeks_in_month[week_num].strftime("%Y-%m-%d")))
                        weeks_in_month[week_num] = backup
                    else:
                        shutil.rmtree(os.path.join(destination_folder, backup.strftime("%Y-%m-%d")))
                else:
                    weeks_in_month[week_num] = backup

    if delete_monthly:
        # Remove excess monthly backups in the current year
        months_in_year = {}
        for backup in backups:
            if backup.year == current_date.year:
                month_num = backup.month
                if month_num in months_in_year:
                    if backup > months_in_year[month_num]:
                        shutil.rmtree(os.path.join(destination_folder, months_in_year[month_num].strftime("%Y-%m-%d")))
                        months_in_year[month_num] = backup
                    else:
                        shutil.rmtree(os.path.join(destination_folder, backup.strftime("%Y-%m-%d")))
                else:
                    months_in_year[month_num] = backup

    if delete_yearly:
        # Remove excess yearly backups in previous years
        years = {}
        for backup in backups:
            year_num = backup.year
            if year_num in years:
                if backup > years[year_num]:
                    shutil.rmtree(os.path.join(destination_folder, years[year_num].strftime("%Y-%m-%d")))
                    years[year_num] = backup
                else:
                    shutil.rmtree(os.path.join(destination_folder, backup.strftime("%Y-%m-%d")))
            else:
                years[year_num] = backup

def perform_backup_and_cleanup(source_folder, destination_folder, required_space_gb, last_run_date_file, delete_weekly, delete_monthly, delete_yearly):
    # Check if the source folder exists
    if not os.path.exists(source_folder):
        messagebox.showerror("Error", "The source folder does not exist.")
        return False

    # Check if the destination folder exists
    if not os.path.exists(destination_folder):
        messagebox.showerror("Error", "The destination folder does not exist.")
        return False

    # Check available disk space
    if not check_disk_space(destination_folder, required_space_gb):
        messagebox.showerror("Error", "The disk has less than the required space available.")
        return False

    # Check if the last_run_date.txt file exists
    if not os.path.exists(last_run_date_file):
        # If last_run_date.txt does not exist, create the file and write the current date
        with open(last_run_date_file, "w") as file:
            file.write(datetime.now().strftime("%Y-%m-%d"))
            print("last_run_date.txt file created")
    else:
        with open(last_run_date_file, "r+") as file:
            last_run_date = file.read().strip()
            current_date = datetime.now()

            print("Last run date:", last_run_date)
            print("Current date:", current_date.strftime("%Y-%m-%d"))

            if last_run_date != current_date.strftime("%Y-%m-%d")):
                backup_folder(source_folder, destination_folder)
                remove_old_backups(destination_folder, current_date, delete_weekly, delete_monthly, delete_yearly)

                # Save the last run date to the file
                file.seek(0)
                file.write(current_date.strftime("%Y-%m-%d"))
                file.truncate()
                print("Last run date updated:", current_date.strftime("%Y-%m-%d"))

    return True

def main():
    config = configparser.ConfigParser()
    config.read('config.ini')

    source_folder = config['BackupSettings']['source_folder']
    destination_folder = config['BackupSettings']['destination_folder']
    required_space_gb = float(config['BackupSettings']['required_disk_space_gb'])
    delete_weekly = config['BackupSettings']['delete_weekly_backups'].lower() == 'Y' or "y"
    delete_monthly = config['BackupSettings']['delete_monthly_backups'].lower() == 'Y' or "y"
    delete_yearly = config['BackupSettings']['delete_yearly_backups'].lower() == 'Y' or "y"

    last_run_date_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "last_run_date.txt")

    while True:
        if perform_backup_and_cleanup(source_folder, destination_folder, required_space_gb, last_run_date_file, delete_weekly, delete_monthly, delete_yearly):
            # Wait for a minute before checking the date again
            time.sleep(60)

if __name__ == "__main__":
    main()
