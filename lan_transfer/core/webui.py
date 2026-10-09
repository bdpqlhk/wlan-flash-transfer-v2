# -*- coding: utf-8 -*-
"""Web UI 页面(原样复用 v1 的单页应用, 零外部资源)。

占位符: __LAN_IP__ / __PORT__ 由 TransferHandler 在响应时替换。
"""
HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LAN 文件传输</title>
<style>
:root {
    --bg: #0b0e14; --bg2: #111620; --card: rgba(22,27,40,0.8);
    --card-border: rgba(255,255,255,0.06); --card-hover: rgba(30,36,55,0.9);
    --text: #e1e4ed; --text2: #9ca3b8; --text3: #5f6980;
    --accent: #4f8af7; --accent2: #7c6ff7; --accent-bg: rgba(79,138,247,0.1);
    --danger: #f2596b; --danger-bg: rgba(242,89,107,0.1);
    --success: #34c97c; --success-bg: rgba(52,201,124,0.1);
    --warning: #f5a623;
    --radius: 16px; --radius-sm: 10px; --radius-xs: 6px;
    --shadow: 0 1px 2px rgba(0,0,0,0.4), 0 4px 16px rgba(0,0,0,0.3);
    --shadow-lg: 0 4px 32px rgba(0,0,0,0.5);
    --transition: 0.2s cubic-bezier(0.4,0,0.2,1);
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--bg);
    background-image:
        radial-gradient(ellipse 80% 50% at 50% -20%, rgba(79,138,247,0.08), transparent),
        radial-gradient(ellipse 60% 40% at 80% 80%, rgba(124,111,247,0.05), transparent);
    color: var(--text); min-height: 100vh; display: flex; justify-content: center; padding: 16px;
    -webkit-font-smoothing: antialiased;
}
.container { width: 100%; max-width: 780px; display: flex; flex-direction: column; gap: 16px; }
.header { padding: 8px 0; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.header-left { display: flex; align-items: center; gap: 12px; }
.logo-box { width: 40px; height: 40px; border-radius: 12px; background: linear-gradient(135deg, var(--accent), var(--accent2)); display: flex; align-items: center; justify-content: center; font-size: 20px; color: #fff; box-shadow: 0 4px 16px rgba(79,138,247,0.3); }
.header h1 { font-size: 21px; font-weight: 700; color: var(--text); letter-spacing: -0.3px; }
.header .subtitle { font-size: 12px; color: var(--text2); margin-top: 1px; }
.card { background: var(--card); border: 1px solid var(--card-border); border-radius: var(--radius); padding: 20px; backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); box-shadow: var(--shadow); transition: border-color var(--transition); }
.card:hover { border-color: rgba(255,255,255,0.1); }
.top-bar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.url-box { flex: 1; min-width: 0; display: flex; align-items: center; gap: 8px; background: rgba(255,255,255,0.04); border: 1px solid var(--card-border); border-radius: var(--radius-sm); padding: 8px 14px; transition: border-color var(--transition); }
.url-box:focus-within { border-color: var(--accent); }
.url-box .protocol { color: var(--text3); font-size: 13px; font-family: monospace; }
.url-box .url-text { flex: 1; font-size: 14px; font-family: "SF Mono","Cascadia Code","Fira Code",Consolas,monospace; color: var(--accent); background: none; border: none; outline: none; min-width: 0; }
.url-actions { display: flex; gap: 6px; }
.icon-btn { width: 36px; height: 36px; border-radius: var(--radius-xs); border: 1px solid var(--card-border); background: rgba(255,255,255,0.04); color: var(--text2); cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 16px; transition: all var(--transition); flex-shrink: 0; }
.icon-btn:hover { background: rgba(255,255,255,0.08); color: var(--text); border-color: rgba(255,255,255,0.15); }
.icon-btn:active { transform: scale(0.95); }
.qr-modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 999; align-items: center; justify-content: center; backdrop-filter: blur(4px); }
.qr-modal.show { display: flex; }
.qr-modal-inner { background: var(--bg2); border: 1px solid var(--card-border); border-radius: var(--radius); padding: 28px; text-align: center; box-shadow: var(--shadow-lg); max-width: 320px; width: 90%; }
.qr-modal-inner img { width: 200px; height: 200px; border-radius: var(--radius-sm); background: #fff; padding: 8px; }
.qr-modal-inner p { margin-top: 14px; color: var(--text2); font-size: 13px; }
.qr-modal-inner .url-display-qr { font-size: 12px; color: var(--accent); word-break: break-all; margin-top: 6px; font-family: monospace; }
.stats-row { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 14px; }
.stat-item { flex: 1; min-width: 80px; display: flex; flex-direction: column; padding: 12px 16px; background: rgba(255,255,255,0.03); border-radius: var(--radius-sm); border: 1px solid var(--card-border); }
.stat-label { font-size: 11px; color: var(--text3); text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 4px; }
.stat-value { font-size: 17px; font-weight: 600; color: var(--text); }
.stat-value.accent { color: var(--accent); }
.dropzone { border: 2px dashed rgba(255,255,255,0.1); border-radius: var(--radius); padding: 40px 24px; text-align: center; cursor: pointer; transition: all 0.3s ease; position: relative; background: rgba(255,255,255,0.015); }
.dropzone:hover, .dropzone.drag-over { border-color: var(--accent); background: var(--accent-bg); transform: scale(1.005); }
.dropzone.drag-over { box-shadow: 0 0 0 4px var(--accent-bg); }
.dz-icon { width: 56px; height: 56px; margin: 0 auto 14px; border-radius: 50%; background: rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: center; font-size: 26px; transition: transform 0.3s ease; }
.dropzone:hover .dz-icon { transform: translateY(-3px); }
.dropzone h3 { font-size: 15px; font-weight: 600; margin-bottom: 6px; }
.dropzone p { font-size: 12px; color: var(--text2); }
.dropzone input { display: none; }
.upload-section { margin-top: 14px; }
.upload-list { display: none; flex-direction: column; }
.upload-list.active { display: flex; }
.upload-item { display: grid; grid-template-columns: 1fr auto; grid-template-rows: auto auto; gap: 4px 12px; padding: 12px; border-radius: var(--radius-sm); background: rgba(255,255,255,0.02); border: 1px solid var(--card-border); margin-bottom: 8px; animation: slideIn 0.25s ease; }
@keyframes slideIn { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
.up-name { font-size: 13px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; grid-column: 1; grid-row: 1; }
.up-meta { font-size: 11px; color: var(--text2); grid-column: 2; grid-row: 1; text-align: right; white-space: nowrap; }
.up-bar-wrap { grid-column: 1 / -1; grid-row: 2; height: 5px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden; margin-top: 2px; }
.up-bar-fill { height: 100%; background: var(--accent); border-radius: 3px; width: 0%; transition: width 0.15s linear; }
.up-bar-fill.done { background: var(--success); }
.up-bar-fill.error { background: var(--danger); }
.up-status { font-size: 11px; font-weight: 500; white-space: nowrap; }
.up-status.waiting { color: var(--text3); }
.up-status.uploading { color: var(--accent); }
.up-status.done { color: var(--success); }
.up-status.error { color: var(--danger); }
.file-list-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; flex-wrap: wrap; gap: 8px; }
.file-list-header h2 { font-size: 16px; font-weight: 600; }
.flh-right { display: flex; align-items: center; gap: 8px; }
.sort-group { display: flex; gap: 2px; background: rgba(255,255,255,0.04); border-radius: var(--radius-xs); border: 1px solid var(--card-border); padding: 2px; }
.sort-btn { padding: 5px 10px; font-size: 11px; border: none; border-radius: 4px; background: transparent; color: var(--text3); cursor: pointer; font-family: inherit; transition: all var(--transition); white-space: nowrap; }
.sort-btn:hover { color: var(--text2); }
.sort-btn.active { background: var(--accent); color: #fff; }
.badge { font-size: 11px; color: var(--text2); background: rgba(255,255,255,0.05); padding: 4px 10px; border-radius: 20px; border: 1px solid var(--card-border); white-space: nowrap; }
.refresh-btn { width: 28px; height: 28px; border-radius: var(--radius-xs); border: 1px solid var(--card-border); background: rgba(255,255,255,0.04); color: var(--text3); cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 15px; transition: all var(--transition); flex-shrink: 0; }
.refresh-btn:hover { color: var(--text); background: rgba(255,255,255,0.08); }
.refresh-btn.spinning { animation: spin 0.6s ease; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state { text-align: center; padding: 48px 20px; color: var(--text2); }
.empty-state .es-icon { width: 72px; height: 72px; margin: 0 auto 16px; border-radius: 50%; background: rgba(255,255,255,0.03); display: flex; align-items: center; justify-content: center; font-size: 32px; opacity: 0.6; }
.empty-state h3 { font-size: 15px; margin-bottom: 6px; color: var(--text2); }
.empty-state p { font-size: 12px; color: var(--text3); }
.file-row { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: var(--radius-sm); transition: background var(--transition); border: 1px solid transparent; margin-bottom: 2px; }
.file-row:hover { background: var(--card-hover); border-color: var(--card-border); }
.file-thumb { width: 42px; height: 42px; border-radius: var(--radius-xs); background: rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0; overflow: hidden; position: relative; }
.file-thumb img { width: 100%; height: 100%; object-fit: cover; position: absolute; inset: 0; }
.file-thumb .icon-overlay { font-size: 18px; z-index: 1; }
.file-info { flex: 1; min-width: 0; }
.file-info .fname { font-size: 13px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: pointer; }
.file-info .fname:hover { color: var(--accent); }
.file-info .fmeta { font-size: 11px; color: var(--text3); margin-top: 2px; display: flex; gap: 10px; flex-wrap: wrap; }
.file-btns { display: flex; gap: 6px; flex-shrink: 0; }
.btn { display: inline-flex; align-items: center; gap: 5px; padding: 6px 14px; border: none; border-radius: var(--radius-xs); font-size: 12px; font-weight: 500; cursor: pointer; transition: all var(--transition); text-decoration: none; font-family: inherit; white-space: nowrap; }
.btn-primary { background: linear-gradient(135deg, var(--accent), var(--accent2)); color: #fff; box-shadow: 0 2px 8px rgba(79,138,247,0.25); }
.btn-primary:hover { opacity: 0.92; transform: translateY(-1px); box-shadow: 0 4px 16px rgba(79,138,247,0.35); }
.btn-primary:active { transform: translateY(0); }
.btn-ghost { background: transparent; color: var(--text2); border: 1px solid var(--card-border); }
.btn-ghost:hover { color: var(--text); border-color: rgba(255,255,255,0.15); background: rgba(255,255,255,0.04); }
.btn-danger { background: transparent; color: var(--text3); border: 1px solid transparent; }
.btn-danger:hover { background: var(--danger-bg); color: var(--danger); border-color: rgba(242,89,107,0.3); }
.btn-sm { padding: 5px 10px; font-size: 11px; }
.toast-container { position: fixed; top: 20px; right: 20px; display: flex; flex-direction: column; gap: 8px; z-index: 1001; pointer-events: none; max-width: 340px; }
.toast-msg { padding: 12px 18px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 500; backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); box-shadow: var(--shadow-lg); animation: toastIn 0.3s ease; pointer-events: auto; display: flex; align-items: center; gap: 8px; border: 1px solid var(--card-border); }
@keyframes toastIn { from { opacity: 0; transform: translateX(40px); } to { opacity: 1; transform: translateX(0); } }
.toast-success { background: rgba(52,201,124,0.2); color: #5de8a0; }
.toast-error { background: rgba(242,89,107,0.2); color: #f57483; }
.dialog-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 998; align-items: center; justify-content: center; backdrop-filter: blur(3px); }
.dialog-overlay.show { display: flex; }
.dialog-box { background: var(--bg2); border: 1px solid var(--card-border); border-radius: var(--radius); padding: 24px; max-width: 360px; width: 90%; box-shadow: var(--shadow-lg); text-align: center; }
.dialog-box h4 { font-size: 16px; margin-bottom: 8px; }
.dialog-box p { font-size: 13px; color: var(--text2); margin-bottom: 18px; word-break: break-all; }
.dialog-actions { display: flex; gap: 10px; justify-content: center; }
.chat-card { background: var(--card); border: 1px solid var(--card-border); border-radius: var(--radius); padding: 16px; backdrop-filter: blur(20px); }
.chat-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.chat-header h2 { font-size: 15px; font-weight: 600; }
.chat-nickname { display: flex; align-items: center; gap: 6px; }
.chat-nickname input { width: 120px; padding: 4px 8px; font-size: 12px; border: 1px solid var(--card-border); border-radius: 4px; background: rgba(255,255,255,0.04); color: var(--text); outline: none; }
.chat-nickname input:focus { border-color: var(--accent); }
.chat-messages { height: 200px; overflow-y: auto; padding: 10px; background: rgba(0,0,0,0.2); border-radius: var(--radius-sm); margin-bottom: 12px; }
.chat-messages::-webkit-scrollbar { width: 6px; }
.chat-messages::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); border-radius: 3px; }
.chat-messages::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 3px; }
.chat-message { margin-bottom: 10px; padding: 8px 12px; background: rgba(255,255,255,0.04); border-radius: var(--radius-xs); border-left: 3px solid var(--accent); }
.chat-message:last-child { margin-bottom: 0; }
.chat-nick { font-size: 11px; font-weight: 600; color: var(--accent); margin-bottom: 2px; }
.chat-text { font-size: 13px; color: var(--text); word-break: break-all; }
.chat-time { font-size: 10px; color: var(--text3); margin-top: 2px; }
.chat-input-area { display: flex; gap: 8px; }
.chat-input { flex: 1; padding: 10px 14px; font-size: 13px; border: 1px solid var(--card-border); border-radius: var(--radius-sm); background: rgba(255,255,255,0.04); color: var(--text); outline: none; }
.chat-input:focus { border-color: var(--accent); }
.chat-input::placeholder { color: var(--text3); }
@media (max-width: 640px) { body { padding: 8px; } .container { gap: 10px; } .card { padding: 14px; } .header h1 { font-size: 18px; } .top-bar { flex-direction: column; align-items: stretch; } .url-actions { justify-content: center; } .stats-row { gap: 8px; } .stat-item { padding: 10px 12px; } .stat-value { font-size: 15px; } .dropzone { padding: 28px 16px; } .dz-icon { width: 44px; height: 44px; font-size: 22px; } .file-row { flex-wrap: wrap; } .file-thumb { width: 36px; height: 36px; font-size: 18px; } .file-btns { width: 100%; justify-content: flex-end; margin-top: 4px; } .sort-group { width: 100%; justify-content: center; } .toast-container { left: 10px; right: 10px; max-width: none; } .chat-nickname input { width: 80px; } }
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="header-left">
            <div class="logo-box">&#9889;</div>
            <div><h1>LAN 文件传输</h1><div class="subtitle">局域网高速文件共享</div></div>
        </div>
    </div>
    <div class="card">
        <div class="top-bar">
            <div class="url-box"><span class="protocol">HTTP</span><input class="url-text" id="urlInput" value="" readonly onclick="this.select()"></div>
            <div class="url-actions">
                <button class="icon-btn" id="btnCopy" title="复制链接" onclick="copyUrl()"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg></button>
                <button class="icon-btn" id="btnQR" title="显示二维码" onclick="showQR()"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><line x1="14" y1="14" x2="14" y2="14.01"/><line x1="18" y1="14" x2="18" y2="14.01"/><line x1="14" y1="18" x2="14" y2="18.01"/><line x1="18" y1="18" x2="18" y2="18.01"/><line x1="14" y1="22" x2="14" y2="22.01"/><line x1="18" y1="22" x2="18" y2="22.01"/><line x1="22" y1="14" x2="22" y2="18"/></svg></button>
            </div>
        </div>
        <div class="stats-row">
            <div class="stat-item"><span class="stat-label">本机 IP</span><span class="stat-value accent" id="statIP">--</span></div>
            <div class="stat-item"><span class="stat-label">端口</span><span class="stat-value" id="statPort">--</span></div>
            <div class="stat-item"><span class="stat-label">文件数</span><span class="stat-value" id="statCount">0</span></div>
            <div class="stat-item"><span class="stat-label">总大小</span><span class="stat-value" id="statSize">0 B</span></div>
        </div>
    </div>
    <div class="card">
        <div class="dropzone" id="dropzone">
            <div class="dz-icon">&#11014;&#65039;</div>
            <h3>点击选择文件 或 拖拽到此处</h3>
            <p>无文件大小限制 &middot; 无文件类型限制 &middot; 局域网满速传输</p>
            <input type="file" id="fileInput" multiple>
        </div>
        <div class="upload-section"><div class="upload-list" id="uploadList"></div></div>
    </div>
    <div class="card">
        <div class="file-list-header">
            <h2>共享文件</h2>
            <div class="flh-right">
                <div class="sort-group" id="sortGroup">
                    <button class="sort-btn active" data-sort="time">最新</button>
                    <button class="sort-btn" data-sort="name">名称</button>
                    <button class="sort-btn" data-sort="size">大小</button>
                </div>
                <span class="badge" id="fileBadge">0 个文件</span>
                <button class="refresh-btn" id="refreshBtn" title="刷新" onclick="loadFiles()"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.5 15a9 9 0 11-2.1-8.8L23 10"/></svg></button>
            </div>
        </div>
        <div id="fileList"></div>
    </div>
    <div class="chat-card">
        <div class="chat-header">
            <h2>📝 聊天室</h2>
            <div class="chat-nickname">
                <span style="font-size:11px;color:var(--text3)">昵称:</span>
                <input type="text" id="chatNickname" placeholder="匿名用户" maxlength="20">
            </div>
        </div>
        <div class="chat-messages" id="chatMessages"></div>
        <div class="chat-input-area">
            <input type="text" class="chat-input" id="chatInput" placeholder="输入消息..." maxlength="2000" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendChatMessage()}">
            <button class="btn btn-primary btn-sm" onclick="sendChatMessage()">发送</button>
        </div>
    </div>
</div>
<div class="qr-modal" id="qrModal" onclick="if(event.target===this)hideQR()"><div class="qr-modal-inner"><img id="qrImage" src="" alt="QR Code"><p>扫描二维码在手机上打开</p><div class="url-display-qr" id="qrUrl"></div></div></div>
<div class="dialog-overlay" id="dialogOverlay"><div class="dialog-box"><h4 id="dialogTitle">确认操作</h4><p id="dialogMsg"></p><div class="dialog-actions"><button class="btn btn-ghost" onclick="closeDialog()">取消</button><button class="btn btn-danger" id="dialogConfirm">确认</button></div></div></div>
<div class="toast-container" id="toastContainer"></div>
<script>
const SHARE_URL = "http://__LAN_IP__:__PORT__";
const LAN_IP = "__LAN_IP__";
const PORT = __PORT__;
document.getElementById("urlInput").value = SHARE_URL;
document.getElementById("statIP").textContent = LAN_IP;
document.getElementById("statPort").textContent = PORT;
let allFiles = [];
let sortBy = "time";

function showToast(msg, type) {
    type = type || "success";
    const container = document.getElementById("toastContainer");
    const el = document.createElement("div");
    el.className = "toast-msg toast-" + type;
    el.innerHTML = "<span>" + msg + "</span>";
    container.appendChild(el);
    setTimeout(() => { el.style.opacity = "0"; el.style.transition = "opacity 0.3s"; }, 2200);
    setTimeout(() => el.remove(), 2600);
}

function fmtSize(bytes) {
    if (bytes === 0) return "0 B";
    const u = ["B","KB","MB","GB","TB"];
    let i = 0, v = bytes;
    while (v >= 1024 && i < u.length-1) { v /= 1024; i++; }
    return v.toFixed(i===0?0:1) + " " + u[i];
}

function fmtTime(ts) {
    const d = new Date(ts * 1000);
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return "刚刚";
    if (diff < 3600000) return Math.floor(diff/60000) + " 分钟前";
    if (diff < 86400000) return Math.floor(diff/3600000) + " 小时前";
    return d.toLocaleDateString("zh-CN") + " " + d.toLocaleTimeString("zh-CN", {hour:"2-digit",minute:"2-digit"});
}

function extFor(name) {
    const p = name.lastIndexOf(".");
    return p >= 0 ? name.slice(p+1).toLowerCase() : "";
}

function isImage(name) {
    return ["jpg","jpeg","png","gif","svg","webp","bmp","ico"].includes(extFor(name));
}

function iconFor(name) {
    const map = {
        pdf:"PDF",doc:"DOC",docx:"DOC",xls:"XLS",xlsx:"XLS",ppt:"PPT",pptx:"PPT",
        exe:"EXE",msi:"MSI",dmg:"DMG",apk:"APK",
        mp4:"VID",mov:"VID",avi:"VID",mkv:"VID",webm:"VID",
        mp3:"AUD",wav:"AUD",flac:"AUD",aac:"AUD",ogg:"AUD",
        zip:"ZIP",rar:"RAR","7z":"7Z",tar:"TAR",gz:"GZ",
        py:"PY",js:"JS",ts:"TS",java:"JV",go:"GO",rs:"RS",c:"C",cpp:"CPP",
        html:"HTM",css:"CSS",json:"JSN",xml:"XML",md:"MD",sql:"SQL",
        txt:"TXT",csv:"CSV",
        psd:"PSD",ai:"AI",sketch:"SK",fig:"FIG",
    };
    return map[extFor(name)] || "FILE";
}

function sortFiles(files) {
    if (sortBy === "time") return [...files].sort((a,b) => b.modified - a.modified);
    if (sortBy === "name") return [...files].sort((a,b) => a.name.localeCompare(b.name, "zh-CN"));
    if (sortBy === "size") return [...files].sort((a,b) => b.size - a.size);
    return files;
}

async function loadFiles() {
    try {
        document.getElementById("refreshBtn").classList.add("spinning");
        setTimeout(() => document.getElementById("refreshBtn").classList.remove("spinning"), 600);
        const res = await fetch("/api/files");
        const data = await res.json();
        allFiles = data.files || [];
        renderFileList();
        updateStats();
    } catch (e) { console.error(e); }
}

function updateStats() {
    const total = allFiles.reduce((s,f) => s + f.size, 0);
    document.getElementById("statCount").textContent = allFiles.length;
    document.getElementById("statSize").textContent = fmtSize(total);
    document.getElementById("fileBadge").textContent = allFiles.length + " 个文件";
}

function renderFileList() {
    const el = document.getElementById("fileList");
    const sorted = sortFiles(allFiles);
    if (sorted.length === 0) {
        el.innerHTML = `<div class="empty-state"><div class="es-icon">&#128230;</div><h3>还没有文件</h3><p>拖拽文件到上方区域开始传输</p></div>`;
        return;
    }
    el.innerHTML = sorted.map(f => {
        const isImg = isImage(f.name);
        return `<div class="file-row">
            <div class="file-thumb">${isImg?'<img src="/api/download/'+encodeURIComponent(f.name)+'" loading="lazy" onerror="this.style.display=\'none\'" />':''}<span class="icon-overlay">${iconFor(f.name)}</span></div>
            <div class="file-info">
                <div class="fname" title="${escHtml(f.name)}" onclick="downloadFile('${escAttr(f.name)}')">${escHtml(f.name)}</div>
                <div class="fmeta"><span>${fmtSize(f.size)}</span><span>${fmtTime(f.modified)}</span>${isImg?'<span style="color:var(--warning);font-size:10px">预览</span>':''}</div>
            </div>
            <div class="file-btns">
                <a class="btn btn-primary btn-sm" href="/api/download/${encodeURIComponent(f.name)}" download><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>下载</a>
                <button class="btn btn-danger btn-sm" onclick="confirmDelete('${escAttr(f.name)}')" title="删除"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg></button>
            </div>
        </div>`;
    }).join("");
}

function escHtml(s) { return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
function escAttr(s) { return s.replace(/\\/g,"\\\\").replace(/'/g,"\\'").replace(/"/g,"&quot;"); }
function downloadFile(name) { window.open("/api/download/" + encodeURIComponent(name), "_blank"); }

let pendingDelete = null;
function confirmDelete(name) {
    pendingDelete = name;
    document.getElementById("dialogTitle").textContent = "删除文件";
    document.getElementById("dialogMsg").textContent = "确定删除 " + name + " 吗？此操作不可撤销。";
    document.getElementById("dialogOverlay").classList.add("show");
}
function closeDialog() { document.getElementById("dialogOverlay").classList.remove("show"); pendingDelete = null; }
document.getElementById("dialogConfirm").addEventListener("click", async () => {
    if (!pendingDelete) return;
    try {
        const res = await fetch("/api/delete/" + encodeURIComponent(pendingDelete), { method: "DELETE" });
        if (res.ok) { showToast("已删除 「" + pendingDelete + "」"); loadFiles(); }
        else { showToast("删除失败", "error"); }
    } catch (e) { showToast("删除失败", "error"); }
    closeDialog();
});

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const uploadList = document.getElementById("uploadList");
dropzone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => handleFiles(fileInput.files));
["dragover","dragenter"].forEach(ev => dropzone.addEventListener(ev, e => { e.preventDefault(); dropzone.classList.add("drag-over"); }));
["dragleave","dragend"].forEach(ev => dropzone.addEventListener(ev, e => { e.preventDefault(); dropzone.classList.remove("drag-over"); }));
dropzone.addEventListener("drop", e => { e.preventDefault(); dropzone.classList.remove("drag-over"); handleFiles(e.dataTransfer.files); });

document.addEventListener("paste", e => {
    const items = e.clipboardData?.items;
    if (!items) return;
    const files = [];
    for (const item of items) { if (item.kind === "file") files.push(item.getAsFile()); }
    if (files.length > 0) handleFiles(files);
});

function handleFiles(fileList) {
    if (!fileList || fileList.length === 0) return;
    const files = Array.from(fileList);
    fileInput.value = "";
    uploadList.classList.add("active");
    const baseId = Date.now();
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (!file) continue;
        const id = "up-" + baseId + "-" + i;
        const el = document.createElement("div");
        el.className = "upload-item";
        el.id = id;
        el.innerHTML = `<span class="up-name">${escHtml(file.name)}</span><span class="up-meta up-status waiting" id="${id}-stat">等待中</span><div class="up-bar-wrap"><div class="up-bar-fill" id="${id}-bar"></div></div>`;
        uploadList.appendChild(el);
        uploadFile(file, id);
    }
}

async function uploadFile(file, id) {
    const stat = document.getElementById(id + "-stat");
    const bar = document.getElementById(id + "-bar");
    stat.className = "up-meta up-status uploading";
    stat.textContent = "上传中...";
    try {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/upload", true);
        xhr.setRequestHeader("X-Filename", encodeURIComponent(file.name));
        xhr.setRequestHeader("X-File-Size", file.size);
        xhr.setRequestHeader("Content-Type", "application/octet-stream");
        let startTime = Date.now();
        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const pct = Math.round((e.loaded / e.total) * 100);
                bar.style.width = pct + "%";
                const elapsed = (Date.now() - startTime) / 1000;
                const speed = e.loaded / Math.max(elapsed, 0.1);
                stat.textContent = pct + "% " + fmtSize(speed) + "/s";
            }
        };
        xhr.onload = () => {
            if (xhr.status === 200) {
                bar.classList.add("done");
                bar.style.width = "100%";
                stat.className = "up-meta up-status done";
                stat.textContent = "完成";
                loadFiles();
                const item = document.getElementById(id);
                if (item) {
                    setTimeout(() => { item.style.opacity = "0"; item.style.transition = "opacity 0.4s"; setTimeout(() => item.remove(), 400); if (uploadList.children.length === 0) uploadList.classList.remove("active"); }, 1500);
                }
            } else { throw new Error("HTTP " + xhr.status); }
        };
        xhr.onerror = () => { bar.classList.add("error"); bar.style.width = "100%"; stat.className = "up-meta up-status error"; stat.textContent = "失败"; showToast("上传失败: " + file.name, "error"); };
        xhr.send(file);
    } catch (e) { bar.classList.add("error"); bar.style.width = "100%"; stat.className = "up-meta up-status error"; stat.textContent = "失败"; }
}

document.querySelectorAll(".sort-btn").forEach(btn => {
    btn.addEventListener("click", () => { document.querySelectorAll(".sort-btn").forEach(b => b.classList.remove("active")); btn.classList.add("active"); sortBy = btn.dataset.sort; renderFileList(); });
});

function copyUrl() {
    const input = document.getElementById("urlInput");
    input.select();
    navigator.clipboard.writeText(input.value).then(() => showToast("链接已复制到剪贴板")).catch(() => { input.select(); document.execCommand("copy"); showToast("链接已复制"); });
}

function showQR() {
    const url = SHARE_URL;
    const qrSrc = "https://api.qrserver.com/v1/create-qr-code/?size=240x240&color=000000&bgcolor=ffffff&data=" + encodeURIComponent(url);
    document.getElementById("qrImage").src = qrSrc;
    document.getElementById("qrUrl").textContent = url;
    document.getElementById("qrModal").classList.add("show");
}
function hideQR() { document.getElementById("qrModal").classList.remove("show"); }
document.addEventListener("keydown", e => { if (e.key === "Escape") hideQR(); });
loadFiles();
loadChatMessages();
setInterval(loadChatMessages, 3000);

let chatLastId = 0;
async function loadChatMessages() {
    try {
        const res = await fetch("/api/chat");
        const data = await res.json();
        const messages = data.messages || [];
        const container = document.getElementById("chatMessages");
        let html = "";
        messages.forEach(m => {
            html += `<div class="chat-message"><div class="chat-nick">${escHtml(m.nickname)}</div><div class="chat-text">${escHtml(m.message)}</div><div class="chat-time">${fmtTime(m.timestamp)}</div></div>`;
        });
        container.innerHTML = html;
        container.scrollTop = container.scrollHeight;
        if (messages.length > 0) chatLastId = messages[messages.length - 1].id;
    } catch (e) { console.error(e); }
}

async function sendChatMessage() {
    const input = document.getElementById("chatInput");
    const nicknameInput = document.getElementById("chatNickname");
    const message = input.value.trim();
    const nickname = nicknameInput.value.trim() || "匿名用户";

    if (!message) return;

    try {
        const res = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nickname, message })
        });
        const data = await res.json();
        if (data.ok) {
            input.value = "";
            loadChatMessages();
        } else {
            showToast(data.error || "发送失败", "error");
        }
    } catch (e) {
        showToast("发送失败", "error");
    }
}
</script>
</body>
</html>"""
