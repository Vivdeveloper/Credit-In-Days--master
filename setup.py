from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in credit_days_customization/__init__.py
from credit_days_customization import __version__ as version

setup(
	name="credit_days_customization",
	version=version,
	description="Credit Days Customization",
	author="Akhilaminc",
	author_email="vivekthakor1690@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
