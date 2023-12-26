## v0.2.0-alpha

* [+] add `FileSystem` class to provide simple FS operation.

  `WebWinApp` exports an instance of it with name `fs` by default.

* [!] bugfix: use `list`, `tuple`, `dict` in type annotation is not supported in python 3.8

* [+] add `wheel` release.

* [*] redirect `stdout` & `stderr` in `WebWinApp`.

  Now it can run with `pythonw`.

## v0.1.2

* [+] show app info in help page

## v0.1.1

* [!] bugfix: create WebWin object with error arg in WebWinApp

* [!] bugfix: not strip the quote char in args-file

## v0.1.0

* window class `WebWin`:
  * export python functions and objects to js
  * display web page and auto inject `webwin & webui front-end js`
  * run js from python

* frontend:
  * call python from js like native js

* app class `WebWinApp`:
  * support cmdline-args & args-file
  * run pure html+js SPA like local application without coding
  * well-prepared overridable methods for implementing business logic
