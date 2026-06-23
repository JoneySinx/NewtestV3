import io, gc, time, html, re
import orjson
from aiohttp import web
from bson.objectid import ObjectId
from utils import temp, get_size
from info import BIN_CHANNEL, MAX_WEB_RESULTS, ACTOR_STORAGE_CHANNEL
from database.ia_filterdb import actors, get_actor_search_results
from web.web_assets import build_page, get_auth, form_wrapper

actor_routes = web.RouteTableDef()

def fast_json(data):
    return orjson.dumps(data).decode('utf-8')

# ─────────────────────────────────────────────────────────
# 🌐 DIRECTORY SEARCH UI (Compact & Uses Global Assets)
# ─────────────────────────────────────────────────────────
@actor_routes.get('/actors')
async def actors_directory_page(req):
    role, _ = await get_auth(req)
    if not role: return web.HTTPFound('/login')
    
    all_actors = await actors.find({}).sort("created_at", -1).limit(21).to_list(length=21)
    has_next_init = len(all_actors) > 20
    all_actors = all_actors[:20]
    
    admin_btn = '''<button onclick="window.location.href='/admin/create_actor'" style="background:var(--accent); color:#fff; border:none; padding:10px 15px; border-radius:8px; font-weight:800; cursor:pointer; font-size:13px; flex:1; min-width:130px;">➕ Create Profile</button>''' if role == 'admin' else ""
    
    act_items = ""
    for a in all_actors:
        cat = a.get("category", "actor")
        i = "🎭" if cat == "actor" else "📱" if cat == "app" else "🌐"
        v = int(a.get("photo_updated_at") or a.get("created_at") or 0)
        act_items += f'<div class="act-card" onclick="window.location.href=\'/actor/{str(a["_id"])}\'"><div style="position:relative; padding-top:135%; background:var(--bg3); overflow:hidden;"><img src="/api/actor/photo?id={str(a["_id"])}&v={v}" class="act-poster" loading="lazy"><div style="position:absolute; top:8px; left:8px; background:rgba(0,0,0,0.8); color:#fff; font-size:9px; padding:4px 8px; border-radius:4px; font-weight:800; z-index:2;">{i} {cat.capitalize()}</div></div><div style="padding:10px; text-align:center;"><div style="font-size:13px; font-weight:800; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">{html.escape(a.get("name", ""))}</div></div></div>'
    
    initial_grid = f'<div id="dir_grid_container" class="dir-grid">{act_items}</div>' if all_actors else '<div id="dir_grid_container" style="color:var(--muted); text-align:center; padding:60px;">📇 No profiles found.</div>'

    html_ui = f'''
    <style>.dir-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}@media(min-width:768px){{.dir-grid{{grid-template-columns:repeat(5,1fr);gap:20px}}}}.act-card{{background:var(--card);border:1px solid var(--border);border-radius:10px;overflow:hidden;transition:.2s;cursor:pointer}}.act-card:hover{{transform:translateY(-6px);border-color:rgba(229,9,20,.6);box-shadow:0 8px 22px rgba(229,9,20,.25)}}.act-poster{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transition:.4s}}.act-card:hover .act-poster{{transform:scale(1.1)}}</style>
    <div class="search-box" style="background:var(--card); border:1px solid var(--border); padding:16px; border-radius:12px; margin-bottom:25px; display:flex; gap:10px; flex-wrap:wrap;">
        <input type="text" id="dir_q" placeholder="Search Directory..." style="flex:1; min-width:200px; background:var(--bg3); border:1px solid var(--border); padding:12px; color:var(--text); border-radius:8px; outline:none;">
        <select id="dir_cat" style="background:var(--bg3); border:1px solid var(--border); color:var(--text); padding:12px; border-radius:8px; outline:none; font-weight:600;"><option value="all">📂 All</option><option value="actor">🎭 Actor</option><option value="app">📱 App</option><option value="website">🌐 Web</option></select>
        <button onclick="resetDir(); searchDirectory()" style="background:var(--accent); color:#fff; border:none; padding:0 24px; border-radius:8px; font-weight:800; cursor:pointer;">Search</button>
        {admin_btn}
    </div>
    {initial_grid}
    <div id="dir_pg_box" style="display:{'flex' if has_next_init else 'none'}; justify-content:center; gap:15px; margin-top:30px;">
        <button class="pg-btn" id="dir_pBtn" onclick="prevDir()" disabled>Previous</button>
        <span class="pg-info" id="dir_pgInfo">Page 1</span>
        <button class="pg-btn" id="dir_nBtn" onclick="nextDir()">Next</button>
    </div>
    <script>
    var dirOffset=0, dirPage=1, hasNext={'true' if has_next_init else 'false'};
    async function searchDirectory(){{
        var q=document.getElementById('dir_q').value, cat=document.getElementById('dir_cat').value;
        var r = await fetch('/api/directory/search?q='+encodeURIComponent(q)+'&cat='+cat+'&offset='+dirOffset);
        var d = await r.json(); document.getElementById('dir_grid_container').innerHTML = d.html; hasNext = d.has_next;
        document.getElementById('dir_pg_box').style.display = (dirOffset===0 && !hasNext) ? 'none' : 'flex';
        document.getElementById('dir_pBtn').disabled=(dirOffset===0); document.getElementById('dir_nBtn').disabled=!hasNext;
        document.getElementById('dir_pgInfo').innerText = 'Page ' + dirPage;
    }}
    function resetDir(){{ dirOffset=0; dirPage=1; }}
    function nextDir(){{ if(hasNext){{ dirOffset+=20; dirPage++; searchDirectory(); window.scrollTo(0,0); }} }}
    function prevDir(){{ if(dirOffset>0){{ dirOffset=Math.max(0,dirOffset-20); dirPage--; searchDirectory(); window.scrollTo(0,0); }} }}
    </script>
    '''
    return build_page("Directory - Fast Finder", f'<div class="main" style="padding-top:20px; max-width:1100px; margin:0 auto;">{html_ui}</div>', "", "actors", role)

@actor_routes.get('/api/directory/search')
async def api_directory_search(req):
    role, _ = await get_auth(req)
    if not role: return web.json_response({"html": ""}, dumps=fast_json)
    q, cat, offset = req.query.get("q", "").strip(), req.query.get("cat", "all"), int(req.query.get("offset", 0))
    query = {}
    if cat != "all": query["category"] = cat
    if q: query["name"] = {"$regex": re.escape(q), "$options": "i"}
    docs = await actors.find(query).sort("created_at", -1).skip(offset).limit(21).to_list(length=21)
    has_next = len(docs) > 20
    docs = docs[:20]
    
    if not docs: return web.json_response({"html": '<div style="color:var(--muted); text-align:center; padding:60px;">📇 No profiles found.</div>', "has_next": False}, dumps=fast_json)
    html_out = ""
    for a in docs:
        c = a.get("category", "actor")
        i, v = "🎭" if c == "actor" else "📱" if c == "app" else "🌐", int(a.get("photo_updated_at") or a.get("created_at") or 0)
        html_out += f'<div class="act-card" onclick="window.location.href=\'/actor/{str(a["_id"])}\'"><div style="position:relative; padding-top:135%; background:var(--bg3); overflow:hidden;"><img src="/api/actor/photo?id={str(a["_id"])}&v={v}" class="act-poster"><div style="position:absolute; top:8px; left:8px; background:rgba(0,0,0,0.8); color:#fff; font-size:9px; padding:4px 8px; border-radius:4px; font-weight:800; z-index:2;">{i} {c.capitalize()}</div></div><div style="padding:10px; text-align:center; font-size:13px; font-weight:800;">{html.escape(a.get("name", ""))}</div></div>'
    return web.json_response({"html": html_out, "has_next": has_next}, dumps=fast_json)

# ─────────────────────────────────────────────────────────
# 🌐 PROFILE VIEW: CLEANED & SYNCED WITH WEB_ASSETS
# ─────────────────────────────────────────────────────────
@actor_routes.get('/actor/{id}')
async def actor_profile_display(req):
    role, _ = await get_auth(req)
    if not role: return web.HTTPFound('/login')
    actor_id = req.match_info['id']
    actor = await actors.find_one({"_id": ObjectId(actor_id)})
    if not actor: return web.Response(text="Profile Not Found", status=404)
        
    actor_name, tags_list, category = actor["name"], actor.get("tags", []), actor.get("category", "actor")
    social, gallery_list = actor.get("social_links", {}), actor.get("gallery", [])
    
    t_html = "".join([f'<span style="background:var(--bg3); border:1px solid var(--border); color:var(--muted); font-size:11px; padding:3px 8px; border-radius:4px; font-weight:600; margin-right:5px;">#{html.escape(t)}</span>' for t in tags_list])
    s_html = "".join([f'<a href="{html.escape(social[k])}" target="_blank" style="background:{c}; color:#fff; padding:6px 14px; border-radius:6px; text-decoration:none; font-size:12px; font-weight:700;">{l}</a>' for k,c,l in [("instagram","#ff007f","📸 Instagram"),("youtube","#ff0000","📺 YouTube"),("twitter","#1da1f2","🐦 Twitter / X")] if social.get(k)])
    
    admin_actions = f'''<div style="display:flex; gap:10px; margin-top:10px; flex-wrap:wrap;"><button onclick="document.getElementById('actorEditModal').classList.add('open')" class="pg-btn">✏️ Edit Details</button><button onclick="deleteActorProfile('{actor_id}')" class="pg-btn" style="background:rgba(160,8,8,.78); color:#fff;">🗑️ Delete Profile</button><label class="pg-btn" style="cursor:pointer;">📸 Update Avatar<input type="file" onchange="updateActorAvatar('{actor_id}', this)" style="display:none;"></label></div>''' if role == 'admin' else ""
    
    g_items = "".join([f'<div class="gallery-item-wrap" onclick="openLightbox(\'/api/actor/photo?id={actor_id}&gallery_idx={i}\')"><img src="/api/actor/photo?id={actor_id}&gallery_idx={i}" class="gallery-item">' + (f'<button class="gallery-del-btn" onclick="deleteGalleryImage(\'{actor_id}\', {i}, event)">🗑️ Delete</button>' if role=='admin' else "") + '</div>' for i in range(len(gallery_list))])
    gallery_html = f'''<form action="/api/actor/gallery_upload" method="post" enctype="multipart/form-data" style="margin-bottom:20px; text-align:center;"><input type="hidden" name="actor_id" value="{actor_id}"><label class="pg-btn" style="background:var(--accent); color:#fff;">📂 Upload to Gallery<input type="file" name="gallery_img" onchange="this.form.submit()" style="display:none;"></label></form>''' if role == 'admin' else ""
    gallery_html += f'<div class="gallery-grid">{g_items}</div>' if g_items else '<div style="color:var(--muted); text-align:center; padding:40px;">🖼️ Gallery is empty.</div>'

    # 🚀 NOTICE: No .file-card or edit modal CSS here! It all comes from web_assets.py
    css_js_minified = f'''
    <style>
    .actor-tab-bar{{display:flex;gap:10px;border-bottom:2px solid var(--border);margin-bottom:25px}}
    .actor-tab{{background:0 0;border:none;color:var(--muted);padding:12px 20px;font-size:15px;font-weight:700;cursor:pointer;position:relative}}
    .actor-tab.active{{color:var(--text)}}.actor-tab.active::after{{content:'';position:absolute;bottom:-2px;left:0;right:0;height:2px;background:var(--accent)}}
    .actor-panel{{display:none}}.actor-panel.active{{display:block}}
    .gallery-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:14px}}
    .gallery-item-wrap{{position:relative;border-radius:8px;overflow:hidden;border:1px solid var(--border);aspect-ratio:1;cursor:pointer}}
    .gallery-item{{width:100%;height:100%;object-fit:cover;transition:.2s}}.gallery-item-wrap:hover .gallery-item{{transform:scale(1.04)}}
    .gallery-del-btn{{position:absolute;bottom:8px;left:50%;transform:translateX(-50%);background:rgba(160,8,8,.85);color:#fff;border:none;padding:4px 10px;border-radius:4px;font-size:10px;cursor:pointer;opacity:0}}.gallery-item-wrap:hover .gallery-del-btn{{opacity:1}}
    .lightbox{{position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:99999;display:none;align-items:center;justify-content:center;opacity:0;transition:.2s}}
    .lightbox.open{{display:flex;opacity:1}}.lightbox-img{{max-width:92%;max-height:88vh;object-fit:contain;border-radius:6px}}
    </style>
    
    <div class="main" style="padding-top:30px;max-width:1100px;margin:0 auto;">
        <a href="/actors" style="color:var(--muted);text-decoration:none;font-weight:700;margin-bottom:15px;display:block;">← Back to Catalog</a>
        <div style="display:flex; gap:25px; background:var(--card); border:1px solid var(--border); padding:25px; border-radius:12px; margin-bottom:35px; flex-wrap:wrap;">
            <img id="actorMasterAvatarImage" src="/api/actor/photo?id={actor_id}&v={int(actor.get("photo_updated_at", 0))}" style="width:200px; aspect-ratio:3/4; border-radius:8px; object-fit:cover; border:1px solid var(--border);">
            <div style="flex:1; min-width:300px; display:flex; flex-direction:column; justify-content:center;">
                <h1 style="font-size:32px; font-weight:900; margin-bottom:5px;">{html.escape(actor_name)}</h1>
                <div style="margin-bottom:12px;">{t_html}</div><div style="display:flex; gap:10px; margin-bottom:10px;">{s_html}</div>{admin_actions}
            </div>
        </div>
        
        <div class="actor-tab-bar">
            <button class="actor-tab active" onclick="switchActorTab(event,'tab-info')">ℹ️ Info</button>
            <button class="actor-tab" onclick="switchActorTab(event,'tab-video')">🎬 Linked Media</button>
            <button class="actor-tab" onclick="switchActorTab(event,'tab-gallery')">🖼️ Gallery</button>
        </div>
        
        <div id="tab-info" class="actor-panel active"><div style="background:var(--card); border:1px solid var(--border); padding:25px; border-radius:8px; white-space:pre-line;">{html.escape(actor.get("bio", ""))}</div></div>
        
        <div id="tab-video" class="actor-panel">
            <div class="search-zone" style="padding:0; margin-bottom:15px; display:flex; gap:10px;">
                <div class="search-wrap" style="flex:1;"><input class="search-input" id="actor_movie_q" placeholder="Search inside profile..."></div>
                <button class="search-btn" onclick="actOffset=0;triggerActorSearchAjax()">Search</button>
            </div>
            <div id="actor_video_results" class="res-grid"></div>
            <div class="pagination" id="actor_page_box" style="display:none;"><button class="pg-btn" id="actor_pBtn" onclick="actorPagePrev()">Prev</button><span class="pg-info" id="actor_pgInfo">Page 1</span><button class="pg-btn" id="actor_nBtn" onclick="actorPageNext()">Next</button></div>
        </div>
        
        <div id="tab-gallery" class="actor-panel">{gallery_html}</div>
    </div>
    
    <div id="actorLightboxModal" class="lightbox" onclick="closeLightbox()"><button style="position:absolute;top:20px;right:25px;background:none;border:none;color:#fff;font-size:32px;cursor:pointer;">&times;</button><img id="lightboxTargetImg" class="lightbox-img" src=""></div>
    
    <div class="edit-modal" id="actorEditModal" onclick="if(event.target===this)this.classList.remove('open')">
        <div class="em-card"><button class="em-close" onclick="document.getElementById('actorEditModal').classList.remove('open')">&#10005;</button>
            <div class="em-title">✏️ Edit Actor Info</div>
            <form action="/api/actor/update_profile" method="post"><input type="hidden" name="actor_id" value="{actor_id}">
                <input type="text" name="name" value="{html.escape(actor_name)}" class="em-input" required placeholder="Full Name">
                <textarea name="bio" class="em-input" style="min-height:100px" required placeholder="Bio">{html.escape(actor.get("bio", ""))}</textarea>
                <input type="text" name="tags" value="{html.escape(', '.join(tags_list))}" class="em-input" placeholder="Tags (Comma Separated)">
                <input type="url" name="insta" value="{html.escape(social.get('instagram',''))}" class="em-input" placeholder="Instagram URL">
                <button class="em-save-btn" type="submit">Save Updates</button>
            </form>
        </div>
    </div>

    <script>
    var actCurPage=1, actOffset=0, actNextOffset="";
    function switchActorTab(ev,tId){{ document.querySelectorAll('.actor-panel, .actor-tab').forEach(x=>x.classList.remove('active')); document.getElementById(tId).classList.add('active'); ev.currentTarget.classList.add('active'); if(tId==='tab-video' && !document.getElementById('actor_video_results').innerHTML) triggerActorSearchAjax(); }}
    function openLightbox(s){{ document.getElementById('lightboxTargetImg').src=s; document.getElementById('actorLightboxModal').style.display='flex'; setTimeout(()=>document.getElementById('actorLightboxModal').classList.add('open'),10); }}
    function closeLightbox(){{ document.getElementById('actorLightboxModal').classList.remove('open'); setTimeout(()=>document.getElementById('actorLightboxModal').style.display='none',200); }}
    
    // 🚀 FULLY SYNCED WITH web_assets.py GLOBAL UI & editFile() ENGINE
    async function triggerActorSearchAjax(){{
        var q=document.getElementById('actor_movie_q').value.trim(), g=document.getElementById('actor_video_results');
        g.innerHTML='<div class="empty">Loading Database Matrix...</div>';
        try{{
            var r = await fetch('/api/actor/search?q='+encodeURIComponent(q)+'&offset='+actOffset+'&id={actor_id}'), d = await r.json();
            if(!d.results.length){{ g.innerHTML='<div class="empty">No linked media found.</div>'; document.getElementById('actor_page_box').style.display='none'; return; }}
            var h='';
            d.results.forEach(f => {{
                var sc=(f.source||'primary').toLowerCase();
                var adm = d.is_admin ? `<div class="poster-admin"><button class="btn-edit" onclick="event.stopPropagation(); editFile('${{f.file_id}}','${{f.raw_collection}}','${{f.name.replace(/'/g, "\\\\'") }}', '${{f.caption||''}}')">✏️ Edit</button><button class="btn-del" onclick="event.stopPropagation(); deleteFile('${{f.file_id}}','${{f.raw_collection}}')">🗑️ Del</button></div>` : '';
                
                h += `<div class="file-card">
                        <div class="poster-box" id="poster-box-${{f.file_id}}" onclick="this.closest('.file-card').classList.toggle('admin-active');event.stopPropagation();">
                            <img src="${{f.tg_thumb}}" id="img-poster-${{f.file_id}}" class="fc-poster" onload="this.classList.add('loaded')" onerror="handleThumbError('${{f.file_id}}')">
                            <div class="poster-top"><span class="type-chip">${{f.type}}</span><span class="size-chip">${{f.size}}</span></div>
                            ${{adm}}
                        </div>
                        <div class="fc-body" onclick="window.open('${{f.watch}}','_blank')"><div class="fc-name" id="name-title-${{f.file_id}}">${{f.name}}</div></div>
                      </div>`;
            }});
            g.innerHTML=h; actNextOffset=d.next_offset; document.getElementById('actor_page_box').style.display='flex';
            document.getElementById('actor_pBtn').disabled=(actOffset===0); document.getElementById('actor_nBtn').disabled=!actNextOffset; document.getElementById('actor_pgInfo').innerText='Page '+actCurPage;
        }}catch(e){{}}
    }}
    
    function actorPageNext(){{ if(actNextOffset){{ actCurPage++; actOffset=actNextOffset; triggerActorSearchAjax(); }} }}
    function actorPagePrev(){{ if(actCurPage>1){{ actCurPage--; actOffset=Math.max(0, actOffset-20); triggerActorSearchAjax(); }} }}
    
    async function updateActorAvatar(aid, inp){{ var f=inp.files[0]; if(!f) return; var fd=new FormData(); fd.append('actor_id',aid); fd.append('photo',f); var r=await fetch('/api/actor/update_avatar',{{method:'POST',body:fd}}); if((await r.json()).success) document.getElementById('actorMasterAvatarImage').src='/api/actor/photo?id='+aid+'&v='+new Date().getTime(); }}
    async function deleteGalleryImage(aid, idx, e){{ e.stopPropagation(); if(confirm("Delete Photo?")){{ var r=await fetch('/api/actor/gallery_delete',{{method:'POST',body:JSON.stringify({{actor_id:aid,index:idx}}),headers:{{'Content-Type':'application/json'}}}}); if((await r.json()).success) window.location.reload(); }} }}
    async function deleteActorProfile(id){{ if(confirm("Delete Profile?")){{ var r=await fetch('/api/actor/delete?id='+id,{{method:'POST'}}); if((await r.json()).success) window.location.href='/actors'; }} }}
    </script>
    '''
    return build_page(f"{actor_name} - Fast Finder", css_js_minified, "", "actors", role)

# ─────────────────────────────────────────────────────────
# ⚙️ PROFILE PAGE: INTERNAL FILE SEARCH API
# ─────────────────────────────────────────────────────────
@actor_routes.get('/api/actor/search')
async def api_actor_search_handler(req):
    role, _ = await get_auth(req)
    if not role: return web.json_response({"error": "Unauthorized"}, status=403, dumps=fast_json)
    actor_id, q_custom, off = req.query.get("id"), req.query.get("q", "").strip(), int(req.query.get("offset", 0) if req.query.get("offset") else 0)
    if not actor_id: return web.json_response({"results": []}, dumps=fast_json)
    
    actor = await actors.find_one({"_id": ObjectId(actor_id)})
    tags_list = actor.get("tags", []) if actor else []
    search_query, final_tags = (q_custom, []) if q_custom else (tags_list[0] if tags_list else "", tags_list)
    if not search_query: return web.json_response({"results": [], "next_offset": ""}, dumps=fast_json)
        
    all_m, next_offset = await get_actor_search_results(search_query, final_tags, max_results=MAX_WEB_RESULTS, offset=off, collection_type="all")
    results_list = [{
        "file_id": str(d.get("_id")), "name": d.get("file_name", "Unknown File"), "size": get_size(d.get("file_size", 0)),
        "type": d.get("file_type", "document").upper(), "source": d.get("source_col", "primary").capitalize(),
        "raw_collection": d.get("source_col", "primary"), "caption": d.get("caption", ""),
        "tg_thumb": f"/api/thumb?file_id={d.get('_id')}&col={d.get('source_col', 'primary')}&v={(d.get('thumb_url', '')[-8:] if str(d.get('thumb_url', '')).startswith('TG_ID:') else '0')}",
        "watch": f"/setup_stream?file_id={d.get('file_ref') or d.get('_id')}&mode=watch"
    } for d in all_m]
    return web.json_response({"results": results_list, "next_offset": next_offset, "is_admin": role == "admin"}, dumps=fast_json)

# ─────────────────────────────────────────────────────────
# 🛠️ ADMIN CREATE/EDIT APIs
# ─────────────────────────────────────────────────────────
@actor_routes.get('/admin/create_actor')
async def create_actor_page(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.HTTPFound('/dashboard')
    content = '''<form action="/api/create_actor" method="post" enctype="multipart/form-data"><input class="em-input" type="text" name="name" placeholder="Full Name" required><select name="category" class="em-input" required><option value="actor">🎭 Actor</option><option value="app">📱 App</option><option value="website">🌐 Website</option></select><textarea name="bio" class="em-input" placeholder="Bio..." style="min-height:100px;" required></textarea><input class="em-input" type="text" name="tags" placeholder="Search Tags (Comma Separated)"><div class="scard-label">Profile Photo</div><input type="file" name="photo" accept="image/*" required style="margin-bottom:15px;"><button class="em-save-btn" type="submit">Create Profile</button></form>'''
    return build_page("Create Profile", form_wrapper("New Profile", content, req.query.get('err',''), req.query.get('msg','')), "login-bg", "actors", role)

@actor_routes.post('/api/create_actor')
async def api_create_actor(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403, dumps=fast_json)
    try:
        reader = await req.multipart()
        name, bio, tags_raw, image_bytes, category = None, None, "", None, "actor"
        while True:
            part = await reader.next()
            if part is None: break
            if part.name == 'name': name = (await part.read()).decode().strip()
            elif part.name == 'bio': bio = (await part.read()).decode().strip()
            elif part.name == 'tags': tags_raw = (await part.read()).decode().strip()
            elif part.name == 'category': category = (await part.read()).decode().strip()
            elif part.name == 'photo': image_bytes = await part.read()
        if not name or not image_bytes: return web.HTTPFound('/admin/create_actor?err=Missing info')
        with io.BytesIO(image_bytes) as img_buffer:
            img_buffer.name = "poster.jpg"
            msg = await temp.BOT.send_photo(chat_id=ACTOR_STORAGE_CHANNEL, photo=img_buffer)
        tg_photo_id = msg.photo.sizes[-1].file_id if hasattr(msg.photo, "sizes") and msg.photo.sizes else msg.photo.file_id
        await actors.insert_one({"name": name, "bio": bio, "category": category, "tags": [t.strip() for t in tags_raw.split(",") if t.strip()], "photo_url": f"TG_ID:{tg_photo_id}", "photo_updated_at": int(time.time()), "social_links": {}, "gallery": [], "created_at": int(time.time())})
        return web.HTTPFound('/actors?msg=Profile created!')
    except: return web.HTTPFound('/admin/create_actor?err=Error')

@actor_routes.post('/api/actor/update_profile')
async def api_actor_update_profile(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403, dumps=fast_json)
    d = await req.post()
    await actors.update_one({"_id": ObjectId(d.get('actor_id'))}, {"$set": {"name": d.get('name', '').strip(), "bio": d.get('bio', '').strip(), "tags": [t.strip() for t in d.get('tags', '').strip().split(",") if t.strip()], "social_links": {"instagram": d.get('insta', '').strip()}}})
    return web.HTTPFound(f"/actor/{d.get('actor_id')}?msg=Updated!")

@actor_routes.get('/api/actor/photo')
async def get_actor_photo(req):
    actor_id, img_index = req.query.get("id"), req.query.get("gallery_idx")
    try:
        doc = await actors.find_one({"_id": ObjectId(actor_id)})
        raw_url = doc.get("gallery", [])[int(img_index)] if img_index is not None else doc.get("photo_url")
        file_data = await temp.BOT.download_media(raw_url.replace("TG_ID:", ""), in_memory=True)
        return web.Response(body=file_data.getvalue(), content_type="image/jpeg", headers={"Cache-Control": "public, max-age=31536000, immutable"})
    except: return web.Response(status=404)
    finally: gc.collect()

@actor_routes.post('/api/actor/update_avatar')
async def api_actor_update_avatar(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403, dumps=fast_json)
    try:
        data = await req.post()
        with io.BytesIO(data.get("photo").file.read()) as img_buffer:
            img_buffer.name = "avatar.jpg"
            msg = await temp.BOT.send_photo(chat_id=ACTOR_STORAGE_CHANNEL, photo=img_buffer)
        tg_id = msg.photo.sizes[-1].file_id if hasattr(msg.photo, "sizes") and msg.photo.sizes else msg.photo.file_id
        await actors.update_one({"_id": ObjectId(data.get("actor_id"))}, {"$set": {"photo_url": f"TG_ID:{tg_id}", "photo_updated_at": int(time.time())}})
        return web.json_response({"success": True}, dumps=fast_json)
    except: return web.json_response({"success": False}, dumps=fast_json)

@actor_routes.post('/api/actor/gallery_upload')
async def api_actor_gallery_upload(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403, dumps=fast_json)
    try:
        reader = await req.multipart()
        actor_id, image_bytes = None, None
        while True:
            part = await reader.next()
            if part is None: break
            if part.name == 'actor_id': actor_id = (await part.read()).decode().strip()
            elif part.name == 'gallery_img': image_bytes = await part.read()
        with io.BytesIO(image_bytes) as img_buffer:
            img_buffer.name = "gal.jpg"
            msg = await temp.BOT.send_photo(chat_id=ACTOR_STORAGE_CHANNEL, photo=img_buffer)
        tg_id = msg.photo.sizes[-1].file_id if hasattr(msg.photo, "sizes") and msg.photo.sizes else msg.photo.file_id
        await actors.update_one({"_id": ObjectId(actor_id)}, {"$push": {"gallery": f"TG_ID:{tg_id}"}})
        return web.HTTPFound(f'/actor/{actor_id}')
    except: return web.HTTPFound('/actors')

@actor_routes.post('/api/actor/gallery_delete')
async def api_actor_gallery_delete(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403, dumps=fast_json)
    try:
        body = await req.json()
        gallery = (await actors.find_one({"_id": ObjectId(body.get("actor_id"))}))["gallery"]
        del gallery[body.get("index")]
        await actors.update_one({"_id": ObjectId(body.get("actor_id"))}, {"$set": {"gallery": gallery}})
        return web.json_response({"success": True}, dumps=fast_json)
    except: return web.json_response({"success": False}, dumps=fast_json)

@actor_routes.post('/api/actor/delete')
async def api_actor_delete(req):
    role, _ = await get_auth(req)
    if role == 'admin': await actors.delete_one({"_id": ObjectId(req.query.get("id"))})
    return web.json_response({"success": True}, dumps=fast_json)
