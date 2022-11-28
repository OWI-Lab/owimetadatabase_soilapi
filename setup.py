import setuptools

setuptools.setup(
    name="owimetadatabase_soilapi",
    version="0.1.0",
    author="OWI-Lab",
    author_email="bruno.stuyts@vub.be",
    description="Tools for preprocessing soil data from the database",
    long_description=open("README.rst").read(),
    packages=setuptools.find_packages(),
    install_requires=[
        'plotly',
        'requests',
        'matplotlib',
        'pandas',
        'groundhog',
        'pyproj'
    ],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
