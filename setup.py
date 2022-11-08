from setuptools import setup

setup(
    name='django-autocompleter',
    version='1.0.0',
    description='A redis-backed autocompletor for Django projects. Originally created by Ara Anjargolian',
    author='YCharts',
    author_email='developers@ycharts.com',
    url='http://github.com/ycharts/django-autocompleter',
    packages=['autocompleter', 'autocompleter.management', 'autocompleter.management.commands'],
    install_requires=['setuptools', 'redis', 'hiredis'],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ]
)
