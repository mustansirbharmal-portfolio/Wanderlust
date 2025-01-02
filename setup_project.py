import os
import shutil

# Create wanderlust package directory
os.makedirs('wanderlust', exist_ok=True)

# Move existing files into wanderlust package
files_to_move = ['__init__.py', 'models.py', 'routes.py', 'app.py']
for file in files_to_move:
    if os.path.exists(file):
        shutil.move(file, os.path.join('wanderlust', file))

# Move templates and static directories
for dir_name in ['templates', 'static']:
    if os.path.exists(dir_name):
        if os.path.exists(os.path.join('wanderlust', dir_name)):
            shutil.rmtree(os.path.join('wanderlust', dir_name))
        shutil.move(dir_name, os.path.join('wanderlust', dir_name))
