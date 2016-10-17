from setuptools import setup, find_packages

setup(
    name='django-jsx',
    version='0.2.0',
    author='Calvin Spealman',
    author_email='calvin@caktusgroup.com',
    packages=find_packages(exclude=['sample_project']),
    include_package_data=True,
    license='BSD',
    description='Integration library for React/JSX and Django',
    classifiers=[
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
    ],
    #long_description=open('README.rst').read(),
)
