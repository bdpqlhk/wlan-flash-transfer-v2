# LAN 文件传输 v2（PyQt6 版）

局域网 AirDrop 桌面端 **v2** —— PyQt6 重写版,深色开发者工具风格(样式参考 TCode GUI)。
任意设备浏览器打开地址即可上传/下载/聊天;桌面端负责启停服务、选目录、看日志、扫码。
**原 v1(tkinter 版)保留在 `../lan-file-transfer/`,本目录独立,互不影响。**

> 📖 文档:[使用说明](docs/使用说明.md) · [技术实现文档](docs/技术实现文档.md)

## 界面

- 顶部品牌区 + 「服务 / 聊天」双 Tab(服务页右侧:二维码 + 服务日志;共享文件表拉伸到底)+ 状态栏
- 状态徽标(○ 已停止 / ● 启动中 / ● 运行中)、蓝色主按钮 `#2e70ef`
- **屏上二维码**:启动后直接显示访问地址二维码,手机扫码直达(纯标准库 `qrterm` 生成)
- 共享文件表:大小/修改时间,双击打开,支持删除;聊天 Tab 实时镜像网页端消息

## 结构

```
main.py                    入口(--smoke 自检 / --screenshot 截图 / GUI)
lan-transfer-v2.spec       PyInstaller 配置(mac .app / win 单文件 exe)
build.sh / build_windows.bat
lan_transfer/
├── core/
│   ├── server.py          TransferServer(实例态服务: 上传/下载/删除/聊天/日志回调)
│   └── webui.py           Web 页面(原样复用 v1 单页应用)
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
| GUI | tkinter | **PyQt6**(tcode 深色风格) |
| 服务 | 嵌在 GUI 文件里,模块级全局状态 | **TransferServer 实例**(回调式日志/聊天,Qt 信号桥回主线程) |
| 二维码 | 仅网页端(需联网 API) | **桌面屏上直接显示**(本地生成,零联网) |
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

## 使用

1. 启动服务(默认端口 8765,可改);手机扫右侧二维码或浏览器输入地址
2. 网页端:拖拽/粘贴上传、下载、删除、实时聊天(桌面端「聊天」Tab 同步可见)
3. 上传前自动检查磁盘空间;桌面端可随时在文件表里管理共享目录内容
