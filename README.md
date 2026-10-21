# Wlan-Flash-Transfer-V2（PyQt6 版）

局域网文件互传桌面端 **v2** —— PyQt6 重写版,深色开发者工具风格(样式参考 TCode GUI)。
任意设备浏览器打开地址即可上传/下载/分享/聊天;桌面端负责启停服务、选目录、看日志、扫码。
**原 v1(tkinter 版)保留在 `../lan-file-transfer/`,本目录独立,互不影响。**

> 📖 文档:[使用说明](docs/使用说明.md) · [技术实现文档](docs/技术实现文档.md) · [网页端图文教程](docs/保姆级使用教程v3.html)

## 界面

**桌面端(PyQt6)**

- 顶部品牌区 + 「服务 / 聊天」双 Tab(服务页右侧:二维码 + 服务日志)+ 状态栏 + 系统托盘
- 状态徽标(○ 已停止 / ● 启动中 / ● 运行中)、蓝色主按钮 `#2e70ef`
- **屏上二维码**:启动后直接显示访问地址二维码,手机扫码直达(纯标准库 `qrterm` 生成)
- 共享文件表:大小/修改时间,行内「预览 / 复制」按钮,双击行直接打开,支持「删除选中」
- 聊天 Tab 实时镜像网页端消息;关窗自动收到托盘,服务保持运行

**网页端(布局E,桌面/手机自适应)**

- 桌面(>980px):左右等宽分栏 —— 上传/共享文件在左,聊天室在右,两列底部对齐
- 手机(≤980px):文件优先单列,右下角 💬 悬浮球聊天(未读角标),点开为全宽底部面板
- 上传:点击 / 拖拽 / 粘贴(Ctrl+V)三合一,独立进度条 + 实时速度
- 共享文件:分页展示(每页 8 个)、最新/名称/大小排序;**三色操作按钮**(蓝下载 / 灰删除 / 绿分享)
- 分享:手机调起系统分享面板;电脑一键复制下载链接
- 聊天:昵称按设备自动生成并记忆,头像由昵称映射 emoji(各端一致);桌面「聊天」Tab 实时镜像

## 结构

```
main.py                    入口(--smoke 自检 / --screenshot 截图 / GUI)
lan-transfer-v2.spec       PyInstaller 配置(mac .app / win 单文件 exe, 含产物瘦身过滤)
build.sh / build_windows.bat
docs/                      使用说明 / 技术实现文档 / 图文教程(HTML, 含截图)
design/                    网页端设计稿(可直接双击预览, 内置演示数据)
lan_transfer/
├── core/
│   ├── server.py          TransferServer(实例态服务: 上传/下载/删除/聊天/日志回调)
│   └── webui.py           Web 页面(布局E 单页应用, 桌面/移动自适应, 零外部资源)
├── qrterm.py              零依赖二维码(终端 + QPixmap 渲染共用)
└── gui/
    ├── theme.py           深色 QSS(参考 tcode)
    ├── workers.py         Worker(QThread)
    ├── widgets.py         表格 / 徽标 / 等宽字体
    └── main_window.py     主窗口
```

相对 v1 的核心变化:

| | v1 | v2 |
|---|---|---|
| GUI | tkinter | **PyQt6**(tcode 深色风格 + 托盘常驻) |
| 服务 | 嵌在 GUI 文件里,模块级全局状态 | **TransferServer 实例**(回调式日志/聊天,Qt 信号桥回主线程) |
| 二维码 | 仅网页端(需联网 API) | **桌面屏上直接显示**(本地生成,零联网) |
| 网页端 | 单列旧版页面 | **布局E**:等宽分栏 / 手机悬浮聊天 / 分页 / 分享 / emoji 头像 |
| 安全 | 文件名仅取 basename | basename + **resolve 路径越界双重校验** |

## 开发与打包

```bash
pip3 install -r requirements.txt   # PyQt6 + PyInstaller
python3 main.py                    # 开发运行
python3 main.py --smoke            # 无头自检(起服务 -> 请求接口 -> 停止)
python3 main.py --screenshot s.png # 无头渲染截图
bash build.sh                      # macOS → dist/Wlan-Flash-Transfer-V2.app(含 frozen 冒烟)
build_windows.bat                  # Windows → dist\Wlan-Flash-Transfer-V2.exe(单文件)
```

打包产物免安装(自带运行时);分发被 Gatekeeper 拦截时:
`xattr -dr com.apple.quarantine dist/Wlan-Flash-Transfer-V2.app`。

打包配置已做**产物瘦身**(剔除未使用的 Qt 组件/插件/翻译文件 + macOS strip):
mac .app 74MB → **56MB(-24%)**;修改 spec 过滤清单后务必 `--smoke` + `--screenshot` 双验证
(conda Python 的 QtGui 硬链接 QtDBus,不可剔除,详见 spec 内注释)。

## 使用

1. 启动服务(默认端口 8765,可改);手机扫右侧二维码或浏览器输入地址
2. 网页端:拖拽/点选/粘贴上传、下载、删除、**分享**(手机系统分享面板 / 电脑复制链接)、
   实时聊天(桌面端「聊天」Tab 同步可见)
3. 上传前自动检查磁盘空间;桌面端可随时在文件表里管理共享目录内容
4. 浏览器兼容:支持 2017 年以后的现代内核(Chrome 55+ / Safari 10.1+ 及其国产套壳)
