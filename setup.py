import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="python-testing-crawler",
    version="0.2.2",
    author="Chris Wood",
    description="Python Test Crawler",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="python testing crawler",
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
    install_requires=[
        'bs4',
        'soupsieve',
        'dataclasses;python_version<"3.7"',  # backport
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Testing",
    ],
)
