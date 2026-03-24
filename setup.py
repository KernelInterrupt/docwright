from setuptools import find_packages, setup

setup(
    name="docwright",
    version="0.1.0",
    description="Playwright-like runtime for guided document reading and controlled document actions",
    license="Apache-2.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    extras_require={
        "document": [],
        "latex": [],
        "full": [],
    },
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
    ],
    package_data={"docwright.capabilities.resources": ["*.md"]},
)
