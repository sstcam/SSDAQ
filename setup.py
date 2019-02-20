from setuptools import setup, find_packages

import sys
install_requires = ["zmq","numpy",'tables','pyparsing','matplotlib','pyyaml','click']

# version = {}
# with open('ssdaq/version.py') as fp:
#     exec(fp.read(),version)
# from ssdaq import version
PACKAGENAME = 'ssdaq'
# try:
__import__(PACKAGENAME+'.version',fromlist=[None])

# except:
#     pass
package = sys.modules[PACKAGENAME+'.version']

# # LONG_DESCRIPTION = package.__doc__

package.version.update_release_version()
setup(name="SSDAQ",
      version=version.get_version(pep440=True),#version['__version__'],
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
                        'ss-example-listener = ssdaq.bin.simple_ev_listn:main',
                        'control-ssdaq=ssdaq.bin.ssdaq_control:main'
                    ]
                    }
      )

