import os
from setuptools import setup, find_packages

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "version.txt")) as f:
    version = f.read().rstrip()

with open(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), "requirements", "base.in")
) as f:
    install_requires = f.readlines()

setup(
    name="iscript",
    version=version,
    description="TaskCluster iScript",
    author="Mozilla Release Engineering",
    author_email="release+python@mozilla.com",
    url="https://github.com/mozilla-releng/scriptworker-scripts/tree/master/iscript",
    packages=find_packages(),
    package_data={"iscript": ["data/*"]},
    include_package_data=True,
    zip_safe=False,
    entry_points={"console_scripts": ["iscript = iscript.script:main"]},
    license="MPL2",
    install_requires=install_requires,
)
