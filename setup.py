
from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

version = '0.3'
setup(name='coproc',
    version='{}'.format(version),
    description='Tools for working with concurrent processes.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/devincornell/coproc',
    author='Devin J. Cornell',
    author_email='devinj.cornell@gmail.com',
    license='MIT',
    packages=find_packages(include=['coproc', 'coproc.*']),
    install_requires=['pandas', 'plotnine', 'matplotlib', 'psutil'],
    zip_safe=False,
    download_url='https://github.com/devincornell/plotnine/archive/v{}.tar.gz'.format(version)
)

