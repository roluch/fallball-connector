import codecs

from os.path import abspath, dirname, join

from setuptools import find_packages, setup

from pip.req import parse_requirements


here = abspath(dirname(__file__))

with codecs.open(join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

with codecs.open(join(here, 'VERSION'), encoding='utf-8') as f:
    VERSION = f.read()

install_reqs = parse_requirements(join(here, 'requirements.txt'), session=False)
reqs = [str(ir.req) for ir in install_reqs]


setup(
    name='fallball-connector',
    version=VERSION,
    author='APS Connect team',
    author_email='aps@odin.com',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    setup_requires=['nose>=1.0'],
    install_requires=reqs,
    url='https://github.com/ingrammicro',
    license='Apache License',
    description='A sample connector for FallBall file sharing application',
    long_description=long_description,
)
