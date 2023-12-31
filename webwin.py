""" WebWin - Web UI with Python-backend

With WebWin, you can design GUI with modern HTML & javascript, implement
business logic with Python, call Python from javascript and vice versa, and
pack all into a small-size, stand-alone application.

NO Electron! The only requirement to run the packaged application is a modern
browser.

Author: Cataero Gong
https://github.com/cataerogong/webwin
Copyright (c) 2023 Cataero Gong
License: MIT (see LICENSE for details)
"""

import argparse
from collections.abc import Iterable
from datetime import datetime
import fnmatch
import inspect
import io
import json
import os
import pathlib
import re
import shlex
import socket
import string
import sys
import traceback
from typing import Dict, Iterable, List, Tuple
import chardet
from webui import webui


__version__ = "0.2.1"
VERSION = re.split(r'[\.\-_]', __version__)


def detect_enc(filename, default_encoding='ascii'):
    """ 自动识别文件编码

    :param default_encoding: (str) 万一没有识别出文件编码时使用的缺省编码
    """
    r = None
    with open(filename, 'rb') as f:
        d = chardet.UniversalDetector()
        for l in f:
            d.feed(l)
            if d.done:
                break
        r = d.close()
    # 经常把 GBK 识别成 GB2312，gb18030 > gbk > gb2312，所以 LEGACY_MAP 转换一下
    return (d.LEGACY_MAP.get(r['encoding'].lower(), r['encoding']) if r and r['encoding'] else default_encoding)

def open_any_enc(filename, mode='r', default_encoding='ascii'):
    """ open “自动识别文件编码”版本

    :param default_encoding: (str) 万一没有识别出文件编码时使用的缺省编码
    """
    return open(filename, mode, encoding=detect_enc(filename, default_encoding))

def is_port_valid(p: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', p))
        return True
    except OSError:
        return False
    finally:
        s.close()

def insert_str(html: str, insert: str, where: str = '</html>', *, forward: bool = False, before: bool = True) -> str:
    """ 在网页中搜索“定位字符串”，插入字符串

    搜索大小写无关；默认在网页末尾的 `</html>` 前插入。

    ~~~HTML
    <html>
    ...
    inserted string
    </html>

    Args:
        where (str): 定位字符串
        forward (bool): True: 正向查找，False: 反向查找
        before (bool): True: 插入在“定位字符串”之前，False: 之后
    ~~~
    """
    if forward:
        p = html.lower().find(where.lower())
    else:
        p = html.lower().rfind(where.lower())
    if p >= 0:
        if not before:
            p = p + len(where)
        html = html[:p] + insert + html[p:]
    return html

def append_js(html: str, js_file: str = '', js_str: str = '') -> str:
    """ 在网页 "</html>" 前插入 "载入 js_file 和 js_str" 的 <script> 语句

    ~~~HTML
    <script src="js_file"></script>
    <script>
    js_str
    </script>
    </html>
    ~~~

    Args:
        html (str): 待处理的 html
        js_file (str): js 文件 URL
        js_str (str): js 语句

    Returns:
        处理后的 html
    """
    if js_file:
        html = insert_str(html, f'<script src="{js_file}"></script>\n')
    if js_str:
        html = insert_str(html, f'<script>\n{js_str}\n</script>\n')
    return html

def comment_html(html: str, regex_to_comment: str, regex_flags = re.IGNORECASE) -> str:
    """ 注释掉网页内所有符合正则表达式的字符串

    `some string` => `<!-- some string -->`

    Args:
        html (str): 待处理的 html
        regex_to_comment (str): 正则表达式
        regex_flags: re.RegexFlag

    Returns:
        处理后的 html
    """
    for m in re.finditer(regex_to_comment, html, regex_flags):
        html = html[:m.start()] + '<!-- ' + html[m.start():m.end()] + ' -->' + html[m.end():]
    return html

def comment_js_file(html: str, js_file: str) -> str:
    """ 注释掉网页内加载 js_file 的语句

    `<script src="js_file"></script>` => `<!-- <script src="js_file"></script> -->`

    Args:
        html (str): 待处理的 html
        js_file (str): js 文件 URL 字符串，前面可以不写全，但结尾必须写完整。
                当然，字符串越短，匹配到的语句就越多，可能会造成错误的结果。
                对于 `<script src="/my/js/some_script.js"></script>` 来说，
                `/my/js/some_script.js`, `/js/script.js`, `js/script.js`,
                `script.js` 都可以匹配，但 `/my/js/some_script` 不行。

    Returns:
        处理后的 html
    """
    safe_str = js_file.replace('.', '\\.')
    return comment_html(html, f'''<script\\s+.+{safe_str}["']>\\s*</script>''')

def inject_webui_js(html: str) -> str:
    """ 在网页末尾增加载入 webui的 js 代码

    ~~~HTML
    <script src="/webui.js"></script>
    </html>
    ~~~
    """
    return append_js(html, js_file='/webui.js')

def webwin_wait():
    """ 等待所有窗口关闭 """
    webui.wait()

def webwin_exit():
    """ 关闭所有窗口 ，并释放 WebWin 资源

    调用后，WebWin 将不可使用
    """
    webui.exit()


class WebWin:
    """ 浏览器窗口 """

    WEBWIN_JS_TEMPLATE = '''
/**
* WebWin js
*
*/
var webwin = {
async _call_(fname, ...args) {
    try {
        let ret = JSON.parse(await webui.call(fname, JSON.stringify(args)));
        if (ret.status == "succ") { return ret.retval; }
        else { throw Error("Backend-Error: " + ret.msg); }
    } catch (e) {
        // console.log(e);
        throw e;
    }
},
/* Back-end exported objects and functions */

/*_WEBWIN_EXPOSE_END_*/
};
console.log('webwin.js loaded.');
'''

    WEBEIN_JS_EXPOSE_END = '/*_WEBWIN_EXPOSE_END_*/'

    def __init__(self,
                 webroot: str = '.',
                 port: int = 0,
                 browser: str = 'any',
                 size = (0, 0)
                 ):
        """
        Args:
            webroot: 网页根目录（基于当前路径的相对路径 或 绝对路径）
            port: 端口
            browser: 使用的浏览器
            size: 窗口大小(width, height), list or tuple
                  当前(webui2==2.4.5)， webui.window.set_size() 不是对所有浏览器生效，edge:ok, firefox:NO
        """
        self.webroot = webroot
        self.port = port
        self.browser = browser
        self.size = size
        self._webui_win = webui.window()
        self.webwin_js = self.WEBWIN_JS_TEMPLATE
        self._webwin_js_expose(f'_version_: "{__version__}",')

    @property
    def browser(self) -> str:
        return self._browser

    @browser.setter
    def browser(self, val: str):
        if val not in self.valid_browser_types():
            raise ValueError(f'invalid "browser" type: "{val}"')
        self._browser = val

    @property
    def _webui_browser(self) -> int:
        return webui.browser.__dict__.get(self._browser, webui.browser.any)

    @staticmethod
    def valid_browser_types() -> List[str]:
        """ “支持的浏览器类型”参数值列表 """
        return webui.browser.__annotations__.keys()

    def _bind_func(self, f, bindname):
        def wrapper(e: webui.event):
            args_j = e.window.get_str(e, 0)
            args = json.loads(args_j) if args_j else []
            try:
                retval = f(*args)
                return json.dumps({'status': 'succ', 'retval': retval}, ensure_ascii=False)
            except Exception as ex:
                return json.dumps({'status': 'fail', 'msg': repr(ex)}, ensure_ascii=False)
        self._webui_win.bind(bindname, wrapper)

    def _webwin_js_expose(self, js_str: str, end: str = '\n'):
        self.webwin_js = insert_str(self.webwin_js, js_str + end, where=self.WEBEIN_JS_EXPOSE_END)

    def _expose_func(self, f, bindname: str, jsname: str = ''):
        """ 在 webwinjs 中添加 js 函数 """
        docstring = '/*\n' + f.__doc__ + '\n */' if f.__doc__ else ''
        self._webwin_js_expose(f'''{docstring}
async {jsname or bindname}(...args) {{
    return await webwin._call_("{bindname}", ...args);
}},''')
        print(f'webwin exposed func: {bindname}')

    def bind_func(self, func, bindname: str = ''):
        """ 将 Python 函数提供给前端 js

        Args:
            func (callable): 函数
            bindname (str): 前端使用的函数名，默认为 func 的函数名
        """
        if not callable(func):
            raise TypeError(f'Not callable: {repr(func)}')
        if not bindname:
            bindname = func.__name__
        self._bind_func(func, bindname)
        self._expose_func(func, bindname)

    def bind_object(self, obj, bindname: str = ''):
        """ 将 Python 对象的方法提供给前端 js

        除了 `_` 开头的对象方法，其他都会提供给前端。

        Args:
            obj (callable): 对象
            bindname (str): 前端使用的对象名，默认为 obj 的类名小写
        """
        if not bindname:
            bindname = obj.__class__.__name__.lower()
        self._webwin_js_expose(bindname + ': {')
        for m in inspect.getmembers(obj, predicate=lambda x: inspect.ismethod(x) and not x.__name__.startswith('_')):
            funcbindname = f'{bindname}.{m[0]}'
            funcjsname = m[0]
            self._bind_func(m[1], funcbindname)
            self._expose_func(m[1], bindname=funcbindname, jsname=funcjsname)
        self._webwin_js_expose('},')
        print(f'webwin exposed object: {bindname}')

    def inject_webwin_js(self, html: str) -> str:
        """ 在 html 末尾增加载入 webwin 的 js 代码 """
        return append_js(html, js_str=self.webwin_js)

    def _prepare_webui(self):
        self._webui_win.set_port(self.port)
        self._webui_win.set_root_folder(self.webroot)
        self._webui_win.set_size(self.size[0], self.size[1])

    def show_html(self, html: str, append_webui_js: bool = True, append_webwin_js: bool = True):
        """ 打开浏览器并展示 html 字符串

        Args:
            html (str): HTML 字符串
            append_webui_js (bool): 是否在 HTML 末尾插入 webui 功能 js 代码。
        """
        html = insert_str(html, '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />', '<head>', forward=True, before=False)
        if append_webui_js:
            html = inject_webui_js(html)
        if append_webwin_js:
            html = self.inject_webwin_js(html)
        self._prepare_webui()
        self._webui_win.show(html, self._webui_browser)
        self.run_js('if ("on_webwin_loaded" in window && window.on_webwin_loaded) { window.on_webwin_loaded(); }')

    def show_file(self, html_file: str = 'index.html', append_webui_js: bool = True, append_webwin_js: bool = True):
        """ 打开浏览器并展示 html 文件

        Args:
            html_file (str): HTML 文件路径（基于网页根目录的相对路径 或者 绝对路径）
            append_webui_js (bool): 是否在 HTML 末尾插入 webui 功能 js 代码。
        """
        with open_any_enc(os.path.normpath(os.path.join(self.webroot, html_file))) as f:
            html = str(f.read())
        self.show_html(html, append_webui_js, append_webwin_js)

    def run_js(self, js: str):
        """ 在网页执行 js 脚本（在浏览器窗口显示后才可调用本方法）

        Args:
            js (str): js 脚本字符串

        Returns:
            (any) js return value

        Raises:
            Exception: js error
        """
        res = self._webui_win.script(js)
        if res.error is True:
            raise Exception(f'webui run js error: {repr(res.data)}')
        return res.data

    def run_js_file(self, js_file: os.PathLike):
        """ 在网页执行 js 文件（在浏览器窗口显示后才可调用本方法）

        Args:
            js_file (PathLike): js 脚本文件路径（基于当前目录的相对路径 或 绝对路径）

        Returns:
            (any) js return value

        Raises:
            FileNotFoundError:
            Exception: js error
        """
        if not os.path.exists(js_file):
            raise FileNotFoundError(js_file)
        with open_any_enc(js_file) as f:
            print(f'webui run js: {js_file}')
            res_data = self.run_js(str(f.read()))
            self.run_js(f'console.log("{os.path.basename(js_file)} loaded.");')
            return res_data

    def close(self):
        """ 关闭窗口

        窗口可重用
        """
        self._webui_win.close()

    def destroy(self):
        """ 销毁窗口

        窗口不可重用
        """
        self._webui_win.destroy()


class FileSystem:
    def get_roots(self) -> List[str]:
        """ 获取所有根目录

        Returns:
            在 win 平台，返回所有有效盘符列表（包括":\\"）
            在其他平台，返回 ['/']
        """
        if os.name == 'nt':
            return [d+':\\' for d in string.ascii_uppercase if os.path.exists(d+':\\')]
        # elif os.name == 'posix':
        #     return ['/']
        else:
            return ['/']

    def ls(self, dir: str, pattern: str = '', type: str = '') -> List[Dict]:
        """ 列出目录下文件和子目录
        
        Args:
            dir (str): 根目录
            pattern (str): 匹配模板，支持 '*' 和 '?'
            type (str): 限定类型，'dir':目录，'file':文件，'symlink':符号链接

        Returns:
            字典对象列表，字典键值：name, fullpath, type, size, ctime, mtime, atime
        """
        if pathlib.Path(dir).is_dir():
            ret = []
            with os.scandir(dir) as lst:
                for e in lst:
                    stat = e.stat()
                    node = {'name': e.name,
                            'fullpath': e.path,
                            'type': 'file' if e.is_file() else 'dir' if e.is_dir() else 'symlink' if e.is_symlink() else '',
                            'size':stat.st_size,
                            'ctime': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                            'mtime': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                            'atime': datetime.fromtimestamp(stat.st_atime).strftime('%Y-%m-%d %H:%M:%S'),
                            }
                    if (not pattern or fnmatch.fnmatch(e.name, pattern)) and (not type or node['type'] == type.lower()):
                        ret.append(node)
            return ret
        else:
            raise FileNotFoundError(dir)

    def cwd(self) -> str:
        """ 获取当前目录 """
        return os.path.abspath(os.getcwd())

    def readfile(self, path: str, encoding: str = "") -> str:
        """ 读文件
        
        Args:
            path (str): 文件路径
            encoding (str): 文件编码，为空时自动检测

        Returns:
            (str) 文件内容
        """
        if pathlib.Path(path).is_file():
            if encoding:
                with open(path, encoding=encoding) as f:
                    return f.read()
            else:
                with open_any_enc(path) as f:
                    return f.read()
        raise FileNotFoundError(path)

    def writefile(self, path: str, text: str, mode: str = 'w', encoding: str = "utf-8"):
        """ 写文件

        Args:
            path (str): 文件路径
            text (str): 写入内容
            mode (str): 写入模式，'w':overwrite, 'a':append
            encoding (str): 文件编码，默认："utf-8"
        """
        with open(path, mode, encoding=encoding) as f:
            return f.write(text)

    def removefile(self, path: str):
        """ 删除文件

        Args:
            path (str): 文件路径
        """
        if pathlib.Path(path).is_file():
            os.remove(path)
        raise FileNotFoundError(path)


class DualOutputIO(io.StringIO):
	""" 双路输出IO

	仅支持输出，用来替换stdout, stderr。

	输出模式：
		1、【单独】：输出到主IO，当主IO为None时，输出到备IO；
		2、【同时】；
		3、【丢弃】：两路IO均为None时，丢弃输出信息。
	"""

	def __init__(self, io_1: io.StringIO, io_2: io.StringIO, both: bool = False):
		""" 双路输出IO

		输出模式：
			1、【单独】：输出到主IO，当主IO为None时，输出到备IO；
			2、【同时】；
			3、【丢弃】：两路IO均为None时，丢弃输出信息。

		Args:
			io_1: 主用输出IO
			io_2: 备用输出IO
			both: 是否同时输出
		"""
		super().__init__()
		self._io_1 = io_1
		self._io_2 = io_2
		self.both = both

	def _io_1_write(self, s: str):
		return self._io_1.write(s) if self._io_1 else 0

	def _io_2_write(self, s: str):
		return self._io_2.write(s) if self._io_2 and (self.both or not self._io_1) else 0

	def write(self, s: str):
		r1 = self._io_1_write(s) 
		r2 = self._io_2_write(s)
		return r1 or r2

	def _io_1_writelines(self, lines):
		if self._io_1:
			self._io_1.writelines(lines)

	def _io_2_writelines(self, lines):
		if self._io_2 and (self.both or not self._io_1):
			self._io_2.writelines(lines)

	def writelines(self, lines: Iterable[str]):
		self._io_1_writelines(lines)
		self._io_2_writelines(lines)


class FileLog(io.StringIO):
    def __init__(self, filename: str):
        super().__init__()
        self.filename = filename

    def write(self, __s: str) -> int:
        with open(self.filename, 'a') as f:
            return f.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ' + __s)

    def writelines(self, __lines: Iterable[str]) -> None:
        with open(self.filename, 'a') as f:
            return f.writelines(__lines)


class WebWinAppArgs(argparse.Namespace):
    def __init__(self,
                    webroot='',
                    mainpage='index.html',
                    port=0,
                    browser='any',
                    size=(0, 0),
                    del_js=[],
                    run_js=[]):
        self.webroot = webroot
        self.mainpage = mainpage
        self.port = port
        self.browser = browser
        self.size = size
        self.del_js = del_js
        self.run_js = run_js

    @staticmethod
    def browser_type(s: str) -> str:
        if s not in WebWin.valid_browser_types():
            raise argparse.ArgumentTypeError(f'invalid "browser" value: "{s}"')
        return s

    @staticmethod
    def size_type(s: str) -> Tuple[int, int]:
        ret = [int(x) for x in s.split(',')]
        if len(ret) == 1:
            ret.append(ret[0])
        if len(ret) != 2:
            raise argparse.ArgumentTypeError(f'invalid "size" value: "{s}"')
        return tuple(ret)


class WebWinApp:
    class ArgParser(argparse.ArgumentParser):
        def __init__(self, *args, **kwargs):
            self._wwa_args = dict()
            self._wwa_built = False
            self._wwa_app_info = ('', '', '')
            super().__init__(*args, **kwargs)

        def _webwin_show_msg(self, msg: str = ''):
            webui.window().show(inject_webui_js(f'''<html>
                <head><meta charset="UTF-8" /><title>{self._wwa_app_info[0]} v{self._wwa_app_info[1]}</title></head>
                <body style="background:#fdf3df;">{msg or '<h2>{0}</h2><p>{2}</p>'.format(*self._wwa_app_info)}
                <hr><pre style="font-size:1rem;color:gray;">{self.format_help()}</pre>
                </body>
                </html>'''))
            webui.wait()

        def print_help(self, file=None):
            self._webwin_show_msg()

        def exit(self, status=0, message=None):
            if message:
                self._webwin_show_msg(message)
            sys.exit()

        def error(self, message):
            self.exit(2, f'<h1>ERROR</h1>{message}')

        def add_argument(self, *args, **kwargs):
            """ 添加参数项

            以第一个参数名判断是否已存在，如已存在，则完全替换原有参数项。

            如想修改原有参数项的某些设置，请用 `mod_argument`。
            """
            # if no positional args are supplied or only one is supplied and
            # it doesn't look like an option string, parse a positional
            # argument
            chars = self.prefix_chars
            if not args or len(args) == 1 and args[0][0] not in chars:
                if args and 'dest' in kwargs:
                    raise ValueError('dest supplied twice for positional argument')
                kw = self._get_positional_kwargs(*args, **kwargs)
                name = kw['dest']

            # otherwise, we're adding an optional argument
            else:
                kw = self._get_optional_kwargs(*args, **kwargs)
                name = kw['option_strings'][0]
            # print('add_arg:', name)
            self._wwa_args[name] = (args, kwargs)

        def mod_argument(self, first_arg_name, **kwargs):
            """ 修改参数项设置

            只能修改参数项的 keyword args。如果参数项不存在，则不作操作。

            Args:
                first_arg_name (str): 第一个参数名，例如 `add_argument('-i', '--info', ...)` 对应 `-i`
            """
            # print('mod_arg:', first_arg_name)
            arg = self._wwa_args.get(first_arg_name, None)
            if arg:
                arg[1].update(kwargs)

        def del_argument(self, first_arg_name):
            """ 删除参数项

            Args:
                first_arg_name (str): 第一个参数名，例如 `add_argument('-i', '--info', ...)` 对应 `-i`
            """
            # print('del_arg:', arg_name)
            self._wwa_args.pop(first_arg_name, None)

        @property
        def args_list(self):
            """ 当前已添加的参数项名列表

            如果一个参数项设置了多个参数名，则取第一个，例如 `add_argument('-i', '--info', ...)` 对应 `-i`
            """
            return self._wwa_args.keys()

        def build_parser(self):
            """ 生成实际的参数解析器（只能调用一次） """
            if not self._wwa_built:
                for n, v in self._wwa_args.items():
                    super().add_argument(*v[0], **v[1])
                self._wwa_built = True


    def __init__(self,
                 app_name: str = '',
                 app_ver:str = '1.0.0',
                 app_desc: str = '',
                 args: WebWinAppArgs = WebWinAppArgs(),
                 webroot_bundled: bool = False,
                 enable_args_file: bool = True,
                 enable_cmdline_args: bool = True):
        self._build_base_paths()
        self.APP_NAME = app_name or self.PROG_NAME
        self.APP_VER = app_ver
        self.APP_DESC = app_desc
        self.help_msg = app_desc
        self.webroot_bundled = webroot_bundled
        sys.stdout = DualOutputIO(sys.stdout, None)
        sys.stderr = DualOutputIO(sys.stderr, FileLog(self.LOG_FILE), True)
        self._enable_args_file = enable_args_file
        self._enable_cmdline_args = enable_cmdline_args
        self._mainwin = WebWin()
        self.args = args
        self.argparser = WebWinApp.ArgParser(allow_abbrev=False)
        self.argparser._wwa_app_info = (self.APP_NAME, self.APP_VER, self.APP_DESC)

    @property
    def mainwin(self) -> WebWin:
        """ WebWin 窗口对象 """
        if not self._mainwin:
            self._mainwin = WebWin()
        return self._mainwin

    def _build_base_paths(self):
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):  # 判断当前执行程序是否是 PyInstaller 打包后的 exe
            self.PROG_FILE = os.path.abspath(sys.executable)
            self.BUNDLE_DIR = sys._MEIPASS
        else: # .py
            self.PROG_FILE = os.path.abspath(sys.argv[0])
            self.BUNDLE_DIR = os.path.dirname(self.PROG_FILE)
        self.PROG_NAME = os.path.splitext(os.path.basename(self.PROG_FILE))[0]
        self.PROG_DIR = os.path.dirname(self.PROG_FILE)
        self.ARGS_FILE = os.path.join(self.PROG_DIR, self.PROG_NAME + '.args')
        self.LOG_FILE = os.path.join(self.PROG_DIR, self.PROG_NAME + '.log')
        self.CUR_DIR = os.path.abspath(os.getcwd())

    def log(self, msg: str):
        """ 记录信息（输出到sys.stdout） """
        print(msg, file=sys.stdout)

    def log_err(self, msg: str):
        """ 记录错误信息（输出到sys.stderr） """
        print(msg, file=sys.stderr)

    def log_exc(self):
        """ 记录 Exception Traceback 信息（输出到sys.stderr） """
        print(traceback.format_exc(), file=sys.stderr)

    @property
    def logging_to_console(self) -> bool:
        return self._log2console

    @logging_to_console.setter
    def logging_to_console(self, val: bool):
        self._log2console = val

    @property
    def logging_to_file(self) -> bool:
        return self._log2file

    @logging_to_file.setter
    def logging_to_file(self, val: bool):
        self._log2file = val

    def _parse_args(self):
        """ 从 参数文件 和 命令行 读取参数

        参数文件：程序目录下，与程序同名的 `.args` 文件（`程序名.args`）

        优先级：命令行 > 参数文件
        """
        args = []
        if self._enable_args_file and os.path.exists(self.ARGS_FILE):
            with open_any_enc(self.ARGS_FILE) as f:
                s = f.read()
            args = [s.strip('"') for s in shlex.split(s, comments=True, posix=(os.name == 'posix'))]
            self.log(f'args file: {args}')
        if self._enable_cmdline_args:
            self.log(f'args cmdline: {sys.argv[1:]}')
            args.extend(sys.argv[1:])
        self.argparser.parse_args(args, namespace=self.args)
        self.log(f'args: {self.args}')

    def adjust_argparser(self):
        """ （可重载）调整参数解析器

        使用 `self.argparser` (WebWinApp.ArgParser) 的 `add_argument()`, `mod_argument` 和 `del_argument` 增加、删除、修改参数设置
        """
        pass

    def _prepare_argparser(self):
        self.argparser.add_argument('--webroot', default='', help='网页根目录（相对或绝对路径）[默认: 当前目录]')
        self.argparser.add_argument('--mainpage', metavar='HTML_FILE', default='index.html', help='应用主页 [默认: index.html]')
        self.argparser.add_argument('--port', type=int, default=0, help='端口 [默认: 随机]')
        self.argparser.add_argument('--browser', type=WebWinAppArgs.browser_type, default='any', help=f'使用的浏览器（必须是本机已安装的）[默认: 系统缺省浏览器][可选项: {", ".join(self.mainwin.valid_browser_types())}]')
        # webui.window.set_size() 不是对所有浏览器生效，edge:ok, firefox:NO (webui2==2.4.5)
        # self._argparser.add_argument('--size', metavar='WIDTH,HEIGHT', type=WebWinAppArgs.size_type, default=(0, 0), help='窗口大小 [默认: 上次运行时大小]')
        self.argparser.add_argument('--del-js', metavar='DEL.JS', nargs='*', default=[], help='禁止主页加载 js 脚本文件')
        self.argparser.add_argument('--run-js', metavar='PATH/RUN.JS', nargs='*', default=[],  help='加载后执行 js 脚本文件（相对或绝对路径）')
        self.argparser.epilog = '【*注意*】如果网页会用到浏览器存储（如cookie,LocalStorage,indexdb），则必须指定端口(--port)'
        self.adjust_argparser()
        self.argparser.build_parser()

    def apply_args(self):
        """ （可重载）应用参数

        通过 `self.args` (WebWinAppArgs) 访问保存解析后参数值，可以修改参数值

        ```
        class SubApp(WebWinApp):
            def apply_args(self):
                self.args.some_arg = 'new value'
                super().apply_args()
        ```
        """
        if self.webroot_bundled:
            self.args.webroot = os.path.normpath(os.path.join(self.BUNDLE_DIR, self.args.webroot))
        else:
            self.args.webroot = os.path.normpath(os.path.join(self.CUR_DIR, self.args.webroot))
        self.args.mainpage = os.path.normpath(os.path.join(self.args.webroot, self.args.mainpage))

    def bind_all(self):
        """ （可重载）将 Python 对象和函数方法提供给前端 js

        调用 `self.mainwin.expose_object()` 和 `self.mainwin.expose_func()`
        """
        self.mainwin.bind_object(FileSystem(), 'fs')

    def show_msg_page(self, msg: str='', add_help_msg: bool=True):
        self.mainwin.show_html(f'''<html>
            <head><meta charset="UTF-8" /><title>{self.APP_NAME} v{self.APP_VER}</title></head>
            <body style="background:#fdf3df;">{msg}<hr>
            <pre style="font-size:1rem;color:gray">{self.help_msg if add_help_msg else ''}</pre></body>
            </html>''')

    def run(self):
        """ 获取参数，打开窗口显示网页 """
        try:
            if (self._enable_args_file or self._enable_cmdline_args):
                self._prepare_argparser()
                self.help_msg = self.argparser.format_help()
                self._parse_args()
                self.apply_args()
            if self.args.port and not is_port_valid(self.args.port):
                self.mainwin.port = 0
                self.show_msg_page(f'<h1>端口被占用！</h1>【端口】{self.args.port}')
            elif self.args.port and self.args.port < 1024:
                self.mainwin.port = 0
                self.show_msg_page(f'<h1>不能使用小于 1024 的特权端口！</h1>【端口】{self.args.port}')
            elif not os.path.exists(self.args.mainpage):
                self.show_msg_page(f'<h1>应用主页文件不存在！</h1>【网页根目录】{self.args.webroot}<br />【应用主页】{self.args.mainpage}')
            else:
                self.mainwin.webroot = self.args.webroot
                self.mainwin.port = self.args.port
                self.mainwin.browser = self.args.browser
                self.mainwin.size = self.args.size
                self.bind_all()
                with open_any_enc(self.args.mainpage) as f:
                    html = f.read()
                for js in self.args.del_js:
                    html = comment_js_file(html, js)
                self.mainwin.show_html(html)
                for js in [os.path.normpath(os.path.join(self.CUR_DIR, j)) for j in self.args.run_js]:
                    try:
                        self.mainwin.run_js_file(js)
                    except:
                        self.log_exc()
        except Exception as e:
            if not isinstance(e, SystemExit):
                self.log_exc()

    def wait(self):
        """ 等待*所有*窗口关闭 """
        try:
            webwin_wait()
        except:
            self.log_exc()

    def exit(self):
        """ 关闭所有窗口，并释放 WebWin 资源

        调用后，WebWin 将不可使用
        """
        try:
            webwin_exit()
        except:
            self.log_exc()

if __name__ == '__main__':
    app = WebWinApp()
    app.run()
    app.wait()
