from setuptools import find_packages, setup

import reporter


setup(name='market-reporter',
      version=reporter.__version__,
      description='Market Reporter',
      author='Akira Miyazawa, Tatsuya Aoki, Fumiya Yamamoto, Soichiro Murakami, and Akihiko Watanabe',
      author_email='miyazawa-a@nii.ac.jp, aoki@lr.pi.titech.ac.jp',
      url='https://github.com/aistairc/market-reporter',
      packages=find_packages(exclude=['docs', 'envs', 'figures', 'resources', 'tests']),
      test_suite='tests')
