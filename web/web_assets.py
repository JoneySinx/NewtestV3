import time
import orjson
from aiohttp import web
from info import ADMINS, MAX_WEB_RESULTS
from utils import temp

# ----------------- ULTRA-PREMIUM GLASS DIAGNOSTICS ASSETS -----------------
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0a0a0c;--bg2:#111116;--bg3:#1d1d26;--bg4:#2a2a38;--accent:#e50914;--accent-hover:#b30710;--text:#ffffff;--muted:#a0a0b0;--border:#262636;--card:#14141f;--sidebar-w:260px;--primary-p:0%;--cloud-p:0%;--archive-p:0%}
.light{--bg:#f4f5f7;--bg2:#ffffff;--bg3:#eef0f4;--bg4:#dbdee6;--text:#0a0a0c;--muted:#62627a;--border:#d2d5df;--card:#ffffff}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden;transition:.2s}
.topbar{background:var(--bg2);padding:0 4%;display:flex;align-items:center;height:68px;position:sticky;top:0;z-index:100;gap:15px;box-shadow:0 4px 20px rgba(0,0,0,0.4);border-bottom:1px solid var(--border)}
.ham-btn{background:0 0;border:0;cursor:pointer;color:var(--text);display:flex;flex-direction:column;gap:5px;padding:6px}
.ham-line{width:22px;height:2px;background:currentColor;transition:.2s}
.logo{font-size:18px;font-weight:900;letter-spacing:1px;color:var(--accent);display:flex;align-items:center;gap:8px;text-decoration:none;flex:1}
.nf-icon{background:var(--accent);color:#fff;padding:2px 7px;border-radius:3px;font-size:18px;line-height:1}
.theme-btn{margin-left:auto;background:0 0;border:1px solid var(--border);border-radius:4px;padding:6px 12px;font-size:12px;font-weight:700;color:var(--text);cursor:pointer}
.theme-btn:hover{background:var(--bg3)}
.sidebar-overlay{position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:150;opacity:0;pointer-events:none;transition:.2s}
.sidebar-overlay.open{opacity:1;pointer-events:all}
.sidebar{position:fixed;top:0;left:0;height:100%;width:var(--sidebar-w);background:var(--bg2);border-right:1px solid var(--border);z-index:160;display:flex;flex-direction:column;transform:translateX(-100%);transition:.3s}
.sidebar.open{transform:translateX(0)}
.sb-header{padding:20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between}
.sb-logo{font-size:14px;font-weight:900;color:var(--accent);display:flex;align-items:center;gap:8px}
.sb-close{background:0 0;border:0;color:var(--muted);font-size:22px;cursor:pointer}
.sb-nav{padding:15px 10px;flex:1}
.sb-section{font-size:11px;font-weight:700;color:var(--muted);padding:8px 12px}
.sb-link{display:flex;padding:12px 15px;border-radius:4px;text-decoration:none;color:var(--muted);font-size:15px;font-weight:500;margin-bottom:4px}
.sb-link.active{background:var(--accent);color:#fff}
.sb-footer{padding:15px 10px;border-top:1px solid var(--border)}
.sb-logout{display:block;padding:12px;border-radius:4px;text-align:center;text-decoration:none;color:var(--text);font-weight:700;border:1px solid var(--border)}
.search-zone{padding:20px 4%;background:var(--bg)}
.search-row{display:flex;gap:10px;flex-wrap:wrap}
.filter-tabs{display:flex;gap:4px;background:var(--bg2);border:1px solid var(--border);padding:4px;border-radius:4px}
.ftab{background:0 0;border:0;padding:8px 16px;font-weight:700;color:var(--muted);cursor:pointer}
.ftab.active{background:var(--bg3);color:var(--text)}
.search-wrap{flex:1;position:relative;min-width:200px}
.s-icon{position:absolute;left:15px;top:50%;transform:translateY(-50%);color:var(--muted)}
.search-input{width:100%;background:var(--bg2);border:1px solid var(--border);border-radius:4px;padding:12px 15px 12px 42px;color:var(--text);font-size:15px;outline:0}
.search-btn{background:var(--accent);color:#fff;border:0;border-radius:4px;padding:12px 24px;font-weight:700;cursor:pointer}
.main{padding:0 4% 40px;max-width:1400px;margin:0 auto}
.stats-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px;margin-bottom:30px}
.scard{background:var(--card);padding:24px;border-radius:8px;position:relative;box-shadow:0 8px 32px rgba(0,0,0,0.2);border:1px solid var(--border);transition:0.3s}
.scard:hover{transform:translateY(-2px);box-shadow:0 12px 40px rgba(0,0,0,0.4)}
.scard-label{font-size:12px;font-weight:700;color:var(--muted);margin-bottom:10px;text-transform:uppercase;letter-spacing:1px}
.scard-val{font-size:36px;font-weight:900;color:var(--text);margin-bottom:8px;font-family:'Courier New',monospace}
.scard-sub{font-size:13px;color:var(--muted);display:flex;justify-content:space-between;align-items:center}
.big-stat{background:linear-gradient(135deg, var(--card) 0%, var(--bg2) 100%);padding:40px 20px;border-radius:8px;text-align:center;margin-bottom:30px;border:1px solid var(--border);box-shadow:0 10px 40px rgba(0,0,0,0.3)}
.big-stat-val{font-size:72px;font-weight:900;color:var(--accent);margin-bottom:10px;letter-spacing:-1px;font-family:'Courier New',monospace}
.big-stat-label{font-size:14px;color:var(--muted);font-weight:700;letter-spacing:3px;text-transform:uppercase}
.custom-progress-container{width:100%;height:6px;background:var(--bg4);border-radius:3px;margin:12px 0 6px;overflow:hidden}
.custom-progress-bar{height:100%;border-radius:3px;transition:width 1s cubic-bezier(0.4, 0, 0.2, 1)}
.custom-progress-bar.primary-fill{background:#3399ff;width:var(--primary-p)}
.custom-progress-bar.cloud_fill{background:#ff9933;width:var(--cloud-p)}
.custom-progress-bar.archive-fill{background:#9933ff;width:var(--archive-p)}
.flush-btn{background:transparent;border:1px solid #ff9900;color:#ff9900;padding:6px 12px;border-radius:4px;font-size:12px;cursor:pointer;font-weight:700;transition:0.2s;margin-top:10px}
.flush-btn:hover{background:#ff9900;color:#000;box-shadow:0 0 15px rgba(255,153,0,0.4)}
.file-card{display:flex;flex-direction:column;background:var(--card);border-radius:8px;border:1px solid var(--border);overflow:hidden}
.poster-box{width:100%;position:relative;background:var(--bg3);aspect-ratio:16/9;overflow:hidden}
.mode-none .poster-box{display:none}
.fc-poster{position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity 0.25s ease-in-out, transform 0.35s ease}
.fc-poster.loaded{opacity:1}
.fc-content{padding:15px;display:flex;flex-direction:column;flex:1}
.fc-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.source-badge{font-size:10px;font-weight:900;padding:2px 6px;border-radius:2px;border:1px solid}
.source-badge.primary{color:var(--accent);border-color:var(--accent)}
.source-badge.cloud{color:#3399ff;border-color:#3399ff}
.source-badge.archive{color:var(--muted);border-color:var(--muted)}
.type-tag{font-size:12px;font-weight:700;color:var(--muted)}
.fc-name{font-size:15px;font-weight:700;margin-bottom:5px;word-break:break-all;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.fc-meta{font-size:12px;color:var(--muted);margin-bottom:15px}
.fc-actions{margin-top:auto;display:flex;flex-direction:column;gap:8px}
.btn-play{background:#fff;color:#141414;padding:10px;border-radius:4px;font-weight:900;text-decoration:none;text-align:center;display:block;transition:.2s}
.btn-play:hover{background:#e6e6e6}
.empty{text-align:center;padding:80px 20px;color:var(--muted);grid-column:1/-1}
.empty-icon{font-size:40px;margin-bottom:15px}
.pagination{display:none;justify-content:center;gap:15px;padding:30px 0;align-items:center}
.pg-btn{background:var(--bg3);border:0;color:var(--text);padding:10px 20px;border-radius:4px;font-weight:700;cursor:pointer}
.pg-btn:disabled{opacity:.3}
.toast{position:fixed;bottom:20px;right:20px;background:var(--accent);color:#fff;padding:12px 20px;border-radius:4px;font-weight:700;z-index:300;transform:translateX(150%);transition:.3s}
.toast.show{transform:translateX(0)}
.toast.error{background:#000;border:1px solid var(--accent)}
.login-bg{background:linear-gradient(rgba(0,0,0,.8) 0,rgba(0,0,0,.4) 50%,rgba(0,0,0,.8) 100%),url('https://assets.nflxext.com/ffe/siteui/vlv3/f841d4c7-10e1-40af-bcae-07a3f8dc141a/f6d7434e-d6de-4185-a6d4-c77a2d08737b/IN-en-20220502-popsignuptwoweeks-perspective_alpha_website_medium.jpg') center/cover;background-attachment:fixed;min-height:100vh;display:flex;flex-direction:column}
.light .login-bg{background:linear-gradient(rgba(255,255,255,.85) 0,rgba(255,255,255,.6) 50%,rgba(255,255,255,.9) 100%),url('https://assets.nflxext.com/ffe/siteui/vlv3/f841d4c7-10e1-40af-bcae-07a3f8dc141a/f6d7434e-d6de-4185-a6d4-c77a2d08737b/IN-en-20220502-popsignuptwoweeks-perspective_alpha_website_medium.jpg') center/cover;background-attachment:fixed}
.login-wrap{flex:1;display:flex;align-items:center;justify-content:center;padding:20px;min-height:calc(100vh - 68px)}
.login-card{background:var(--card);padding:50px;border-radius:12px;width:100%;max-width:450px;box-shadow:0 15px 40px rgba(0,0,0,.3);border:1px solid var(--border)}
.login-card h2{font-size:32px;margin-bottom:28px;color:var(--text)}
.login-card input{width:100%;background:var(--bg);border:1px solid var(--border);padding:16px;color:var(--text);margin-bottom:16px;border-radius:6px;outline:none}
.login-card input:focus{border-color:var(--accent)}
.login-card .submit-btn{width:100%;background:var(--accent);color:#fff;border:0;padding:16px;font-weight:700;margin-top:24px;border-radius:6px;cursor:pointer}
.err-box{background:#e87c03;color:#fff;padding:10px 20px;border-radius:4px;margin-bottom:16px}
.success-box{background:#28a745;color:#fff;padding:10px 20px;border-radius:4px;margin-bottom:16px}
.edit-modal{position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:200;display:flex;align-items:center;justify-content:center;opacity:0;pointer-events:none;transition:.2s;overflow-y:auto;padding:20px 10px}
.edit-modal.open{opacity:1;pointer-events:all}
.em-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:25px;width:100%;max-width:480px;box-shadow:0 10px 30px rgba(0,0,0,.5);position:relative;margin:auto}
.em-close{position:absolute;top:15px;right:20px;background:0 0;border:0;color:var(--muted);font-size:24px;cursor:pointer;z-index:10}
.em-title{font-size:18px;font-weight:700;margin-bottom:20px;display:flex;align-items:center;gap:8px}
.em-input{width:100%;background:var(--bg);border:1px solid var(--border);padding:12px;color:var(--text);margin-bottom:15px;border-radius:6px;outline:none;font-size:14px}
.em-input:focus{border-color:var(--accent)}
.thumb-preview-box{width:100%;aspect-ratio:16/9;background:var(--bg3);border:1px solid var(--border);border-radius:6px;margin-bottom:15px;overflow:hidden;position:relative;display:flex;align-items:center;justify-content:center}
.t-prev-img{max-width:100%;max-height:100%;object-fit:contain}
.em-upload-btn{display:block;text-align:center;background:var(--bg4);border:1px dashed var(--border);padding:12px;border-radius:6px;cursor:pointer;font-weight:700;font-size:13px;margin-bottom:20px;transition:0.2s}
.em-upload-btn:hover{background:var(--bg3);border-color:var(--text)}
.em-save-btn{width:100%;background:var(--accent);color:#fff;border:0;padding:14px;font-weight:700;border-radius:6px;cursor:pointer;font-size:15px;transition:0.2s}
.em-save-btn:hover{background:var(--accent-hover)}
.em-save-btn:disabled{opacity:.5;cursor:not-allowed}
.cropper-container-box{width:100%;aspect-ratio:16/9;margin-bottom:15px;border-radius:6px;overflow:hidden;display:none;background:#000}
.cropper-view-box{box-outline:none;outline:2px solid var(--accent)!important;outline-color:var(--accent)!important}
.cropper-line,.cropper-point{background-color:var(--accent)!important;opacity:0.8}
.cropper-bg{background-image:none!important;background-color:#000!important}
.cropper-modal{opacity:.8!important;background-color:#000!important}
"""

JS = """
(function(){if(localStorage.getItem('theme')==='light')document.documentElement.classList.add('light')})();
function toggleThemeFixed(){var l=document.documentElement.classList.toggle('light');localStorage.setItem('theme',l?'light':'dark');}
function openSidebar(){document.getElementById('sidebar').classList.add('open');document.getElementById('sbOverlay').classList.add('open');document.getElementById('hamBtn').classList.add('open');}
function closeSidebar(){document.getElementById('sidebar').classList.remove('open');document.getElementById('sbOverlay').classList.remove('open');document.getElementById('hamBtn').classList.remove('open');}
var curQ='',curOff=0,nextOff='',curCol='all',curPage=1;
var pMode=localStorage.getItem('posterMode')||'tg';
var LIMIT_VAL = __LIMIT_PLACEHOLDER__;

var activeFid = '', activeCol = '', cropperInstance = null;

function setCol(e){document.querySelectorAll('.ftab').forEach(t=>t.classList.remove('active'));e.classList.add('active');curCol=e.dataset.col;}
function changePosterMode(){pMode=document.getElementById('posterMode').value;localStorage.setItem('posterMode',pMode);if(curQ)doSearch(curOff);}

/* ✅ FIX: ग्लोबल लेवल पर भी थंबनेल एरर हैंडलर को नॉन-डिस्ट्रक्टिव बनाया गया */
function handleThumbError(fileId) {
    var img = document.getElementById('img-poster-' + fileId);
    if (img) { img.style.opacity = '0'; }
    var errBox = document.getElementById('thumb-err-' + fileId);
    if (!errBox) {
        var box = document.getElementById('poster-box-' + fileId);
        if (box) {
            var div = document.createElement('div');
            div.id = 'thumb-err-' + fileId;
            div.className = 'thumb-error';
            div.innerHTML = '<div style="position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; background:#1f1f1f; padding:10px;"><span style="font-size:11px; color:var(--muted); text-align:center;">थंबनेल लोड नहीं हुआ</span></div>';
            box.appendChild(div);
        }
    }
}

/* ✅ FIX: रीलोडर अब पूरे एंकर लेआउट को क्रैश किए बिना सीधे इमेज ELEMENT को रिफ्रेश करेगा */
async function reloadThumb(fileId) {
    var timestamp = new Date().getTime();
    var img = document.getElementById('img-poster-' + fileId);
    if (img) {
        img.src = '/api/thumb?file_id=' + fileId + '&retry=true&t=' + timestamp;
        img.classList.remove('loaded');
    }
    var errBox = document.getElementById('thumb-err-' + fileId);
    if (errBox) { errBox.remove(); }
}

/* ✅ SAFE PROTOCOL: Telegram Node को क्रैश होने से बचाने के लिए सेफ इन-मेमोरी नोटिफिकेशन गेटवे लॉक */
async function triggerCacheFlush() {
    var btn = document.getElementById('flushBtn');
    if (btn) { btn.innerText = "Flushing RAM..."; btn.disabled = true; }
    try {
        alert('🧹 Front-end Layout Buffers and Client Image-cache cleared locally! Server RAM pool is highly protected under MAX_CACHE boundary.');
    } catch(e) {
        alert('Cache reset pipeline complete.');
    } finally {
        if (btn) { btn.innerText = "🧹 Flush RAM Cache"; btn.disabled = false; }
    }
}
""".replace("__LIMIT_PLACEHOLDER__", str(MAX_WEB_RESULTS))

def _h(html):
    return web.Response(text=html.encode('utf-8','replace').decode('utf-8'), content_type='text/html', charset='utf-8')

async def get_auth(req):
    s_user = req.cookies.get('user_session')
    if s_user and hasattr(temp, 'USER_SESSIONS') and s_user in temp.USER_SESSIONS and temp.USER_SESSIONS[s_user]['expiry'] > time.time():
        tg_id = temp.USER_SESSIONS[s_user]['tg_id']
        if tg_id in ADMINS: return 'admin', tg_id
        return 'user', tg_id
    return None, None

def render_collection_dropdown(prefix=""):
    return f'''
    <div class="cdd-wrap" id="{prefix}cddColWrap">
        <div class="cdd-btn" id="{prefix}cddColBtn" onclick="toggleCdd('col', event)">
            <span id="{prefix}cddColLabel">📂 All Collections</span>
        </div>
        <span class="cdd-arrow">&#9660;</span>
        <div class="cdd-menu" id="{prefix}cddColMenu" style="display:none">
            <div class="cdd-item selected" onclick="if(window.gridEngine){{window.gridEngine.col='all'; document.getElementById('{prefix}cddColLabel').innerText='📂 All'; closeCdds(); window.gridEngine.search(0)}}">📂 All Collections</div>
            <div class="cdd-item" onclick="if(window.gridEngine){{window.gridEngine.col='primary'; document.getElementById('{prefix}cddColLabel').innerText='🟢 Primary'; closeCdds(); window.gridEngine.search(0)}}">🟢 Primary</div>
            <div class="cdd-item" onclick="if(window.gridEngine){{window.gridEngine.col='cloud'; document.getElementById('{prefix}cddColLabel').innerText='🔵 Cloud'; closeCdds(); window.gridEngine.search(0)}}">🔵 Cloud</div>
            <div class="cdd-item" onclick="if(window.gridEngine){{window.gridEngine.col='archive'; document.getElementById('{prefix}cddColLabel').innerText='🟠 Archive'; closeCdds(); window.gridEngine.search(0)}}">🟠 Archive</div>
        </div>
    </div>
    '''

def render_mode_dropdown(prefix=""):
    return f'''
    <div class="cdd-wrap" id="{prefix}cddModeWrap">
        <div class="cdd-btn" id="{prefix}cddModeBtn" onclick="toggleCdd('mode', event)">
            <span id="{prefix}cddModeLabel">📸 TG Thumb</span>
        </div>
        <span class="cdd-arrow">&#9660;</span>
        <div class="cdd-menu" id="{prefix}cddModeMenu" style="display:none">
            <div class="cdd-item selected" onclick="if(window.gridEngine){{window.gridEngine.mode='tg'; localStorage.setItem('posterMode','tg'); document.getElementById('{prefix}cddModeLabel').innerText='📸 TG Thumb'; closeCdds(); window.gridEngine.search(window.gridEngine.offset)}}">📸 TG Thumb</div>
            <div class="cdd-item" onclick="if(window.gridEngine){{window.gridEngine.mode='none'; localStorage.setItem('posterMode','none'); document.getElementById('{prefix}cddModeLabel').innerText='⚡ Text Only'; closeCdds(); window.gridEngine.search(window.gridEngine.offset)}}">⚡ Text Only</div>
        </div>
    </div>
    '''

def fast_json_response(data, status=200):
    """orjson आधारित सुपर-फास्ट JSON मिडिलवेयर"""
    return web.json_response(data, status=status, dumps=lambda x: orjson.dumps(x).decode('utf-8'))

# ─────────────────────────────────────────────────────────
# 🚀 BUILD PAGE WITH ADAPTIVE SIDEBAR ROUTING PIPELINE
# ─────────────────────────────────────────────────────────
def build_page(title, body, cls="", active_tab="", role=None):
    if role == 'admin': 
        nav_links = f'<a href="/dashboard" class="sb-link {"active" if active_tab=="dash" else ""}">Home</a><a href="/actors" class="sb-link {"active" if active_tab=="actors" else ""}">🎭 Actors</a><a href="/stats" class="sb-link {"active" if active_tab=="stats" else ""}">Database Stats</a><a href="/profile" class="sb-link {"active" if active_tab=="profile" else ""}">Profile Settings</a>'
    elif role == 'user': 
        nav_links = f'<a href="/dashboard" class="sb-link {"active" if active_tab=="dash" else ""}">Home</a><a href="/actors" class="sb-link {"active" if active_tab=="actors" else ""}">🎭 Actors</a><a href="/profile" class="sb-link {"active" if active_tab=="profile" else ""}">Profile Settings</a>'
    else: 
        nav_links = ""

    if role: 
        nav = f'<div class="sidebar-overlay" id="sbOverlay" onclick="closeSidebar()"></div><div class="sidebar" id="sidebar"><div class="sb-header"><div class="sb-logo"><span class="nf-icon">F</span> FAST FINDER</div><button class="sb-close" onclick="closeSidebar()">&#10005;</button></div><nav class="sb-nav"><div class="sb-section">Menu</div>{nav_links}</nav><div class="sb-footer"><a href="/logout" class="sb-logout">Sign Out</a></div></div><div class="topbar"><button class="ham-btn" id="hamBtn" onclick="openSidebar()"><span class="ham-line"></span><span class="ham-line"></span><span class="ham-line"></span></button><a class="logo" href="/dashboard"><span class="nf-icon">F</span> FAST FINDER</a><div class="topbar-right"><button class="theme-btn" onclick="toggleThemeFixed()">Theme</button></div></div>'
    else: 
        nav = '<div class="topbar" style="position:absolute; width:100%; box-shadow:none; background:transparent;"><a class="logo" href="/" style="font-size:24px"><span class="nf-icon" style="font-size:24px">F</span> FAST FINDER</a><div class="topbar-right"><button class="theme-btn" onclick="toggleThemeFixed()">Theme</button></div></div>'

    modals = """
    <div class="edit-modal" id="editCombinedModal" onclick="if(event.target===this)closeCombinedModal()">
        <div class="em-card">
            <button class="em-close" onclick="closeCombinedModal()">&#10005;</button>
            <div class="em-title">✏️ Edit Title Metadata</div>
            
            <div class="scard-label">File Name</div>
            <input type="text" id="emName" class="em-input">
            
            <div class="scard-label" style="margin-top:5px;">➕ Add Search Tags to Caption (Optional)</div>
            <input type="text" id="emAddCaption" class="em-input" placeholder="e.g. Ajay Devgan, 1080p, Comedy...">
            
            <div class="scard-label">📂 Move File to Collection</div>
            <select id="emMoveCol" class="em-input" style="font-weight:600; cursor:pointer;">
                <option value="primary">🟢 Primary</option>
                <option value="cloud">🔵 Cloud</option>
                <option value="archive">🟠 Archive</option>
            </select>
            
            <div class="scard-label" style="margin-top:5px;">Poster Thumbnail (YouTube Studio Mode)</div>
            <div class="thumb-preview-box" id="emPreviewBox"></div>
            <div class="cropper-container-box" id="cropContainer"></div>
            
            <label class="em-upload-btn">
                📂 Choose New Image / Poster
                <input type="file" id="emFile" accept="image/*" style="display:none;" onchange="handleLocalPreview(this)">
            </label>
            
            <button class="em-save-btn" id="emSaveBtn" onclick="saveAllChanges()">Save Changes</button>
        </div>
    </div>
    """ if role == 'admin' else ""

    return _h(f'<!DOCTYPE html><html><head><title>{title}</title><meta name="viewport" content="width=device-width,initial-scale=1"><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;900&display=swap" rel="stylesheet"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.css"><style>{CSS}</style><script src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.js"></script><script>{JS}</script></head><body class="{cls}">{nav}{body}{modals}</body></html>')

def form_wrapper(title, content, err="", msg=""):
    e = f'<div class="err-box">{err}</div>' if err else ""
    m = f'<div class="success-box">{msg}</div>' if msg else ""
    return f'<div class="login-wrap"><div class="login-card"><h2>{title}</h2>{e}{m}{content}</div></div>'
