#!/usr/bin/env python3
"""
Comprehensive Project Cleanup Script
Removes unnecessary files, organizes structure, and creates backups
"""

import os
import shutil
import glob
from datetime import datetime
from pathlib import Path

class ProjectCleanup:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.files_removed = []
        self.files_kept = []
        
    def create_backup(self):
        """Create backup of important files before cleanup"""
        print("📦 Creating backup...")
        self.backup_dir.mkdir(exist_ok=True)
        
        important_files = [
            "app.py", "rss_manager.py", "rss_scheduler.py", 
            "calendar.db", "requirements.txt", "vercel.json",
            "README.md", "RSS_FEEDS_README.md", "THINGSTODO_SCRAPER_README.md"
        ]
        
        for file in important_files:
            if (self.project_root / file).exists():
                shutil.copy2(self.project_root / file, self.backup_dir / file)
                print(f"  ✅ Backed up: {file}")
    
    def remove_test_files(self):
        """Remove test and startup scripts"""
        print("\n🧹 Removing test/startup files...")
        
        test_files = [
            "quick_start.py", "simple_test.py", "start_app.py", 
            "start_now.py", "start_simple.py", "test_app.py"
        ]
        
        for file in test_files:
            file_path = self.project_root / file
            if file_path.exists():
                file_path.unlink()
                self.files_removed.append(file)
                print(f"  🗑️  Removed: {file}")
    
    def remove_cache_files(self):
        """Remove Python cache and temporary files"""
        print("\n🧹 Removing cache files...")
        
        # Remove __pycache__ directories
        for pycache in self.project_root.rglob("__pycache__"):
            if pycache.is_dir():
                shutil.rmtree(pycache)
                self.files_removed.append(str(pycache.relative_to(self.project_root)))
                print(f"  🗑️  Removed: {pycache.relative_to(self.project_root)}")
        
        # Remove .pyc files
        for pyc_file in self.project_root.rglob("*.pyc"):
            pyc_file.unlink()
            self.files_removed.append(str(pyc_file.relative_to(self.project_root)))
            print(f"  🗑️  Removed: {pyc_file.relative_to(self.project_root)}")
        
        # Remove log files
        log_files = ["rss_scheduler.log", "*.log"]
        for pattern in log_files:
            for log_file in self.project_root.glob(pattern):
                if log_file.is_file():
                    log_file.unlink()
                    self.files_removed.append(str(log_file.relative_to(self.project_root)))
                    print(f"  🗑️  Removed: {log_file.relative_to(self.project_root)}")
    
    def remove_system_files(self):
        """Remove system-generated files"""
        print("\n🧹 Removing system files...")
        
        system_files = [".DS_Store", "Thumbs.db", "*.tmp", "*.bak"]
        for pattern in system_files:
            for file in self.project_root.rglob(pattern):
                if file.is_file():
                    file.unlink()
                    self.files_removed.append(str(file.relative_to(self.project_root)))
                    print(f"  🗑️  Removed: {file.relative_to(self.project_root)}")
    
    def consolidate_parsers(self):
        """Consolidate parser files"""
        print("\n🔧 Consolidating parser files...")
        
        parser_files = [
            "advanced_event_parser.py",
            "advanced_parser.py", 
            "ai_parser.py",
            "washington_post_parser.py"
        ]
        
        # Keep the most comprehensive one, remove others
        keep_file = "washington_post_parser.py"  # Most recent and comprehensive
        
        for parser in parser_files:
            if parser != keep_file:
                file_path = self.project_root / parser
                if file_path.exists():
                    # Move to backup instead of deleting
                    backup_path = self.backup_dir / f"removed_{parser}"
                    shutil.move(str(file_path), str(backup_path))
                    self.files_removed.append(parser)
                    print(f"  📦 Archived: {parser} -> backup/removed_{parser}")
    
    def organize_import_scripts(self):
        """Organize import scripts"""
        print("\n📁 Organizing import scripts...")
        
        import_scripts = [
            "create_full_wp_file.py",
            "import_all_wp_events.py", 
            "import_wp_events.py",
            "import_wp_final.py"
        ]
        
        # Create scripts directory
        scripts_dir = self.project_root / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        for script in import_scripts:
            file_path = self.project_root / script
            if file_path.exists():
                # Move to scripts directory
                new_path = scripts_dir / script
                shutil.move(str(file_path), str(new_path))
                print(f"  📁 Moved: {script} -> scripts/{script}")
    
    def create_gitignore(self):
        """Create/update .gitignore file"""
        print("\n📝 Creating .gitignore...")
        
        gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# Database
*.db
*.sqlite
*.sqlite3

# Logs
*.log
logs/

# System Files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo

# Temporary files
*.tmp
*.bak
*.backup

# Environment variables
.env
.env.local
.env.production

# Backup directories
backup_*/
"""
        
        gitignore_path = self.project_root / ".gitignore"
        with open(gitignore_path, 'w') as f:
            f.write(gitignore_content)
        print("  ✅ Created .gitignore")
    
    def generate_report(self):
        """Generate cleanup report"""
        print("\n📊 Cleanup Report")
        print("=" * 50)
        print(f"Files removed: {len(self.files_removed)}")
        for file in self.files_removed:
            print(f"  🗑️  {file}")
        
        print(f"\nBackup created at: {self.backup_dir}")
        print("\n✅ Cleanup completed successfully!")
    
    def run_cleanup(self):
        """Run complete cleanup process"""
        print("🚀 Starting Project Cleanup...")
        print("=" * 50)
        
        self.create_backup()
        self.remove_test_files()
        self.remove_cache_files()
        self.remove_system_files()
        self.consolidate_parsers()
        self.organize_import_scripts()
        self.create_gitignore()
        self.generate_report()

if __name__ == "__main__":
    cleanup = ProjectCleanup()
    cleanup.run_cleanup()
