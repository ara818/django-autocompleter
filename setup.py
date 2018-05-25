from setuptools import setup

setup(
    name='django-autocompleter',
    version="0.6.0",
    description='A redis-backed autocompletor for Django projects',
    author='Tom Jakeway',
    author_email='tom@ycharts.com',
    url='http://github.com/ara818/django-autocompleter',
    packages=['autocompleter', 'autocompleter.management', 'autocompleter.management.commands'],
    install_requires=['setuptools', 'redis'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ]
)
