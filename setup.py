from setuptools import setup, find_packages

setup(
    name="wanderlust",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Flask==3.0.0',
        'Flask-SQLAlchemy==3.1.1',
        'Flask-Login==0.6.3',
        'openai==1.6.1',
        'python-dotenv==1.0.0',
        'Pillow==10.1.0',
        'requests==2.31.0',
        'werkzeug==3.0.1'
    ],
)
