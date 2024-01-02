@echo off

if "%1"=="" goto :build
goto :%1

:build
	python setup.py bdist_wheel --python-tag py3
	exit /b

:clean
	if exist __pycache__ rd /s /q __pycache__
	if exist webwin.egg-info rd /s /q webwin.egg-info
	if exist build rd /s /q build
	if exist dist rd /s /q dist
	exit /b

:rebuild
	call :clean
	call :build
	exit /b
