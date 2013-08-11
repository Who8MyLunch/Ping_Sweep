

from setuptools import setup, find_packages

entry_points = {'console_scripts': ['ping_sweep = ping_sweep:main']}

# Other stuff.
version = '2013.08.11'
description = 'Ping return time analysis tool'

# Do it.
setup(name='ping_sweep',
      packages=find_packages(),

      entry_points=entry_points,

      # Metadata
      version=version,
      author='Pierre V. Villeneuve',
      author_email='pierre.villeneuve@gmail.com',
      description=description,
)
