from setuptools import setup, find_packages

setup(
    name='django-autocompleter',
    version="0.1.0",
    description='A redis-backed autocompletor for Django projects',
    author='Ara Anjargolian',
    author_email='ara818@gmail.com',
    url='http://github.com/ara818/django-autocompleter',
    packages=find_packages('autocompleter'),
    install_requires = ['setuptools', 'redis'],
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
