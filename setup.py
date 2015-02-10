#!/usr/bin/env python
from setuptools import setup, find_packages
import os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
NEWS = open(os.path.join(here, 'NEWS.txt')).read()


version = '0.6.4'

install_requires = [
    'requests',
    'PyYAML',
    'jinja2',
    'argparse',
    'click',
]


setup(name='cloudy-release-client',
    version=version,
    description="Client program and library for cloudy-release.",
    long_description=README + '\n\n' + NEWS,
    classifiers=[
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    ],
    keywords='deployment cloudy-release',
    author='Luper Rouch',
    author_email='luper.rouch@gmail.com',
    url='https://github.com/flupke/cloudy-release-client',
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    entry_points={
        'console_scripts':
            ['cloudy=cloudyclient.cli.base:main']
    }
)
