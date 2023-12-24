import argparse
from time import sleep
from webwin import WebWin, WebWinApp, webwin_exit

def swap(a, b):
    print('swap():', a, b)
    return [b, a]

class World:
    def __init__(self, myname):
        self.myname = myname

    def set_name_1(self, name):
        self.name_1 = name

    def set_name_2(self, name):
        self.name_2 = name

    def hello(self):
        return f"Hello, <name>{self.name_1}</name>!<br /> Hello, <name>{self.name_2}</name>!<br /> I'm <name>{self.myname}</name>."

class DemoApp(WebWinApp):
    def adjust_argparser(self):
        super().adjust_argparser()
        # 修改参数项设置
        self.argparser.mod_argument('--port', required=True, help='端口 [必须]') # 从可选改为必须
        self.argparser.mod_argument('--browser', help=argparse.SUPPRESS) # 从帮助信息中隐藏该参数项，但依旧可用
        # 删除参数项，用 WebWinApp.Args 的默认值
        self.argparser.del_argument('--size') # 该参数用户不可设置，用默认值
        self.argparser.del_argument('--del-js') # 该参数用户不可设置，用默认值
        self.argparser.del_argument('--run-js') # 该参数用户不可设置，用默认值
        # 删除参数项，后面会设置固定值
        self.argparser.del_argument('--webroot') # 该参数用户不可设置，webroot 为固定值
        self.argparser.del_argument('--mainpage') # 该参数用户不可设置，mainpage 为固定值
        # 增加参数项
        self.argparser.add_argument('-n', '--name', default='WebWin', help='名字 [default: WebWin]')
        self.argparser.epilog = '' # clear epilog

    def apply_args(self):
        # 设置参数固定值
        self.args.webroot = '.'
        self.args.mainpage = 'demo.html'
        # 修改用户输入的参数
        if self.args.name != 'WebWin':
            self.args.name = self.args.name + ' WebWin'
        super().apply_args()
        print('webroot', self.mainwin.webroot)

    def bind_all(self):
        super().bind_all()
        self.mainwin.bind_func(swap)
        self.mainwin.bind_object(World(self.args.name))

# 打包时会把前端网页一起打包，因此需要：
# 创建 App 时启用 webroot 包内定位标志：
#   app = DemoApp('WebWin Demo', webroot_bundled=True)
# 或者 把网页根目录指定到包内的绝对路径：
#   在 apply_args() 函数中：self.args.webroot = self.BUNDLE_DIR
app = DemoApp('WebWin Demo', webroot_bundled=True)
app.run()
# sleep(2)
# print('close...')
# app._mainwin.close()
# app.wait()
# print('closed')

# sleep(2)
# print('run again')
# app.run()
# sleep(2)
# print('destroy...')
# app._mainwin.destroy()
# app.wait()
# print('destroyed')

# sleep(2)
# print('run again (can not open any window)')
# app.run()
app.wait()
print('Bye-bye')
