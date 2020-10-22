# -*- coding: utf-8 -*-


from setuptools import setup, find_packages


with open('github_pipeline/man/VERSION', 'rb') as f:
    version = f.read().decode('utf-8')

with open('README.md', 'rb') as f:
    long_descr = f.read().decode('utf-8')

with open('requirements.txt', 'rb') as f:
    requirements = f.read().decode('utf-8').split('\n')


setup(
    name='github-pipeline',
    packages=find_packages(),
    install_requires=requirements,
    tests_require=['pytest', ],
    setup_requires=['pytest', 'pytest-runner'],
    zip_safe=False,
    include_package_data=True,
    version=version,
    description='GitHub repository processing pipeline library.',
    long_description=long_descr,
    author='Tim Storer',
    author_email='timothy.storer@glasgow.ac.uk',
    url='https://git.dcs.gla.ac.uk/cornichon/github-pipeline',
)
