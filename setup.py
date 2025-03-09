from setuptools import setup, find_packages

setup(
    name="tpip",
    version="0.1.0",
    description="""优选 pip 镜像源，提升下载速度的命令行工具。
A command line tool that optimizes the pip image source and speeds up downloads.""",
    author="yjys",
    author_email="wsy52552@gmail.com",
    url="https://github.com/wsy-yjys/tpip",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'tpip=tpip.tpip:main',
        ],
    },
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Installation/Setup",
        "Topic :: Utilities",
    ],
    install_requires=[
        "requests",
        "aiohttp",
        "prettytable"
    ]
)
