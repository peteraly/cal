#!/usr/bin/env python3
"""
Ongoing Project Maintenance Script
Run this periodically to keep your project clean
"""

import os
import glob
import shutil
from datetime import datetime, timedelta
from pathlib import Path

class ProjectMaintenance:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        
    def clean_old_logs(self, days_old=7):
        """Remove log files older than specified days"""
        print("🧹 Cleaning old log files...")
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        log_patterns = ["*.log", "logs/*.log"]
        
        for pattern in log_patterns:
            for log_file in self.project_root.rglob(pattern):
                if log_file.is_file():
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        log_file.unlink()
                        print(f"  🗑️  Removed old log: {log_file.name}")
    
    def clean_temp_files(self):
        """Remove temporary files"""
        print("🧹 Cleaning temporary files...")
        
        temp_patterns = ["*.tmp", "*.temp", "*.bak", "*.backup", "*.swp", "*.swo"]
        
        for pattern in temp_patterns:
            for temp_file in self.project_root.rglob(pattern):
                if temp_file.is_file():
                    temp_file.unlink()
                    print(f"  🗑️  Removed temp file: {temp_file.name}")
    
    def clean_python_cache(self):
        """Remove Python cache files"""
        print("🧹 Cleaning Python cache...")
        
        for pycache in self.project_root.rglob("__pycache__"):
            if pycache.is_dir():
                shutil.rmtree(pycache)
                print(f"  🗑️  Removed cache: {pycache.relative_to(self.project_root)}")
        
        for pyc_file in self.project_root.rglob("*.pyc"):
            pyc_file.unlink()
            print(f"  🗑️  Removed: {pyc_file.name}")
    
    def clean_system_files(self):
        """Remove system-generated files"""
        print("🧹 Cleaning system files...")
        
        system_files = [".DS_Store", "Thumbs.db", "desktop.ini"]
        
        for file in self.project_root.rglob("*"):
            if file.name in system_files:
                file.unlink()
                print(f"  🗑️  Removed system file: {file.name}")
    
    def check_disk_usage(self):
        """Check disk usage of project"""
        print("📊 Checking disk usage...")
        
        total_size = 0
        file_count = 0
        
        for file in self.project_root.rglob("*"):
            if file.is_file():
                total_size += file.stat().st_size
                file_count += 1
        
        size_mb = total_size / (1024 * 1024)
        print(f"  📁 Total files: {file_count}")
        print(f"  💾 Total size: {size_mb:.2f} MB")
    
    def run_maintenance(self):
        """Run all maintenance tasks"""
        print("🔧 Running Project Maintenance...")
        print("=" * 40)
        
        self.clean_old_logs()
        self.clean_temp_files()
        self.clean_python_cache()
        self.clean_system_files()
        self.check_disk_usage()
        
        print("\n✅ Maintenance completed!")

if __name__ == "__main__":
    maintenance = ProjectMaintenance()
    maintenance.run_maintenance()
