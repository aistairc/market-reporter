from setuptools import find_packages, setup

import fag


setup(name='fag',
      version=fag.__version__,
      description='Financial Article Generator',
      author='Akira Miyazawa, Tatsuya Aoki, Fumiya Yamamoto, Soichiro Murakami, and Akihiko Watanabe',
      author_email='miyazawa-a@nii.ac.jp, aoki@lr.pi.titech.ac.jp',
      url='https://github.com/aistairc/fag',
      packages=find_packages(exclude=['docs', 'envs', 'resources', 'tests']),
      test_suite='tests')
