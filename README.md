# webwin - Web UI with Python-backend


## webwin 能干啥？

* 用 HTML & javascript 设计 UI 交互，用 Python 实现业务逻辑
* javascript 调用 Python 函数，Python 执行 javascript 代码
* 可以把你的应用打包成一个小尺寸的独立程序，便于分发
* NO Electron! 运行打包后的程序运行简单，一点即开，只需要有浏览器（无需用户提前打开）
* 对于那种 Single-Page-Application (SPA) 的网页应用，再不用自建 web 服务来运行了，可以很方便地把它变成如单机程序般易于使用


## 缘起

0. 经常有些小需求，没有现成应用可以完成，想自己写个程序，于是 ……

1. 编程语言？

   我会 Python，处理数据能力很强大，还有打包工具可以打包成独立程序，给别人使用也很方便，不用安装。很好，就用 Python 吧！

2. GUI？

   不是所有需求都适合 `命令行` 这种运行模式，有些需求还是要 GUI 操作界面的，那就看看 Python 的 GUI 库吧 …… Tkinter，Python 自带，太弱太难用；PyQt/PySide2，强大，打包后体积太大；wxPython，好像不太好用；PySimpleGUI，体积小，功能还是有点弱，但还行 …… 暂时先用 PySimpleGUI 凑合着。

3. Web page + REST API？

   开发了一些小型的 网页 + REST API 后端 的项目，渐渐觉得这个模式不错哎，前端 HTML + javascript 提供 UI 展示、交互，后端实现业务逻辑，不错不错。但是，用来开发单机小工具还是重了点，每次使用，都要开后端、开浏览器、输地址，烦。

   到了这步，Electron？后端实现业务逻辑的能力还是没有 Python 强（pandas ...），听说打包后的程序巨大无比，再加上懒病发作，学习能力减弱，Electron 啊，看看就好了 ……

4. webui

   发现了一个好东西：[webui](https://github.com/webui-dev/webui)，把 后端服务、前后端通讯、浏览器设置 都封装了，还贴心地提供了 [Python 版本](https://github.com/webui-dev/python-webui)。

   试试 …… 还不错哎，写出来的应用就像单机程序一样，点一下就开，打包后的程序也很小。
   
   嗯，用它来试试吧。

5. WebWin

   webui 用起来还是有点糙，在外面再包一层，让它用起来更顺一点 ……

   程序员么，总想着自己造轮子，造不了新轮子，也要在旧轮子上打几个补丁，所以就有了这个项目 ^_^


## 预警

由于 webui 还在不停开发中，估计接口还会有变化，我也会试着跟随改进，但万一哪天懒病发作，那就 ……

因此，我会写明我开发使用的依赖版本，请注意。


## 安装

目前只能直接把源码直接放到项目下调用，暂没有 pip install

源码: `webwin.py`

依赖: （可能有变化，具体见 `requirements.txt`）

* python >= 3.8

* webui2==2.4.5  （至少2.4.5）
* pyinstaller （版本应该关系不大）
* chardet  （版本应该关系不大）


## 用法

### 极简

```python
from webwin import WebWin, webwin_wait

def hello(name):
    print(f'From js: {name}')
    return f'Hello, {name}!'

win = WebWin()
win.bind_func(hello)
win.show_html('''<html>
<body>
name: <input type="text" id="name" />
<button onclick="say_hello()">hello</button>
<script>
async function say_hello() {
  alert(await webwin.hello(document.getElementById("name").value));
}
</script>
</body>
</html>''')
webwin_wait()
```

### demo

将 `demo.html`, `demo.py`, `webwin.py` 放到同一个目录下，执行以下命令：

 --     | 命令
 --     | --
正常运行 | `python demo.py --port 8008`
显示帮助 | `python demo.py -h`
参数错误 | `python demo.py`


## 打包

我是用 PyInstaller 打包，`WebWinApp` 类支持从打包后的包内路径读取文件，这样就可以把所有前端网页资源也一起打包进最终的程序文件，打包成一个单文件应用程序。

打包时需要设置参数 `--add-data` 来把网页资源一起打包。

```sh
pyinstaller -F -c --hide-console hide-early --collect-binaries webui --add-data demo.html:. demo.py
```

## License

This project is licensed under the terms of the MIT license.
