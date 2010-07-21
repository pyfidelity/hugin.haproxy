from setuptools import setup, find_packages
import os

version = '0.1'

setup(name='hugin.haproxy',
      version=version,
      description="Syslog monitor for haproxy",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        ],
      keywords='haproxy python twisted',
      author='Helge Tesdal',
      author_email='tesdal@jarn.com',
      url='http://www.jarn.com/',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['hugin'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'Twisted',
          # -*- Extra requirements: -*-
      ],
      entry_points = """
          [console_scripts]
          readfile = hugin.haproxy.readfile:main
      [console_scripts]
      parsehaproxy = hugin.haproxy.parsehaproxy:main
      """,
      )
