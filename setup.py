from setuptools import setup

import webwin

setup(
    name="webwin",
    version=webwin.__version__,
    py_modules=['webwin'], # only one python file

    # 表明当前模块依赖哪些包，若环境中没有，则会从pypi中下载安装
    install_requires=['webui2==2.4.5',
                      'chardet>=5.0',
                      'pyinstaller>=6.0'],
    # 限定 python 版本
    python_requires='>=3.8',
    # install_requires 在安装模块时会自动安装依赖包
    # 而 extras_require 不会，这里仅表示该模块会依赖这些包
    # 但是这些包通常不会使用到，只有当你深度使用模块时，才会用到，这里需要你手动安装
    # extras_require={
    #     'pack':  ["ReportLab>=1.2", "RXP"],
    #     'reST': ["docutils>=0.3"],
    # }

    # metadata to display on PyPI
    author="Cataerog Gong",
    author_email="cataerogong@hotmail.com",
    description="Web UI with Python backend",
    keywords="web ui javascript js python backend",
    url="https://github.com/cataerogong/webwin",   # project home page, if any
    project_urls={
        "Bug Tracker": "",
        "Documentation": "",
        "Source Code": "https://github.com/cataerogong/webwin",
    },
    classifiers=[
        # 发展时期,常见的如下
        'Development Status :: 4 - Beta',
        # 开发的目标用户
        'Intended Audience :: Developers',
        # 许可证信息
        'License :: OSI Approved :: MIT License',
        # 使用的自然语言
        'Natural Language :: Chinese (Simplified)',
        # 目标 Python 版本
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: Implementation :: CPython',
        # 属于什么类型
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',

    ],
    license='MIT License',

    # could also include long_description, download_url, etc.
    # entry_points={
    #     'console_scripts': [
    #         'pkgtree = pkgtree:main',
    #     ]
    # }
)