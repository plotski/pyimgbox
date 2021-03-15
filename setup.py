import setuptools
import re

def get_description():
    with open('README.md', 'r') as f:
        return f.read()

def get_var(name):
    with open('pyimgbox/__init__.py') as f:
        content = f.read()
        match = re.search(rf'''^{name}\s*=\s*['"]([^'"]*)['"]''',
                          content, re.MULTILINE)
        if match:
            return match.group(1)
        else:
            raise RuntimeError(f'Unable to find {name}')

setuptools.setup(
    name='pyimgbox',
    version=get_var('__version__'),
    author=get_var('__author__'),
    author_email=get_var('__author_email__'),
    description='Upload images to imgbox.com',
    long_description=get_description(),
    long_description_content_type='text/markdown',
    url='https://github.com/plotski/pyimgbox',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries',
        'Intended Audience :: Developers',
    ],
    python_requires='>=3.6',
    install_requires=[
        'httpx==0.*,>=0.16.0',
        'beautifulsoup4',
    ],
)
