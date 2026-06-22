import io, gc, time, html, re
from aiohttp import web
from bson.objectid import ObjectId
from utils import temp, get_size
from info import MAX_WEB_RESULTS, ACTOR_STORAGE_CHANNEL
from database.ia_filterdb import actors, get_actor_search_results
from web.web_assets import build_page, get_auth, form_wrapper, fast_json_response, render_collection_dropdown, render_mode_dropdown

actor_routes = web.RouteTableDef()

# ─────────────────────────────────────────────────────────
# 🎨 REUSABLE UI ASSETS (Pre-compiled to save RAM & CPU)
# ─────────────────────────────────────────────────────────
DIR_UI = '''
<style>
    .dir-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
    @media(min-width: 768px) { .dir-grid { grid-template-columns: repeat(5, 1fr); gap: 20px; } }
    .search-box { background:var(--card); border:1px solid var(--border); padding:16px; border-radius:12px; margin-bottom:25px; box-shadow:0 4px 15px rgba(0,0,0,0.1); }
    .s-row-1 { display: flex; gap: 10px; margin-bottom: 12px; }
    .s-input { flex: 1; background:var(--bg3); border:1px solid var(--border); padding:12px 16px; color:var(--text); border-radius:8px; outline:none; font-family:inherit; font-weight:600; font-size:14px; transition:0.2s; }
    .s-input:focus { border-color:var(--accent); }
    .s-btn { background:var(--accent); color:#fff; border:none; padding:0 24px; border-radius:8px; font-weight:800; cursor:pointer; transition:0.2s; white-space:nowrap; }
    .s-btn:hover { background:var(--accent-hover); transform:scale(1.02); }
    .s-row-2 { display: flex; gap: 10px; flex-wrap:wrap; align-items:center; }
    .cdd-wrap-dir { position: relative; background: var(--bg3); border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; cursor: pointer; font-weight: 700; font-size: 13px; color: var(--text); flex: 1; min-width: 100px; display: flex; justify-content: space-between; align-items: center; user-select: none; transition:0.2s; }
    .cdd-wrap-dir:hover { border-color: var(--accent); }
    .cdd-menu-dir { position: absolute; top: calc(100% + 5px); left: 0; right: 0; background: var(--bg2); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; z-index: 100; display: none; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
    .cdd-item-dir { padding: 10px 14px; border-bottom: 1px solid var(--border); transition: 0.2s; }
    .cdd-item-dir:hover { background: var(--bg3); color: var(--accent); }
    .pg-bar { display:flex; justify-content:center; align-items:center; gap:15px; margin-top:30px; }
    .act-card { background:var(--card); border:1px solid var(--border); border-radius:10px; overflow:hidden; transition:transform 0.2s, border-color 0.2s, box-shadow 0.2s; cursor:pointer; box-shadow:0 4px 10px rgba(0,0,0,0.2); }
    .act-card:hover { transform:translateY(-6px); border-color:rgba(229,9,20,0.6); box-shadow:0 8px 22px rgba(229,9,20,0.25); }
    .act-poster { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; transition:transform 0.4s cubic-bezier(0.4, 0, 0.2, 1); }
    .act-card:hover .act-poster { transform:scale(1.1); }
</style>
<div class="search-box">
    <div class="s-row-1">
        <input type="text" id="dir_q" class="s-input" placeholder="Search...">
        <button class="s-btn" onclick="resetDir(); searchDirectory()">Search</button>
    </div>
    <div class="s-row-2">
        <div class="cdd-wrap-dir" onclick="toggleDirCDD('cat', event)">
            <span id="dir_cat_lbl">📂 All</span> <span style="font-size:10px; color:var(--muted);">▼</span>
            <div class="cdd-menu-dir" id="dir_cat_menu">
                <div class="cdd-item-dir" onclick="pickDirCat('all', '📂 All', event)">📂 All</div>
                <div class="cdd-item-dir" onclick="pickDirCat('actor', '🎭 Actor', event)">🎭 Actor</div>
                <div class="cdd-item-dir" onclick="pickDirCat('app', '📱 App', event)">📱 App</div>
                <div class="cdd-item-dir" onclick="pickDirCat('website', '🌐 Website', event)">🌐 Website</div>
            </div>
        </div>
        <div class="cdd-wrap-dir" onclick="toggleDirCDD('mode', event)">
            <span id="dir_mode_lbl">🖼️ Poster</span> <span style="font-size:10px; color:var(--muted);">▼</span>
            <div class="cdd-menu-dir" id="dir_mode_menu">
                <div class="cdd-item-dir" onclick="pickDirMode('poster', '🖼️ Poster', event)">🖼️ Poster</div>
                <div class="cdd-item-dir" onclick="pickDirMode('text', '📄 Text', event)">📄 Text</div>
            </div>
        </div>
        {admin_btn}
    </div>
</div>
'''

PROFILE_CSS = '''<style>.actor-tab-bar{display:flex;gap:10px;border-bottom:2px solid var(--border);margin-bottom:25px}.actor-tab{background:0 0;border:none;color:var(--muted);padding:12px 20px;font-size:15px;font-weight:700;cursor:pointer;transition:.2s;position:relative;font-family:inherit}.actor-tab.active{color:var(--text)!important}.actor-tab.active::after{content:'';position:absolute;bottom:-2px;left:0;right:0;height:2px;background:var(--accent)}.actor-panel{display:none}.actor-panel.active{display:block!important}.gallery-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:14px}.gallery-item-wrap{position:relative;border-radius:8px;overflow:hidden;border:1px solid var(--border);aspect-ratio:1;cursor:pointer}.gallery-item{width:100%;height:100%;object-fit:cover;transition:transform .2s}.gallery-item-wrap:hover .gallery-item{transform:scale(1.04)}.gallery-del-btn{position:absolute;bottom:8px;left:50%;transform:translateX(-50%);background:rgba(160,8,8,.85);border:1px solid var(--accent);color:#fff;padding:4px 10px;border-radius:4px;font-size:10px;font-weight:700;cursor:pointer;z-index:5;opacity:0;transition:opacity .15s}.gallery-item-wrap:hover .gallery-del-btn{opacity:1}.lightbox{position:fixed;inset:0;background:rgba(0,0,0,.92);backdrop-filter:blur(15px);z-index:99999;display:none;align-items:center;justify-content:center;opacity:0;transition:opacity .2s ease}.lightbox.open{display:flex;opacity:1}.lightbox-img{max-width:92%;max-height:88vh;object-fit:contain;border-radius:6px;box-shadow:0 10px 40px rgba(0,0,0,.8);transform:scale(.95);transition:transform .2s}.lightbox.open .lightbox-img{transform:scale(1)}.lightbox-close{position:absolute;top:20px;right:25px;background:none;border:none;color:#fff;font-size:32px;cursor:pointer;opacity:.7}.lightbox-close:hover{opacity:1}.actor-header-wrap{display:flex;gap:25px;background:var(--card);border:1px solid var(--border);padding:25px;border-radius:12px;margin-bottom:35px;flex-direction:column;align-items:center;width:100%;box-sizing:border-box}.avatar-box-master{width:100%;max-width:340px;height:auto;aspect-ratio:3/4;background:var(--bg3);border-radius:8px;overflow:hidden;border:1px solid var(--border);flex-shrink:0}@media(min-width:768px){.actor-header-wrap{flex-direction:row;align-items:stretch}.avatar-box-master{width:260px;height:350px;max-width:none;aspect-ratio:auto}}</style>'''

PROFILE_JS = '''<script>
function openLightbox(s){document.getElementById('lightboxTargetImg').src=s;var lb=document.getElementById('actorLightboxModal');lb.style.display='flex';setTimeout(()=>lb.classList.add('open'),10);}
function closeLightbox(){var lb=document.getElementById('actorLightboxModal');lb.classList.remove('open');setTimeout(()=>lb.style.display='none',200);}
function switchActorTab(ev,tId){document.querySelectorAll('.actor-panel').forEach(p=>p.classList.remove('active'));document.querySelectorAll('.actor-tab').forEach(t=>t.classList.remove('active'));document.getElementById(tId).classList.add('active');ev.currentTarget.classList.add('active');if(tId==='tab-video'&&!document.getElementById('results').innerHTML) window.gridEngine.search(0);}
function openActorEditModal(){document.getElementById('actorEditModal').classList.add('open');}
function closeActorEditModal(){document.getElementById('actorEditModal').classList.remove('open');}

// 🎬 Smart Grid Engine for Actor Profile Media
window.gridEngine = {
    col: 'all', mode: 'tg', offset: 0, page: 1, nextOff: '',
    search: async function(o) {
        this.offset = o; if(o===0) this.page = 1;
        var q = document.getElementById('q').value.trim();
        var grid = document.getElementById('results');
        grid.className = 'res-grid mode-' + this.mode;
        grid.innerHTML = '<div class="spin-wrap"><div class="spinner"></div><span>Filtering Cross-Network Matrix...</span></div>';
        try {
            var r = await fetch(`/api/actor/search?q=${encodeURIComponent(q)}&offset=${o}&col=${this.col}&mode=${this.mode}&id={actor_id}`);
            var d = await r.json();
            if(!d.results || !d.results.length) {
                grid.innerHTML = '<div class="empty"><p>No video assets matching filters found inside database.</p></div>';
                document.getElementById('pageBox').style.display='none'; return;
            }
            var h = '';
            d.results.forEach(f => {
                var sc=(f.source||'primary').toLowerCase();
                var adminBtns = '';
                if(d.is_admin) {
                    var safeName = f.name.replace(/\\'/g,"\\\\'").replace(/'/g,"\\\\'");
                    var safeCap = (f.caption||'').replace(/\\'/g,"\\\\'").replace(/'/g,"\\\\'");
                    adminBtns = `<div class="poster-admin"><button class="btn-edit" onclick="event.stopPropagation();editFile('${f.file_id}','${f.raw_collection}','${safeName}', '${safeCap}')">✏️ Edit</button><button class="btn-del" onclick="event.stopPropagation();deleteFile('${f.file_id}','${f.raw_collection}')">🗑️ Delete</button></div>`;
                }
                var ph = '';
                if(this.mode!=='none') {
                    ph = `<div class="poster-box" onclick="if(typeof toggleAdminBtns==='function')toggleAdminBtns(this.closest('.file-card'),event)"><img src="${f.tg_thumb}" class="fc-poster" onload="this.classList.add('loaded')" loading="lazy"><div class="poster-top"><span class="type-chip">${f.type.toUpperCase()}</span><span class="size-chip">${f.size}</span><span class="source-pill ${sc}"><span class="source-dot"></span>${sc.toUpperCase()}</span></div>${adminBtns}</div>`;
                } else {
                    var textAdmin = d.is_admin ? `<div class="text-admin-row"><button class="btn-edit" onclick="event.stopPropagation();editFile('${f.file_id}','${f.raw_collection}','${safeName}', '${safeCap}')">✏️ Edit</button><button class="btn-del" onclick="event.stopPropagation();deleteFile('${f.file_id}','${f.raw_collection}')">🗑️ Delete</button></div>` : '';
                    ph = `<div class="fc-text-info" onclick="if(typeof toggleAdminBtns==='function')toggleAdminBtns(this.closest('.file-card'),event)"><span class="tc-type">${f.type.toUpperCase()}</span><span class="tc-size">${f.size}</span><span class="source-pill ${sc}" style="margin-left:auto"><span class="source-dot"></span>${sc.toUpperCase()}</span></div>${textAdmin}`;
                }
                h += `<div class="file-card">${ph}<div class="fc-body" onclick="window.open('${f.watch}','_blank')"><div class="fc-name">${f.name}</div></div></div>`;
            });
            grid.innerHTML = h; this.nextOff = d.next_offset;
            document.getElementById('pageBox').style.display='flex';
            document.getElementById('pBtn').disabled=(o===0);
            document.getElementById('nBtn').disabled=!this.nextOff;
            document.getElementById('pgInfo').textContent='Page '+this.page;
        } catch(e) { grid.innerHTML='<div class="empty"><p>Matrix sync error.</p></div>'; }
    },
    next: function() { if(this.nextOff) { this.page++; this.search(this.nextOff); window.scrollTo(0,350); } },
    prev: function() { if(this.page>1) { this.page--; this.search(Math.max(0, this.offset-{lim})); window.scrollTo(0,350); } }
};
document.addEventListener('DOMContentLoaded', () => { var q = document.getElementById('q'); if(q) q.addEventListener('keydown', e => { if(e.key==='Enter') window.gridEngine.search(0); }); });

async function updateActorAvatar(aid){ var f=document.getElementById('avatarUpdateInput').files[0]; if(!f)
