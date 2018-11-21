from setuptools import setup, find_packages

import sys
install_requires = ["zmq","numpy",'tables','pyparsing','matplotlib']

setup(name="SSDAQ",
      version="0.4.0",
      description="A framework to handle slow signal data from the CHEC-S camera",
      author="Samuel Flis",
      author_email="samuel.flis@desy.de",
      url='https://github.com/sflis/SSDAQ',
      packages=find_packages(),
      provides=["ssdaq"],
      license="GNU Lesser General Public License v3 or later",
      install_requires=install_requires,
      extras_requires={
          #'encryption': ['cryptography']
      },
      classifiers=["Programming Language :: Python",
                   "Programming Language :: Python :: 3",
                   "Development Status :: 4 - Beta",
                   "Intended Audience :: Developers",
                   "Operating System :: OS Independent",
                   "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   ],
      entry_points={'console_scripts':
                    [
                        'ssdaq = ssdaq.bin.ssdaqd:main',
                        'ssdatawriter = ssdaq.bin.ssdatawriter:main',
                        'ss-example-listener = ssdaq.bin.simple_ev_listn:main'
                    ]
                    }
      )

