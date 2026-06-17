import io, gc, time, json, html
from aiohttp import web
from bson.objectid import ObjectId
from utils import temp, get_size
from info import BIN_CHANNEL
from database.ia_filterdb import actors, get_actor_search_results
from web.web_assets import build_page, get_auth, form_wrapper

actor_routes = web.RouteTableDef()

# ─────────────────────────────────────────────────────────
# 🎭 PUBLIC VIEW: ACTORS DIRECTORY CATALOG PAGE
# ─────────────────────────────────────────────────────────
@actor_routes.get('/actors')
async def actors_directory_page(req):
    role, _ = await get_auth(req)
    if not role: return web.HTTPFound('/login')
    all_actors = await actors.find({}).sort("created_at", -1).to_list(length=200)
    
    admin_btn = '<div style="display:flex;justify-content:flex-end;margin-bottom:25px;"><a href="/admin/create_actor" style="background:var(--accent);color:#fff;padding:12px 24px;border-radius:8px;font-weight:700;text-decoration:none;font-size:14px;box-shadow:0 4px 15px rgba(229,9,20,0.3);">➕ Create New Actor</a></div>' if role == 'admin' else ""
    
    h = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:20px;">'
    for act in all_actors:
        aid = str(act["_id"])
        v_time = str(act.get("created_at", time.time())).replace(".", "")
        h += f'<div style="background:var(--card);border:1px solid var(--border);border-radius:10px;overflow:hidden;cursor:pointer;" onclick="location.href=\'/actor/{aid}\'"><div style="position:relative;padding-top:135%;background:var(--bg3);"><img src="/api/actor/photo?id={aid}&v={v_time}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;"></div><div style="padding:12px;text-align:center;font-size:14px;font-weight:700;color:var(--text);text-overflow:ellipsis;overflow:hidden;white-space:nowrap;">{html.escape(act.get("name",""))}</div></div>'
    h += '</div>' if all_actors else '<div style="color:var(--muted);text-align:center;padding:60px 20px;">🎭 No star profiles created yet.</div>'

    body = f'<div class="main" style="padding-top:30px;max-width:1100px;margin:0 auto;padding-left:20px;padding-right:20px;"><div style="margin-bottom:20px;"><h1 style="font-size:28px;font-weight:900;color:var(--text);margin-bottom:4px;">🎭 Actors Catalog</h1><p style="color:var(--muted);font-size:14px;">Browse star profiles and content grids.</p></div>{admin_btn}{h}</div>'
    return build_page("Actors Directory - Fast Finder", body, "", "actors", role)

# ─────────────────────────────────────────────────────────
# 🎭 ADMIN VIEW: CREATE ACTOR FORM (WITH INTEGRATED SOCIALS)
# ─────────────────────────────────────────────────────────
@actor_routes.get('/admin/create_actor')
async def create_actor_page(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.HTTPFound('/dashboard')
    content = '<form action="/api/create_actor" method="post" enctype="multipart/form-data"><input type="text" name="name" placeholder="Actor Full Name" required><textarea name="bio" placeholder="Biography Details..." style="width:100%;background:var(--bg3);border:1px solid var(--border);padding:12px;color:var(--text);border-radius:6px;min-height:100px;margin-bottom:15px;font-family:inherit;" required></textarea><div class="scard-label" style="margin-bottom:4px;color:var(--muted);">Search Tags (Comma Separated)</div><input type="text" name="tags" placeholder="e.g. SRK, Shahrukh" style="width:100%;background:var(--bg3);border:1px solid var(--border);padding:12px;color:var(--text);border-radius:6px;margin-bottom:15px;"><div class="scard-label" style="margin-bottom:4px;color:var(--muted);">Instagram Profile Link</div><input type="url" name="instagram" placeholder="https://instagram.com/..." style="width:100%;background:var(--bg3);border:1px solid var(--border);padding:12px;color:var(--text);border-radius:6px;margin-bottom:15px;"><div class="scard-label" style="margin-bottom:4px;color:var(--muted);">YouTube Channel Link</div><input type="url" name="youtube" placeholder="https://youtube.com/..." style="width:100%;background:var(--bg3);border:1px solid var(--border);padding:12px;color:var(--text);border-radius:6px;margin-bottom:15px;"><div class="scard-label" style="margin-bottom:4px;color:var(--muted);">Twitter / X Link</div><input type="url" name="twitter" placeholder="https://x.com/..." style="width:100%;background:var(--bg3);border:1px solid var(--border);padding:12px;color:var(--text);border-radius:6px;margin-bottom:15px;"><div class="scard-label" style="margin-bottom:8px;color:var(--muted);">Profile Photo</div><input type="file" name="photo" accept="image/*" required style="color:var(--text);margin-bottom:15px;"><button class="submit-btn" type="submit">Create Actor Profile</button></form><div style="margin-top:15px;text-align:center;"><a href="/actors" style="color:var(--muted);text-decoration:none;font-size:13px;">← Back to Catalog</a></div>'
    return build_page("Create Actor Profile", form_wrapper("Add New Actor", content, req.query.get('err',''), req.query.get('msg','')), "login-bg", "actors", role)

@actor_routes.post('/api/create_actor')
async def api_create_actor(req):
    if (await get_auth(req))[0] != 'admin': return web.json_response({"error":"Unauthorized"}, status=403)
    try:
        r = await req.multipart()
        name, bio, tags_raw, insta, yt, twitter, img_bytes = None, None, "", "", "", "", None
        while True:
            p = await r.next()
            if p is None: break
            if p.name == 'name': name = (await p.read()).decode().strip()
            elif p.name == 'bio': bio = (await p.read()).decode().strip()
            elif p.name == 'tags': tags_raw = (await p.read()).decode().strip()
            elif p.name == 'instagram': insta = (await p.read()).decode().strip()
            elif p.name == 'youtube': yt = (await p.read()).decode().strip()
            elif p.name == 'twitter': twitter = (await p.read()).decode().strip()
            elif p.name == 'photo': img_bytes = await p.read()
        if not name or not bio or not img_bytes: return web.HTTPFound('/admin/create_actor?err=Missing fields')
        
        with io.BytesIO(img_bytes) as buf:
            buf.name = f"{name.replace(' ','_')}.jpg"
            msg = await temp.BOT.send_photo(chat_id=BIN_CHANNEL, photo=buf)
        fid = msg.photo.sizes[-1].file_id if hasattr(msg.photo,"sizes") and msg.photo.sizes else msg.photo.file_id
        
        await actors.insert_one({"name":name,"bio":bio,"tags":[t.strip() for t in tags_raw.split(",") if t.strip()],"photo_url":f"TG_ID:{fid}","social_links":{"instagram":insta,"youtube":yt,"twitter":twitter},"gallery":[],"created_at":time.time()})
        return web.HTTPFound('/actors?msg=Success')
    except Exception as e: return web.HTTPFound(f'/admin/create_actor?err={str(e)}')

# ─────────────────────────────────────────────────────────
# 🌐 PUBLIC VIEW: ACTOR PROFILE MASTER INTERFACE
# ─────────────────────────────────────────────────────────
@actor_routes.get('/actor/{id}')
async def actor_profile_display(req):
    role, _ = await get_auth(req)
    if not role: return web.HTTPFound('/login')
    try:
        aid = req.match_info['id']
        act = await actors.find_one({"_id": ObjectId(aid)})
        if not act: return web.Response(text="Not Found", status=404)
    except: return web.Response(text="Invalid ID", status=400)
    
    act_name = act.get("name", "")
    safe_bio = html.escape(act.get("bio", ""))
    social = act.get("social_links", {})
    gallery_list = act.get("gallery", [])
    t_payload = html.escape(json.dumps(act.get("tags", [])))
    
    v_time = str(act.get("created_at", time.time())).replace(".", "")
    chips = "".join([f'<span style="background:var(--bg3);border:1px solid var(--border);color:var(--muted);font-size:11px;padding:3px 8px;border-radius:4px;font-weight:600;margin-right:4px;margin-bottom:4px;">#{html.escape(t)}</span>' for t in act.get("tags",[])])
    
    soc_html = ""
    if social.get("instagram"): soc_html += f'<a href="{html.escape(social["instagram"])}" target="_blank" style="background:#ff007f;color:#fff;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:700;margin-right:8px;">📸 Instagram</a>'
    if social.get("youtube"): soc_html += f'<a href="{html.escape(social["youtube"])}" target="_blank" style="background:#ff0000;color:#fff;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:700;margin-right:8px;">📺 YouTube</a>'
    if social.get("twitter"): soc_html += f'<a href="{html.escape(social["twitter"])}" target="_blank" style="background:#1da1f2;color:#fff;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:700;margin-right:8px;">🐦 Twitter</a>'

    gal_html = f'<div style="background:var(--card);border:1px dashed var(--border);padding:20px;border-radius:8px;text-align:center;margin-bottom:20px;"><form action="/api/actor/gallery_upload" method="post" enctype="multipart/form-data"><input type="hidden" name="actor_id" value="{aid}"><label style="background:var(--accent);color:#fff;padding:10px 20px;border-radius:6px;font-weight:700;cursor:pointer;font-size:13px;display:inline-block;">📂 Add Image to Gallery<input type="file" name="gallery_img" accept="image/*" style="display:none;" onchange="this.form.submit()"></label></form></div>' if role=='admin' else ""
    if gallery_list:
        gal_html += '<div class="gallery-grid">'
        for i in range(len(gallery_list)):
            del_b = f'<button class="gallery-del-btn" onclick="deleteGalleryImage(\'{aid}\',{i},event)">🗑️ Delete</button>' if role=='admin' else ""
            gal_html += f'<div class="gallery-item-wrap" onclick="openLightbox(\'/api/actor/photo?id={aid}&gallery_idx={i}\')"><img src="/api/actor/photo?id={aid}&gallery_idx={i}" class="gallery-item" loading="lazy">{del_b}</div>'
        gal_html += '</div>'
    else: gal_html += '<div style="color:var(--muted);text-align:center;padding:40px;">🖼️ Gallery is empty.</div>'

    adm_act = f'<div style="display:flex;gap:10px;margin-top:10px;flex-wrap:wrap;"><button onclick="openActorEditModal()" style="background:var(--bg4);border:1px solid var(--border);color:var(--text);padding:8px 16px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;z-index:9999;">✏️ Edit Profile</button><button onclick="deleteActorProfile(\'{aid}\')" style="background:rgba(160,8,8,.78);border:1px solid rgba(229,9,20,.45);color:#fff;padding:8px 16px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;">🗑️ Delete Profile</button><label style="background:var(--bg3);border:1px dashed var(--border);color:var(--text);padding:7px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;">📸 Change Avatar<input type="file" id="avatarUpdateInput" accept="image/*" name="photo" style="display:none;" onchange="updateActorAvatar(\'{aid}\')"></label></div>' if role=='admin' else ""

    tab_engine_ui = f'''
    <style>
        .actor-tab-bar {{ display:flex;gap:10px;border-bottom:2px solid var(--border);margin-bottom:25px; }}
        .actor-tab {{ background:transparent;border:none;color:var(--muted);padding:12px 20px;font-size:15px;font-weight:700;cursor:pointer;position:relative;font-family:inherit; }}
        .actor-tab.active {{ color:var(--text) !important; }}
        .actor-tab.active::after {{ content:\'\';position:absolute;bottom:-2px;left:0;right:0;height:2px;background:var(--accent); }}
        .actor-panel {{ display:none; }}
        .actor-panel.active {{ display:block !important; }}
        
        .gallery-grid {{ display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:14px; }}
        @media(min-width:600px) {{ .gallery-grid {{ grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); }} }}
        .gallery-item-wrap {{ position:relative;border-radius:8px;overflow:hidden;border:1px solid var(--border);aspect-ratio:1;cursor:pointer; }}
        .gallery-item {{ width:100%;height:100%;object-fit:cover; }}
        
        /* ✅ सीएसएस क्लास फिक्स: होवर पर डिलीट बटन अब 100% विज़िबल होगा */
        .gallery-item-wrap:hover .gallery-del-btn {{ opacity:1 !important; }}
        .gallery-del-btn {{ position:absolute;bottom:8px;left:50%;transform:translateX(-50%);background:rgba(160,8,8,.9);border:1px solid var(--accent);color:#fff;padding:4px 10px;border-radius:4px;font-size:10px;font-weight:700;cursor:pointer;z-index:5;opacity:0;transition:opacity 0.15s; }}
        
        .lightbox {{ position:fixed;inset:0;background:rgba(0,0,0,.92);backdrop-filter:blur(15px);z-index:99999;display:none;align-items:center;justify-content:center;opacity:0;transition:opacity .2s; }}
        .lightbox.open {{ display:flex;opacity:1; }}
        .lightbox-img {{ max-width:92%;max-height:88vh;object-fit:contain;border-radius:6px; }}
        .lightbox-close {{ position:absolute;top:20px;right:25px;background:none;border:none;color:#fff;font-size:32px;cursor:pointer; }}

        .search-zone-actor {{ padding:16px 0 0 0; }}
        .search-row1-actor {{ display:flex;align-items:center;gap:10px;margin-bottom:10px; }}
        .search-row2-actor {{ display:flex;align-items:center;justify-content:flex-start;gap:10px;margin-bottom:16px; }}
        @media(min-width:768px){{
          .search-zone-actor {{ display:flex;align-items:center;gap:10px;flex-wrap:nowrap;padding-bottom:16px; }}
          .search-row1-actor {{ flex:1;margin-bottom:0; }}
          .search-row2-actor {{ margin-bottom:0; flex-shrink:0; }}
        }}
        .search-wrap-actor {{ flex:1;min-width:0;display:flex;align-items:center;background:var(--bg3);border:1.5px solid var(--border);border-radius:12px;padding:0 6px 0 18px;gap:8px;overflow:hidden;min-height:38px; }}
        .search-input-actor {{ flex:1;width:100%;background:transparent;border:none;outline:none;color:var(--text);font-size:14px;font-weight:600;padding:6px 0;font-family:inherit; }}
        .search-btn-actor {{ background:var(--accent);color:#fff;border:none;border-radius:12px;padding:0 20px;height:38px;font-size:14px;font-weight:700;cursor:pointer; }}
        
        .cdd-wrap-actor {{ position:relative;user-select:none; }}
        .cdd-btn-actor {{ background:var(--bg3);color:var(--text);border:1.5px solid var(--border);border-radius:999px;padding:8px 28px 8px 14px;font-size:11px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px;white-space:nowrap; }}
        .cdd-arrow-actor {{ position:absolute;right:12px;top:50%;transform:translateY(-50%);pointer-events:none;font-size:9px;color:var(--muted); }}
        .cdd-menu-actor {{ position:absolute;top:calc(100% + 7px);left:50%;transform:translateX(-50%);min-width:max-content;background:var(--bg2);border:1.5px solid var(--border);border-radius:16px;overflow:hidden;z-index:9999;display:none;box-shadow:0 8px 32px rgba(0,0,0,.45); }}
        .cdd-item-actor {{ display:flex;align-items:center;gap:10px;padding:11px 14px;font-size:12px;font-weight:700;color:var(--text);cursor:pointer;border-bottom:1px solid var(--border); }}
        .cdd-item-actor.selected {{ color:var(--accent); }}
        .cdd-radio-actor {{ width:16px;height:16px;border-radius:50%;border:2px solid var(--border);margin-left:auto;display:flex;align-items:center;justify-content:center; }}
        .cdd-radio-dot-actor {{ width:6px;height:6px;border-radius:50%;background:var(--accent);display:none; }}
        .cdd-item-actor.selected .cdd-radio-dot-actor {{ display:block; }}

        .res-grid {{ display:grid;grid-template-columns:1fr;gap:4px;margin-bottom:24px; }}
        @media(min-width:600px){{ .res-grid {{ grid-template-columns:repeat(3,1fr);gap:14px; }} }}
        .file-card {{ background:var(--card);border-radius:6px;overflow:hidden;border:1px solid var(--border);cursor:pointer; }}
        .poster-box {{ position:relative;padding-top:56.25%;background:var(--bg3);overflow:hidden; }}
        .fc-poster {{ position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity .25s; }}
        .fc-poster.loaded {{ opacity:1; }}
        .poster-top {{ position:absolute;top:0;left:0;right:0;display:flex;align-items:center;gap:5px;padding:8px;z-index:3; }}
        .type-chip {{ background:rgba(0,0,0,.72);color:#fff;border-radius:5px;padding:3px 8px;font-size:10px;font-weight:800;border:1px solid rgba(255,255,255,.14); }}
        .size-chip {{ background:rgba(0,0,0,.6);color:#e0e0e0;border-radius:5px;padding:3px 8px;font-size:10px;font-weight:600;border:1px solid rgba(255,255,255,.08); }}
        .source-pill {{ margin-left:auto;border-radius:20px;padding:3px 8px;font-size:9px;font-weight:700;display:inline-flex;align-items:center;gap:4px; }}
        .source-pill.primary {{ background:#14532d;color:#4ade80;border:1px solid #22c55e; }}
        .source-pill.cloud {{ background:#1e3a5f;color:#93c5fd;border:1px solid #60a5fa; }}
        .source-pill.archive {{ background:#7c2d12;color:#fdba74;border:1px solid #fb923c; }}
        .fc-body {{ padding:10px 11px 12px; }}
        .fc-name {{ color:var(--text);font-size:12.5px;font-weight:600;line-height:1.45;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden; }}
    </style>

    <div class="main" style="padding-top:30px;max-width:1100px;margin:0 auto;padding-left:20px;padding-right:20px;">
        <div style="margin-bottom:15px;"><a href="/actors" style="color:var(--muted);text-decoration:none;font-size:14px;font-weight:700;">← Back to Catalog</a></div>
        <div style="display:flex;gap:25px;background:var(--card);border:1px solid var(--border);padding:25px;border-radius:12px;margin-bottom:35px;flex-wrap:wrap;">
            <div style="width:160px;height:220px;background:var(--bg3);border-radius:8px;overflow:hidden;border:1px solid var(--border);flex-shrink:0;">
                <img id="actorMasterAvatarImage" src="/api/actor/photo?id={aid}&v={v_time}" style="width:100%;height:100%;object-fit:cover;">
            </div>
            <div style="flex:1;min-width:300px;display:flex;flex-direction:column;justify-content:center;">
                <h1 style="font-size:32px;font-weight:900;color:var(--text);margin-bottom:2px;">{html.escape(act_name)}</h1>
                <div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:8px;">{chips}</div>
                <div style="display:flex;gap:12px;margin-top:12px;flex-wrap:wrap;">{soc_html}</div>
                {adm_act}
            </div>
        </div>

        <div class="actor-tab-bar">
            <button class="actor-tab active" onclick="switchActorTab(event,'tab-info')">ℹ️ Info</button>
            <button class="actor-tab" onclick="switchActorTab(event,'tab-video')">🎬 Video</button>
            <button class="actor-tab" onclick="switchActorTab(event,'tab-gallery')">🖼️ Gallery</button>
        </div>

        <div id="tab-info" class="actor-panel active"><div style="background:var(--card);border:1px solid var(--border);padding:25px;border-radius:8px;line-height:1.7;color:var(--text);font-size:15px;white-space:pre-line;">{safe_bio}</div></div>

        <div id="tab-video" class="actor-panel">
            <div class="search-zone-actor">
                <div class="search-row1-actor">
                    <div class="search-wrap-actor"><input type="text" id="actor_movie_q" value="" placeholder="Search inside actor movies..." class="search-input-actor"></div>
                    <button onclick="resetActorSearchPage();triggerActorSearchAjax()" class="search-btn-actor">Search</button>
                </div>
                <div class="search-row2-actor">
                    <div class="cdd-wrap-actor">
                        <div class="cdd-btn-actor" id="cddColBtnActor" onclick="toggleActorCdd('col',event)"><span id="cddColLabelActor">📂 All Collections</span></div>
                        <span class="cdd-arrow-actor">&#9660;</span>
                        <div class="cdd-menu-actor" id="cddColMenuActor">
                            <div class="cdd-item-actor selected" data-val="all" onclick="pickActorCol('all','📂 All Collections',this,event)">📂 All Collections<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
                            <div class="cdd-item-actor" data-val="primary" onclick="pickActorCol('primary','🟢 Primary',this,event)">🟢 Primary<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
                            <div class="cdd-item-actor" data-val="cloud" onclick="pickActorCol('cloud','🔵 Cloud',this,event)">🔵 Cloud<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
                            <div class="cdd-item-actor" data-val="archive" onclick="pickActorCol('archive','🟠 Archive',this,event)">🟠 Archive<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
                        </div>
                    </div>
                    <div class="cdd-wrap-actor">
                        <div class="cdd-btn-actor" id="cddModeBtnActor" onclick="toggleActorCdd('mode',event)"><span id="cddModeLabelActor">🖼️ Original TG Thumb</span></div>
                        <span class="cdd-arrow-actor">&#9660;</span>
                        <div class="cdd-menu-actor" id="cddModeMenuActor">
                            <div class="cdd-item-actor selected" data-val="tg" onclick="pickActorMode('tg','🖼️ Original TG Thumb',this,event)">🖼️ Original TG Thumb<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
                            <div class="cdd-item-actor" data-val="none" onclick="pickActorMode('none','⚡ Text Only (Fastest)',this,event)">⚡ Text Only (Fastest)<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
                        </div>
                    </div>
                </div>
            </div>
            <div id="actor_video_results" class="res-grid"></div>
            <div class="pagination" id="actor_page_box" style="display:none;"><button class="pg-btn" id="actor_pBtn" onclick="actorPagePrev()" disabled>Previous</button><span class="pg-info" id="actor_pgInfo">Page 1</span><button class="pg-btn" id="actor_nBtn" onclick="actorPageNext()">Next</button></div>
        </div>
        <div id="tab-gallery" class="actor-panel">{gal_html}</div>
    </div>

    <div id="actorLightboxModal" class="lightbox" onclick="closeLightbox()"><button class="lightbox-close" onclick="closeLightbox()">&times;</button><img id="lightboxTargetImg" class="lightbox-img" src="" onclick="event.stopPropagation()"></div>
    <input type="hidden" id="actor_master_tags_payload" value="{t_payload}">

    <div class="edit-modal" id="actorEditModal" onclick="if(event.target===this)closeActorEditModal()">
        <div class="em-card" style="max-width:550px;background:var(--card);border:1px solid var(--border);padding:25px;border-radius:12px;z-index:100000 !important;">
            <button class="em-close" onclick="closeActorEditModal()" style="position:absolute;top:15px;right:20px;background:none;border:none;color:var(--muted);font-size:24px;cursor:pointer;">&#10005;</button>
            <div class="em-title" style="font-size:18px;font-weight:700;margin-bottom:20px;color:var(--text);">✏️ Edit Actor Profile Matrix</div>
            <form action="/api/actor/update_profile" method="post">
                <input type="hidden" name="actor_id" value="{aid}">
                <div class="scard-label">Actor Full Name</div>
                <input type="text" name="name" value="{html.escape(act_name)}" class="em-input" style="width:100%;background:var(--bg);border:1px solid var(--border);padding:12px;color:var(--text);margin-bottom:15px;border-radius:6px;" required>
                <div class="scard-label">Biography Details</div>
                <textarea name="bio" class="em-input" style="width:100%;background:var(--bg);border:1px solid var(--border);min-height:120px;font-family:inherit;padding:10px;line-height:1.5;color:var(--text);margin-bottom:15px;border-radius:6px;" required>{safe_bio}</textarea>
                <div class="scard-label">Search Tags (Comma Separated)</div>
                <input type="text" name="tags" value="{html.escape(', '.join(act.get("tags",[])))}" class="em-input" style="width:100%;background:var(--bg);border:1px solid var(--border);padding:12px;color:var(--text);margin-bottom:15px;border-radius:6px;">
                <div class="em-title" style="font-size:14px;margin-top:15px;margin-bottom:10px;color:var(--text);">🌐 Social Media Channels Matrix</div>
                <div class="scard-label">Instagram Link</div>
                <input type="url" name="instagram" value="{html.escape(social.get('instagram',''))}" class="em-input" style="width:100%;background:var(--bg);border:1px solid var(--border);padding:12px;color:var(--text);margin-bottom:15px;border-radius:6px;">
                <div class="scard-label">YouTube Channel Link</div>
                <input type="url" name="youtube" value="{html.escape(social.get('youtube',''))}" class="em-input" style="width:100%;background:var(--bg);border:1px solid var(--border);padding:12px;color:var(--text);margin-bottom:15px;border-radius:6px;">
                <div class="scard-label">Twitter / X Profile Link</div>
                <input type="url" name="twitter" value="{html.escape(social.get('twitter',''))}" class="em-input" style="width:100%;background:var(--bg);border:1px solid var(--border);padding:12px;color:var(--text);margin-bottom:20px;border-radius:6px;">
                <button class="em-save-btn" type="submit" style="width:100%;background:var(--accent);color:#fff;border:none;padding:14px;font-weight:700;border-radius:6px;cursor:pointer;font-size:15px;">Save Changes</button>
            </form>
        </div>
    </div>

    <script>
        var actCurPage=1, actOffset=0, actNextOffset="", actLimit=21, actorDefaultName="{html.escape(act_name)}", actCol="all", actMode="tg";
        function closeActorCdds(){{ document.getElementById('cddColMenuActor').style.display='none';document.getElementById('cddColBtnActor').classList.remove('open');document.getElementById('cddModeMenuActor').style.display='none';document.getElementById('cddModeBtnActor').classList.remove('open'); }}
        function toggleActorCdd(w,e){{ if(e)e.stopPropagation(); var mId=w==='col'?'cddColMenuActor':'cddModeMenuActor', bId=w==='col'?'cddColBtnActor':'cddModeBtnActor', oId=w==='col'?'cddModeMenuActor':'cddColMenuActor', obId=w==='col'?'cddModeBtnActor':'cddColBtnActor'; document.getElementById(oId).style.display='none';document.getElementById(obId).classList.remove('open'); var m=document.getElementById(mId), b=document.getElementById(bId); if(m.style.display==='block') {{ m.style.display='none';b.classList.remove('open'); }} else {{ m.style.display='block';b.classList.add('open'); }} }}
        function pickActorCol(v,l,el,e){{ if(e)e.stopPropagation(); actCol=v;document.getElementById('cddColLabelActor').textContent=l;document.querySelectorAll('#cddColMenuActor .cdd-item-actor').forEach(function(i){{i.classList.remove('selected');}});el.classList.add('selected');closeActorCdds();resetActorSearchPage();triggerActorSearchAjax(); }}
        function pickActorMode(v,l,el,e){{ if(e)e.stopPropagation(); actMode=v;document.getElementById('cddModeLabelActor').textContent=l;document.querySelectorAll('#cddModeMenuActor .cdd-item-actor').forEach(function(i){{i.classList.remove('selected');}});el.classList.add('selected');closeActorCdds();resetActorSearchPage();triggerActorSearchAjax(); }}
        document.addEventListener('click', closeActorCdds);
        
        function openLightbox(s) {{ var lb=document.getElementById('actorLightboxModal');document.getElementById('lightboxTargetImg').src=s;lb.style.display='flex';setTimeout(function(){{lb.classList.add('open');}},10); }}
        function closeLightbox() {{ var lb=document.getElementById('actorLightboxModal');lb.classList.remove('open');setTimeout(function(){{lb.style.display='none';}},200); }}
        function switchActorTab(evt,tId) {{ var p=document.querySelectorAll('.actor-panel'), t=document.querySelectorAll('.actor-tab'); for(var i=0;i<p.length;i++)p[i].classList.remove('active'); for(var j=0;j<t.length;j++)t[j].classList.remove('active'); document.getElementById(tId).classList.add('active');evt.currentTarget.classList.add('active'); if(tId==='tab-video'&&document.getElementById('actor_video_results').innerHTML==="")triggerActorSearchAjax(); }}
        function resetActorSearchPage() {{ actCurPage=1; actOffset=0; }}

        async function triggerActorSearchAjax() {{
            var typedQ=document.getElementById('actor_movie_q').value.trim(), q=typedQ||actorDefaultName, grid=document.getElementById('actor_video_results');
            grid.className='res-grid mode-'+actMode; grid.innerHTML='<div class="spin-wrap"><div class="spinner"></div><span>Filtering Matrix...</span></div>';
            try {{
                var r=await fetch('/api/actor/search?q='+encodeURIComponent(q)+'&offset='+actOffset+'&col='+actCol+'&mode='+actMode+'&id={aid}');
                var d=await r.json();
                if(!d.results||!d.results.length){{ grid.innerHTML='<div class="empty"><p>No video assets found.</p></div>';document.getElementById('actor_page_box').style.display='none';return; }}
                var h='';
                d.results.forEach(function(f){{
                    var sc=f.source.toLowerCase(), pHtml='';
                    if(actMode!=='none') pHtml='<div class="poster-box"><img src="'+f.tg_thumb+'" class="fc-poster" onload="this.classList.add(\\'loaded\\')" loading="lazy"><div class="poster-top"><span class="type-chip">'+f.type.toUpperCase()+'</span><span class="size-chip">'+f.size+'</span><span class="source-pill '+sc+'"><span class="source-dot"></span>'+sc.toUpperCase()+'</span></div></div>';
                    else pHtml='<div class="fc-text-info"><span class="tc-type">'+f.type.toUpperCase()+'</span><span class="tc-size">'+f.size+'</span><span class="source-pill '+sc+'" style="margin-left:auto"><span class="source-dot"></span>'+sc.toUpperCase()+'</span></div>';
                    h+='<div class="file-card" onclick="window.open(\\''+f.watch+'\\',\\'_blank\\')">'+pHtml+'<div class="fc-body"><div class="fc-name">'+f.name+'</div></div></div>';
                }});
                grid.innerHTML=h; actNextOffset=d.next_offset; document.getElementById('actor_page_box').style.display='flex'; document.getElementById('actor_pBtn').disabled=(actOffset===0);document.getElementById('actor_nBtn').disabled=!actNextOffset;document.getElementById('actor_pgInfo').textContent='Page '+actCurPage;
            }} catch(e){{ grid.innerHTML='<div class="empty"><p>Sync timeout error.</p></div>'; }}
        }}

        function openActorEditModal() {{ document.getElementById('actorEditModal').classList.add('open'); }}
        function closeActorEditModal() {{ document.getElementById('actorEditModal').classList.remove('open'); }}

        async function updateActorAvatar(actorId) {{
            var input=document.getElementById('avatarUpdateInput'); if(!input.files||!input.files[0]) return;
            var fd=new FormData(); fd.append('actor_id',actorId); fd.append('photo',input.files[0]);
            try {{
                var r=await fetch('/api/actor/update_avatar',{{method:'POST',body:fd}}); var d=await r.json();
                if(d.success){{ document.getElementById('actorMasterAvatarImage').src='/api/actor/photo?id='+actorId+'&t='+new Date().getTime();alert("Avatar updated successfully!"); }}
                else alert(d.error);
            }} catch(e){{ alert("Upload error!"); }}
        }}

        async function deleteGalleryImage(actorId,idx,e) {{ if(e)e.stopPropagation(); if(!confirm("Delete this photo permanently?")) return;
            try {{
                var r=await fetch('/api/actor/gallery_delete',{{method:'POST',body:JSON.stringify({{actor_id:actorId,index:idx}}),headers:{{'Content-Type':'application/json'}}}}); var d=await r.json();
                if(d.success){{ alert("Removed!");location.reload(); }} else alert(d.error);
            }} catch(e){{ alert("Deletion error!"); }}
        }}

        async function deleteActorProfile(id) {{ if(!confirm("Permanently delete profile?")) return;
            try {{ var r=await fetch('/api/actor/delete?id='+id,{{method:'POST'}}); var d=await r.json(); if(d.success){{ alert("Deleted!");location.href='/actors'; }} else alert(d.error); }} catch(e){{ alert("Network error!"); }}
        }}
        function actorPageNext() {{ if(actNextOffset){{ actCurPage++;actOffset=actNextOffset;triggerActorSearchAjax();scrollTo(0,350); }} }}
        function actorPagePrev() {{ if(actCurPage>1){{ actCurPage--;actOffset=Math.max(0,actOffset-actLimit);triggerActorSearchAjax();scrollTo(0,350); }} }}
        document.getElementById('actor_movie_q').addEventListener('keydown',function(e){{if(e.key==='Enter'){{resetActorSearchPage();triggerActorSearchAjax();}}}});
    </script>
    '''
    return build_page(f"{act_name} - Profile Matrix", tab_engine_ui, "", "actors", role)

@actor_routes.get('/api/actor/search')
async def api_actor_search_handler(req):
    if not (await get_auth(req))[0]: return web.json_response({"results":[]})
    aid = req.query.get("id")
    off = max(0, int(req.query.get("offset","0")))
    col = req.query.get("col","all").lower()
    mode = req.query.get("mode","tg").lower()
    
    actor = await actors.find_one({"_id": ObjectId(aid)})
    if not actor: return web.json_response({"results":[]})
    
    q_custom = req.query.get("q","").strip()
    all_m, next_offset = await get_actor_search_results(q_custom if q_custom else actor["name"], actor.get("tags",[]), max_results=21, offset=off, collection_type=col)
    
    res = []
    for d in all_m:
        fid = d.get("file_ref") or d.get("_id")
        sc = d.get("source_col","primary")
        v_salt = d.get("thumb_url","")[-8:] if (d.get("thumb_url") and d["thumb_url"].startswith("TG_ID:")) else "0"
        res.append({"file_id":str(d["_id"]),"name":d.get("file_name"),"size":get_size(d.get("file_size",0)),"type":d.get("file_type","video"),"source":sc.capitalize(),"tg_thumb":f"/api/thumb?file_id={d['_id']}&col={sc}&v={v_salt}","watch":f"/setup_stream?file_id={fid}&mode=watch"})
    return web.json_response({"results":res,"next_offset":next_offset})

@actor_routes.post('/api/actor/update_profile')
async def api_actor_update_profile(req):
    if (await get_auth(req))[0] != 'admin': return web.json_response({"error":"Unauthorized"}, status=403)
    d = await req.post()
    aid = d.get('actor_id')
    await actors.update_one({"_id":ObjectId(aid)},{"$set":{"name":d.get('name').strip(),"bio":d.get('bio').strip(),"tags":[t.strip() for t in d.get('tags','').split(",") if t.strip()],"social_links":{"instagram":d.get('instagram').strip(),"youtube":d.get('youtube').strip(),"twitter":d.get('twitter').strip()}}})
    return web.HTTPFound(f'/actor/{aid}?msg=Updated')

@actor_routes.post('/api/actor/update_avatar')
async def api_actor_update_avatar(req):
    if (await get_auth(req))[0] != 'admin': return web.json_response({"success":False}, status=403)
    d = await req.post()
    aid = d.get("actor_id")
    with io.BytesIO(d.get("photo").file.read()) as buf:
        buf.name = f"avatar_{aid}.jpg"
        msg = await temp.BOT.send_photo(chat_id=BIN_CHANNEL, photo=buf)
    fid = msg.photo.sizes[-1].file_id if hasattr(msg.photo,"sizes") and msg.photo.sizes else msg.photo.file_id
    await actors.update_one({"_id":ObjectId(aid)},{"$set":{"photo_url":f"TG_ID:{fid}","created_at":time.time()}})
    return web.json_response({"success":True})

@actor_routes.post('/api/actor/gallery_upload')
async def api_actor_gallery_upload(req):
    if (await get_auth(req))[0] != 'admin': return web.json_response({"error":"Unauthorized"}, status=403)
    r = await req.multipart()
    aid, img_bytes = None, None
    while True:
        p = await r.next()
        if p is None: break
        if p.name == 'actor_id': aid = (await p.read()).decode().strip()
        elif p.name == 'gallery_img': img_bytes = await p.read()
    with io.BytesIO(img_bytes) as buf:
        buf.name = "gallery.jpg"
        msg = await temp.BOT.send_photo(chat_id=BIN_CHANNEL, photo=buf)
    fid = msg.photo.sizes[-1].file_id if hasattr(msg.photo,"sizes") and msg.photo.sizes else msg.photo.file_id
    await actors.update_one({"_id":ObjectId(aid)},{"$push":{"gallery":f"TG_ID:{fid}"}})
    return web.HTTPFound(f'/actor/{aid}?msg=Uploaded')

@actor_routes.post('/api/actor/gallery_delete')
async def api_actor_gallery_delete(req):
    if (await get_auth(req))[0] != 'admin': return web.json_response({"success":False}, status=403)
    b = await req.json()
    act = await actors.find_one({"_id":ObjectId(b.get("actor_id"))})
    gal = act.get("gallery",[])
    if 0 <= b.get("index",-1) < len(gal):
        del gal[b["index"]]
        await actors.update_one({"_id":ObjectId(b["actor_id"])},{"$set":{"gallery":gal}})
        return web.json_response({"success":True})
    return web.json_response({"success":False})

@actor_routes.post('/api/actor/delete')
async def api_actor_delete(req):
    if (await get_auth(req))[0] != 'admin': return web.json_response({"error":"Unauthorized"}, status=403)
    await actors.delete_one({"_id":ObjectId(req.query.get("id"))})
    return web.json_response({"success":True})
