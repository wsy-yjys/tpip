from setuptools import setup, find_packages

setup(
    name="tpip",
    version="1.2.0",
    description="""帮助中国用户快速切换 pip 镜像源，提升下载速度的命令行工具
A tool helps Chinese users quickly switch pip mirrors to improve download speeds.""",
    author="caoergou",
    author_email="itsericsmail@gmail.com",
    url="https://github.com/caoergou/tpip",
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
    ],
    install_requires=["requests", "aiohttp", "prettytable"],
)
