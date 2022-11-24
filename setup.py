import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='selenium_profiles',
    author='Aurin Aegerter',
    author_email='aurinliun@gmx.ch',
    description='Emulate and Automate Chrome using Profiles and Selenium',
    keywords='Selenium,emulation, automation, undetected-chromedriver, webautomation',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/kaliiiiiiiiii/Selenium_Profiles',
    project_urls={
        'Documentation': 'https://github.com/kaliiiiiiiiii/Selenium_Profiles',
        'Bug Reports':
        'https://github.com/kaliiiiiiiiii/Selenium_Profiles/issues',
        'Source Code': 'https://github.com/kaliiiiiiiiii/Selenium_Profiles',
        # 'Funding': '',
        # 'Say Thanks!': '',
    },
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    classifiers=[
        # see https://pypi.org/classifiers/
        'Development Status :: 5 - Production/Stable',

        'Intended Audience :: Developers',
        'Topic :: Webautomation :: Selenium',
        'Programming Language :: Python :: 3.7',
        'License :: CC BY-NC-SA 4.0',
        'Operating System :: Windows',
    ],
    python_requires='~=3.7',
    install_requires=['selenium', 'requests', 'undetected-chromedriver'],
    include_package_data=True,
    extras_require={
        'dev': ['check-manifest'],
        # 'test': ['coverage'],
    },
)
