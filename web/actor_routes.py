import io
import gc
import time
import json
import html
from aiohttp import web
from bson.objectid import ObjectId
from utils import temp, get_size
from info import BIN_CHANNEL
from database.ia_filterdb import actors, get_actor_search_results
from web.web_assets import build_page, get_auth, form_wrapper

actor_routes = web.RouteTableDef()

# ─────────────────────────────────────────────────────────
# 🎭 ACTORS DIRECTORY CATALOG PAGE
# ─────────────────────────────────────────────────────────
@actor_routes.get('/actors')
async def actors_directory_page(req):
    role, _ = await get_auth(req)
    if not role: return web.HTTPFound('/login')

    all_actors = await actors.find({}).sort("created_at", -1).to_list(length=200)

    admin_btn = ''
    if role == 'admin':
        admin_btn = '<div style="display:flex;justify-content:flex-end;margin-bottom:25px;"><a href="/admin/create_actor" style="background:var(--accent);color:#fff;padding:12px 24px;border-radius:8px;font-weight:700;text-decoration:none;font-size:14px;box-shadow:0 4px 15px rgba(229,9,20,.3);">➕ Create New Actor</a></div>'

    if not all_actors:
        grid = '<div style="color:var(--muted);text-align:center;padding:60px 20px;grid-column:1/-1;">🎭 No actor profiles created yet.</div>'
    else:
        cards = []
        for act in all_actors:
            act_id = str(act["_id"])
            photo_v = int(act.get("photo_updated_at") or act.get("created_at") or 0)
            name = html.escape(act.get('name', ''))
            cards.append(f'''<div class="ac-card" onclick="location.href='/actor/{act_id}'">
  <div class="ac-img-wrap"><img src="/api/actor/photo?id={act_id}&v={photo_v}" class="ac-img" loading="lazy" onload="this.classList.add('loaded')"></div>
  <div class="ac-name">{name}</div>
</div>''')
        grid = f'''<style>
.ac-card{{background:var(--card);border:1px solid var(--border);border-radius:10px;overflow:hidden;cursor:pointer;transition:transform .2s,box-shadow .2s}}
.ac-card:hover{{transform:translateY(-4px);box-shadow:0 12px 32px rgba(0,0,0,.5);border-color:rgba(229,9,20,.35)}}
.ac-img-wrap{{position:relative;padding-top:135%;background:var(--bg3);overflow:hidden}}
.ac-img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity .35s ease}}
.ac-img.loaded{{opacity:1}}
.ac-name{{padding:10px 12px;font-size:14px;font-weight:700;color:var(--text);overflow:hidden;white-space:nowrap;text-overflow:ellipsis;text-align:center}}
</style><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:20px;">{''.join(cards)}</div>'''

    body = f'''<div class="main" style="padding:30px 20px 0;max-width:1100px;margin:0 auto">
  <div style="margin-bottom:20px"><h1 style="font-size:28px;font-weight:900;color:var(--text);margin-bottom:4px">🎭 Actors Catalog</h1>
  <p style="color:var(--muted);font-size:14px">Browse verified star profiles and linked content grids.</p></div>
  {admin_btn}{grid}</div>'''
    return build_page("Actors Directory - Fast Finder", body, "", "actors", role)


# ─────────────────────────────────────────────────────────
# 🎭 ADMIN: CREATE ACTOR FORM
# ─────────────────────────────────────────────────────────
@actor_routes.get('/admin/create_actor')
async def create_actor_page(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.HTTPFound('/dashboard')

    content = '''<form action="/api/create_actor" method="post" enctype="multipart/form-data">
  <input type="text" name="name" placeholder="Actor Full Name (e.g., Shah Rukh Khan)" required>
  <textarea name="bio" placeholder="Actor Biography / Details..." style="width:100%;background:var(--bg3);border:1px solid var(--border);padding:12px;color:var(--text);border-radius:6px;min-height:100px;outline:none;margin-bottom:15px;font-family:inherit" required></textarea>
  <div class="scard-label" style="margin-bottom:4px;color:var(--muted)">Search Tags (Comma Separated)</div>
  <input type="text" name="tags" placeholder="e.g. SRK, Shahrukh, King Khan" style="width:100%;background:var(--bg3);border:1px solid var(--border);padding:12px;color:var(--text);border-radius:6px;margin-bottom:15px;outline:none">
  <div class="scard-label" style="margin-bottom:8px;color:var(--muted)">Actor Profile Photo</div>
  <input type="file" name="photo" accept="image/*" required style="padding:10px 0;color:var(--text)">
  <button class="submit-btn" type="submit" style="background:var(--accent);color:#fff;width:100%;padding:14px;border:0;border-radius:6px;font-weight:700;cursor:pointer;margin-top:10px">Create Actor Profile</button>
</form>
<div style="margin-top:15px;text-align:center"><a href="/actors" style="color:var(--muted);text-decoration:none;font-size:13px">← Back to Actors Catalog</a></div>'''
    return build_page("Create Actor Profile", form_wrapper("Add New Actor", content, req.query.get('err',''), req.query.get('msg','')), "login-bg", "actors", role)


# ─────────────────────────────────────────────────────────
# ⚙️ ADMIN API: CREATE ACTOR
# ─────────────────────────────────────────────────────────
@actor_routes.post('/api/create_actor')
async def api_create_actor(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403)

    try:
        reader = await req.multipart()
        name, bio, tags_raw, image_bytes = None, None, "", None
        while True:
            part = await reader.next()
            if part is None: break
            if part.name == 'name': name = (await part.read()).decode().strip()
            elif part.name == 'bio': bio = (await part.read()).decode().strip()
            elif part.name == 'tags': tags_raw = (await part.read()).decode().strip()
            elif part.name == 'photo': image_bytes = await part.read()

        if not name or not bio or not image_bytes:
            return web.HTTPFound('/admin/create_actor?err=All fields are required!')

        tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]

        with io.BytesIO(image_bytes) as buf:
            buf.name = f"{name.replace(' ', '_')}.jpg"
            msg = await temp.BOT.send_photo(chat_id=BIN_CHANNEL, photo=buf)

        if not msg or not msg.photo:
            return web.HTTPFound('/admin/create_actor?err=Telegram Upload Failed!')

        # ✅ FIX: Pyrogram में msg.photo एक list है — [-1] सबसे बड़ी size
        tg_photo_id = msg.photo[-1].file_id

        now_ts = int(time.time())
        await actors.insert_one({
            "name": name, "bio": bio, "tags": tags_list,
            "photo_url": f"TG_ID:{tg_photo_id}",
            "photo_updated_at": now_ts,
            "social_links": {"instagram": "", "youtube": "", "twitter": ""},
            "gallery": [], "created_at": now_ts
        })
        return web.HTTPFound('/actors?msg=Actor Profile created successfully!')
    except Exception as e:
        return web.HTTPFound(f'/admin/create_actor?err=Server Error: {str(e)}')


# ─────────────────────────────────────────────────────────
# 🖼️ PHOTO ENGINE — CACHE OPTIMIZED
# ─────────────────────────────────────────────────────────
@actor_routes.get('/api/actor/photo')
async def get_actor_photo(req):
    actor_id = req.query.get("id")
    img_index = req.query.get("gallery_idx")
    if not actor_id: return web.Response(status=400)

    try:
        doc = await actors.find_one({"_id": ObjectId(actor_id)})
        if not doc: return web.Response(status=404)

        if img_index is not None:
            idx = int(img_index)
            gallery = doc.get("gallery", [])
            if idx < 0 or idx >= len(gallery):
                return web.Response(status=404)
            raw_url = gallery[idx]
        else:
            raw_url = doc.get("photo_url")

        if not raw_url or not raw_url.startswith("TG_ID:"):
            return web.Response(status=404)

        file_data = await temp.BOT.download_media(raw_url.replace("TG_ID:", ""), in_memory=True)
        if not file_data: return web.Response(status=404)

        body_bytes = file_data.getvalue()
        file_data.close()
        del file_data

        # ✅ ?v= tag की वजह से दोनों cases में safe immutable cache
        return web.Response(
            body=body_bytes,
            content_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=31536000, immutable",
                     "Content-Disposition": 'inline; filename="photo.jpg"'}
        )
    except Exception:
        return web.Response(status=500)
    finally:
        gc.collect()


# ─────────────────────────────────────────────────────────
# 🌐 ACTOR PROFILE PAGE
# ─────────────────────────────────────────────────────────
@actor_routes.get('/actor/{id}')
async def actor_profile_display(req):
    role, _ = await get_auth(req)
    if not role: return web.HTTPFound('/login')

    try:
        actor_id = req.match_info['id']
        actor = await actors.find_one({"_id": ObjectId(actor_id)})
        if not actor: return web.Response(text="Actor Not Found", status=404)
    except:
        return web.Response(text="Invalid ID", status=400)

    actor_name   = actor["name"]
    tags_list    = actor.get("tags", [])
    social       = actor.get("social_links", {})
    gallery_list = actor.get("gallery", [])
    safe_bio     = html.escape(actor.get("bio", ""))
    photo_v      = int(actor.get("photo_updated_at") or actor.get("created_at") or 0)
    tags_json    = html.escape(json.dumps(tags_list))

    tags_html = '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;">' + \
        ''.join(f'<span style="background:var(--bg3);border:1px solid var(--border);color:var(--muted);font-size:11px;padding:3px 8px;border-radius:4px;font-weight:600;">#{html.escape(t)}</span>' for t in tags_list) + \
        '</div>'

    social_html = '<div style="display:flex;gap:12px;margin-top:12px;flex-wrap:wrap;">'
    if social.get("instagram"): social_html += f'<a href="{html.escape(social["instagram"])}" target="_blank" style="background:#ff007f;color:#fff;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:700">📸 Instagram</a>'
    if social.get("youtube"):   social_html += f'<a href="{html.escape(social["youtube"])}" target="_blank" style="background:#ff0000;color:#fff;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:700">📺 YouTube</a>'
    if social.get("twitter"):   social_html += f'<a href="{html.escape(social["twitter"])}" target="_blank" style="background:#1da1f2;color:#fff;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:700">🐦 Twitter / X</a>'
    social_html += '</div>'

    # Gallery HTML
    gallery_html = ""
    if role == 'admin':
        gallery_html += f'''<div style="background:var(--card);border:1px dashed var(--border);padding:20px;border-radius:8px;text-align:center;margin-bottom:20px">
  <form action="/api/actor/gallery_upload" method="post" enctype="multipart/form-data" style="margin:0">
    <input type="hidden" name="actor_id" value="{actor_id}">
    <label style="background:var(--accent);color:#fff;padding:10px 20px;border-radius:6px;font-weight:700;cursor:pointer;font-size:13px;display:inline-block">
      📂 Add Image to Gallery
      <input type="file" name="gallery_img" accept="image/*" style="display:none" onchange="this.form.submit()">
    </label>
  </form></div>'''

    if not gallery_list:
        gallery_html += '<div style="color:var(--muted);text-align:center;padding:40px">🖼️ Gallery is empty.</div>'
    else:
        gallery_html += '<div class="gallery-grid">'
        for i in range(len(gallery_list)):
            del_btn = f'<button class="gallery-del-btn" onclick="deleteGalleryImage(\'{actor_id}\',{i},event)">🗑️ Delete</button>' if role == 'admin' else ""
            gallery_html += f'<div class="gallery-item-wrap" onclick="openLightbox(\'/api/actor/photo?id={actor_id}&gallery_idx={i}\')"><img src="/api/actor/photo?id={actor_id}&gallery_idx={i}" class="gallery-item" loading="lazy" onload="this.classList.add(\'gl-loaded\')">{del_btn}</div>'
        gallery_html += '</div>'

    admin_actions = ""
    if role == 'admin':
        admin_actions = f'''<div style="display:flex;gap:10px;margin-top:10px;flex-wrap:wrap">
  <button onclick="openActorEditModal()" style="background:var(--bg4);border:1px solid var(--border);color:var(--text);padding:8px 16px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">✏️ Edit Profile & Socials</button>
  <button onclick="deleteActorProfile('{actor_id}')" style="background:rgba(160,8,8,.78);border:1px solid rgba(229,9,20,.45);color:#fff;padding:8px 16px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">🗑️ Delete Profile</button>
  <label style="background:var(--bg3);border:1px dashed var(--border);color:var(--text);padding:7px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;display:inline-block">
    📸 Change Avatar
    <input type="file" id="avatarUpdateInput" accept="image/*" style="display:none" onchange="updateActorAvatar('{actor_id}')">
  </label></div>'''

    edit_modal = f'''<div class="edit-modal" id="actorEditModal" onclick="if(event.target===this)closeActorEditModal()">
  <div class="em-card" style="max-width:550px;background:var(--card);border:1px solid var(--border);padding:25px;border-radius:12px">
    <button class="em-close" onclick="closeActorEditModal()" style="position:absolute;top:15px;right:20px;background:none;border:none;color:var(--muted);font-size:24px;cursor:pointer">&#10005;</button>
    <div class="em-title" style="font-size:18px;font-weight:700;margin-bottom:20px;color:var(--text)">✏️ Edit Actor Profile</div>
    <form action="/api/actor/update_profile" method="post">
      <input type="hidden" name="actor_id" value="{actor_id}">
      <div class="scard-label">Actor Full Name</div>
      <input type="text" name="name" value="{html.escape(actor_name)}" class="em-input" style="width:100%;background:var(--bg);border:1px solid var(--border);padding:12px;color:var(--text);margin-bottom:15px;border-radius:6px" required>
      <div class="scard-label">Biography</div>
      <textarea name="bio" class="em-input" style="width:100%;background:var(--bg);border:1px solid var(--border);min-height:120px;font-family:inherit;padding:10px;line-height:1.5;color:var(--text);margin-bottom:15px;border-radius:6px" required>{safe_bio}</textarea>
      <div class="scard-label">Search Tags (Comma Separated)</div>
      <input type="text" name="tags" value="{html.escape(', '.join(tags_list))}" placeholder="e.g. SRK, Shahrukh" class="em-input" style="width:100%;background:var(--bg);border:1px solid var(--border);padding:12px;color:var(--text);margin-bottom:15px;border-radius:6px">
      <div class="em-title" style="font-size:14px;margin-top:15px;margin-bottom:10px;color:var(--text)">🌐 Social Media</div>
      <div class="scard-label">Instagram</div>
      <input type="url" name="insta" value="{html.escape(social.get('instagram',''))}" placeholder="https://instagram.com/..." class="em-input" style="width:100%;background:var(--bg);border:1px solid var(--border);padding:12px;color:var(--text);margin-bottom:15px;border-radius:6px">
      <div class="scard-label">YouTube</div>
      <input type="url" name="yt" value="{html.escape(social.get('youtube',''))}" placeholder="https://youtube.com/..." class="em-input" style="width:100%;background:var(--bg);border:1px solid var(--border);padding:12px;color:var(--text);margin-bottom:15px;border-radius:6px">
      <div class="scard-label">Twitter / X</div>
      <input type="url" name="twitter" value="{html.escape(social.get('twitter',''))}" placeholder="https://x.com/..." class="em-input" style="width:100%;background:var(--bg);border:1px solid var(--border);padding:12px;color:var(--text);margin-bottom:20px;border-radius:6px">
      <button class="em-save-btn" type="submit" style="width:100%;background:var(--accent);color:#fff;border:none;padding:14px;font-weight:700;border-radius:6px;cursor:pointer;font-size:15px">Save Changes</button>
    </form>
  </div></div>'''

    page = f'''<style>
  /* ── Tabs ── */
  .actor-tab-bar{{display:flex;gap:10px;border-bottom:2px solid var(--border);margin-bottom:25px}}
  .actor-tab{{background:transparent;border:none;color:var(--muted);padding:12px 20px;font-size:15px;font-weight:700;cursor:pointer;transition:color .2s;position:relative;font-family:inherit}}
  .actor-tab.active{{color:var(--text)!important}}
  .actor-tab.active::after{{content:'';position:absolute;bottom:-2px;left:0;right:0;height:2px;background:var(--accent)}}
  .actor-panel{{display:none}}.actor-panel.active{{display:block!important}}

  /* ── Gallery ── */
  .gallery-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:14px}}
  @media(min-width:600px){{.gallery-grid{{grid-template-columns:repeat(auto-fill,minmax(180px,1fr))}}}}
  .gallery-item-wrap{{position:relative;border-radius:8px;overflow:hidden;border:1px solid var(--border);aspect-ratio:1;cursor:pointer}}
  .gallery-item{{width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity .35s ease,transform .25s ease}}
  .gallery-item.gl-loaded{{opacity:1}}
  .gallery-item-wrap:hover .gallery-item{{transform:scale(1.05)}}
  .gallery-del-btn{{position:absolute;bottom:8px;left:50%;transform:translateX(-50%);background:rgba(160,8,8,.85);border:1px solid var(--accent);color:#fff;padding:4px 10px;border-radius:4px;font-size:10px;font-weight:700;cursor:pointer;z-index:5;opacity:0;transition:opacity .15s}}
  .gallery-item-wrap:hover .gallery-del-btn{{opacity:1}}

  /* ── Lightbox ── */
  .lightbox{{position:fixed;inset:0;background:rgba(0,0,0,.92);backdrop-filter:blur(16px);z-index:99999;display:none;align-items:center;justify-content:center;opacity:0;transition:opacity .25s ease}}
  .lightbox.open{{display:flex;opacity:1}}
  .lightbox-img{{max-width:92%;max-height:88vh;object-fit:contain;border-radius:6px;box-shadow:0 10px 40px rgba(0,0,0,.8);transform:scale(.92);transition:transform .3s cubic-bezier(.34,1.56,.64,1)}}
  .lightbox.open .lightbox-img{{transform:scale(1)}}
  .lightbox-close{{position:absolute;top:20px;right:25px;background:none;border:none;color:#fff;font-size:32px;cursor:pointer;opacity:.7;transition:opacity .15s,transform .15s}}
  .lightbox-close:hover{{opacity:1;transform:scale(1.15)}}

  /* ── Search zone ── */
  .search-zone-actor{{padding:16px 0 0}}
  .search-row1-actor{{display:flex;align-items:center;gap:10px;margin-bottom:10px}}
  .search-row2-actor{{display:flex;align-items:center;gap:10px;margin-bottom:16px}}
  @media(min-width:768px){{.search-zone-actor{{display:flex;align-items:center;gap:10px;flex-wrap:nowrap;padding-bottom:16px}}.search-row1-actor{{flex:1;margin-bottom:0}}.search-row2-actor{{margin-bottom:0;flex-shrink:0}}}}
  .search-wrap-actor{{flex:1;min-width:0;display:flex;align-items:center;background:var(--bg3);border:1.5px solid var(--border);border-radius:12px;padding:0 6px 0 18px;gap:8px;overflow:hidden;min-height:38px}}
  .search-input-actor{{flex:1;min-width:0;width:100%;background:transparent;border:none;outline:none;color:var(--text);font-size:14px;font-weight:600;padding:6px 0;font-family:inherit}}
  .search-input-actor::placeholder{{color:var(--muted);font-weight:400}}
  .search-btn-actor{{flex-shrink:0;background:var(--accent);color:#fff;border:none;border-radius:12px;padding:0 20px;height:38px;font-size:14px;font-weight:700;cursor:pointer;transition:transform .15s,background .15s}}
  .search-btn-actor:hover{{transform:scale(1.03)}}

  /* ── Dropdown ── */
  .cdd-wrap-actor{{flex:0 1 auto;min-width:0;position:relative;user-select:none}}
  .cdd-btn-actor{{background:var(--bg3);color:var(--text);border:1.5px solid var(--border);border-radius:999px;padding:8px 28px 8px 14px;font-size:11px;font-weight:700;cursor:pointer;font-family:inherit;display:inline-flex;align-items:center;gap:5px;white-space:nowrap;transition:border-color .15s}}
  .cdd-btn-actor:hover,.cdd-btn-actor.open{{border-color:var(--accent)}}
  .cdd-arrow-actor{{position:absolute;right:12px;top:50%;transform:translateY(-50%);pointer-events:none;font-size:9px;color:var(--muted);transition:transform .2s}}
  .cdd-btn-actor.open + .cdd-arrow-actor{{transform:translateY(-50%) rotate(180deg)}}
  .cdd-menu-actor{{position:absolute;top:calc(100% + 7px);left:50%;transform:translateX(-50%);min-width:max-content;background:var(--bg2);border:1.5px solid var(--border);border-radius:16px;overflow:hidden;z-index:9999;box-shadow:0 8px 32px rgba(0,0,0,.45);display:none}}
  .cdd-item-actor{{display:flex;align-items:center;gap:10px;padding:11px 14px;font-size:12px;font-weight:700;color:var(--text);cursor:pointer;transition:background .12s;border-bottom:1px solid var(--border)}}
  .cdd-item-actor:last-child{{border-bottom:none}}
  .cdd-item-actor:hover{{background:var(--bg3)}}
  .cdd-item-actor.selected{{color:var(--accent)}}
  .cdd-radio-actor{{width:16px;height:16px;border-radius:50%;border:2px solid var(--border);margin-left:auto;flex-shrink:0;display:flex;align-items:center;justify-content:center}}
  .cdd-item-actor.selected .cdd-radio-actor{{border-color:var(--accent)}}
  .cdd-radio-dot-actor{{width:6px;height:6px;border-radius:50%;background:var(--accent);display:none}}
  .cdd-item-actor.selected .cdd-radio-dot-actor{{display:block}}

  /* ── Results grid ── */
  .res-grid{{display:grid;grid-template-columns:1fr;gap:16px;margin-bottom:24px}}
  @media(min-width:768px){{.res-grid{{grid-template-columns:repeat(3,1fr)}}}}
  .file-card{{background:var(--card);border-radius:6px;overflow:hidden;border:1px solid var(--border);cursor:pointer;transition:transform .22s cubic-bezier(.4,0,.2,1),box-shadow .22s,border-color .22s}}
  .file-card:hover{{transform:translateY(-4px);border-color:rgba(229,9,20,.4);box-shadow:0 14px 36px rgba(0,0,0,.6)}}
  .poster-box{{position:relative;padding-top:56.25%;background:var(--bg3);overflow:hidden}}
  .fc-poster{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity .3s ease}}
  .fc-poster.loaded{{opacity:1}}
  .poster-top{{position:absolute;top:0;left:0;right:0;display:flex;align-items:center;gap:5px;padding:8px;z-index:3}}
  .type-chip{{background:rgba(0,0,0,.72);backdrop-filter:blur(8px);color:#fff;border-radius:5px;padding:3px 8px;font-size:10px;font-weight:800;border:1px solid rgba(255,255,255,.14)}}
  .size-chip{{background:rgba(0,0,0,.60);backdrop-filter:blur(8px);color:#e0e0e0;border-radius:5px;padding:3px 8px;font-size:10px;font-weight:600;border:1px solid rgba(255,255,255,.08)}}
  .source-pill{{margin-left:auto;border-radius:20px;padding:3px 8px;font-size:9px;font-weight:700;display:inline-flex;align-items:center;gap:4px}}
  .source-pill.primary{{background:#14532d;color:#4ade80;border:1px solid #22c55e}}
  .source-pill.cloud{{background:#1e3a5f;color:#93c5fd;border:1px solid #60a5fa}}
  .source-pill.archive{{background:#7c2d12;color:#fdba74;border:1px solid #fb923c}}
  .source-dot{{width:5px;height:5px;border-radius:50%;background:currentColor}}
  .fc-body{{padding:10px 11px 12px}}
  .fc-name{{color:var(--text);font-size:12.5px;font-weight:600;line-height:1.45;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
  .fc-name:hover{{color:var(--accent)}}
  /* text-only mode */
  .fc-text-info{{display:flex;align-items:center;gap:6px;padding:8px 10px;background:var(--bg3);border-bottom:1px solid var(--border)}}
  .tc-type{{background:rgba(229,9,20,.15);color:var(--accent);border-radius:4px;padding:2px 7px;font-size:10px;font-weight:800}}
  .tc-size{{color:var(--muted);font-size:10px;font-weight:600}}
  .res-grid.mode-none .poster-box{{display:none}}

  /* ── Pagination & spinner ── */
  .pagination{{display:flex;align-items:center;justify-content:center;gap:12px;margin-top:20px}}
  .pg-btn{{background:var(--bg4);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:8px 18px;font-size:12px;font-weight:700;cursor:pointer;transition:background .15s}}
  .pg-btn:disabled{{opacity:.45;cursor:not-allowed}}
  .pg-btn:not(:disabled):hover{{background:var(--accent);color:#fff;border-color:var(--accent)}}
  .pg-info{{color:var(--muted);font-size:12px;font-weight:600}}
  .spin-wrap{{display:flex;flex-direction:column;align-items:center;gap:16px;padding:60px 20px;color:var(--muted);grid-column:1/-1}}
  .spinner{{width:36px;height:36px;border:3px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite}}
  @keyframes spin{{to{{transform:rotate(360deg)}}}}
  .empty{{text-align:center;padding:60px 20px;color:var(--muted);grid-column:1/-1}}

  /* ── Actor header ── */
  .actor-header-wrap{{display:flex;gap:25px;background:var(--card);border:1px solid var(--border);padding:25px;border-radius:12px;margin-bottom:35px;flex-direction:column;align-items:center;width:100%;box-sizing:border-box}}
  .avatar-box-master{{width:100%;max-width:340px;aspect-ratio:3/4;background:var(--bg3);border-radius:8px;overflow:hidden;border:1px solid var(--border);flex-shrink:0}}
  .avatar-img{{width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity .4s ease}}
  .avatar-img.av-loaded{{opacity:1}}
  @media(min-width:768px){{.actor-header-wrap{{flex-direction:row;align-items:stretch}}.avatar-box-master{{width:260px;height:350px;max-width:none;aspect-ratio:auto}}}}
</style>

<div class="main" style="padding:30px 20px 0;max-width:1100px;margin:0 auto">
  <div style="margin-bottom:15px"><a href="/actors" style="color:var(--muted);text-decoration:none;font-size:14px;font-weight:700">← Back to Catalog</a></div>

  <div class="actor-header-wrap">
    <div class="avatar-box-master">
      <img id="actorMasterAvatarImage" src="/api/actor/photo?id={actor_id}&v={photo_v}" class="avatar-img" onload="this.classList.add('av-loaded')">
    </div>
    <div style="flex:1;min-width:300px;display:flex;flex-direction:column;justify-content:center;width:100%">
      <h1 style="font-size:32px;font-weight:900;color:var(--text);margin-bottom:2px">{html.escape(actor_name)}</h1>
      {tags_html}{social_html}{admin_actions}
    </div>
  </div>

  <div class="actor-tab-bar">
    <button class="actor-tab active" onclick="switchActorTab(event,'tab-info')">ℹ️ Info</button>
    <button class="actor-tab" onclick="switchActorTab(event,'tab-video')">🎬 Video</button>
    <button class="actor-tab" onclick="switchActorTab(event,'tab-gallery')">🖼️ Gallery</button>
  </div>

  <div id="tab-info" class="actor-panel active">
    <div style="background:var(--card);border:1px solid var(--border);padding:25px;border-radius:8px;line-height:1.7;color:var(--text);font-size:15px;white-space:pre-line">{safe_bio}</div>
  </div>

  <div id="tab-video" class="actor-panel">
    <div class="search-zone-actor">
      <div class="search-row1-actor">
        <div class="search-wrap-actor">
          <input type="text" id="actor_movie_q" placeholder="Search inside actor movies..." class="search-input-actor">
        </div>
        <button onclick="resetActorSearchPage();triggerActorSearchAjax()" class="search-btn-actor">Search</button>
      </div>
      <div class="search-row2-actor">
        <div class="cdd-wrap-actor">
          <div class="cdd-btn-actor" id="cddColBtnActor" onclick="toggleActorCdd('col',event)"><span id="cddColLabelActor">📂 All Collections</span></div>
          <span class="cdd-arrow-actor">&#9660;</span>
          <div class="cdd-menu-actor" id="cddColMenuActor">
            <div class="cdd-item-actor selected" onclick="pickActorCdd('col','all','📂 All Collections',this,event)">📂 All Collections<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
            <div class="cdd-item-actor" onclick="pickActorCdd('col','primary','🟢 Primary',this,event)">🟢 Primary<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
            <div class="cdd-item-actor" onclick="pickActorCdd('col','cloud','🔵 Cloud',this,event)">🔵 Cloud<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
            <div class="cdd-item-actor" onclick="pickActorCdd('col','archive','🟠 Archive',this,event)">🟠 Archive<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
          </div>
        </div>
        <div class="cdd-wrap-actor">
          <div class="cdd-btn-actor" id="cddModeBtnActor" onclick="toggleActorCdd('mode',event)"><span id="cddModeLabelActor">🖼️ With Thumbnails</span></div>
          <span class="cdd-arrow-actor">&#9660;</span>
          <div class="cdd-menu-actor" id="cddModeMenuActor">
            <div class="cdd-item-actor selected" onclick="pickActorCdd('mode','tg','🖼️ With Thumbnails',this,event)">🖼️ With Thumbnails<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
            <div class="cdd-item-actor" onclick="pickActorCdd('mode','none','⚡ Text Only',this,event)">⚡ Text Only<span class="cdd-radio-actor"><span class="cdd-radio-dot-actor"></span></span></div>
          </div>
        </div>
      </div>
    </div>
    <div id="actor_video_results" class="res-grid"></div>
    <div class="pagination" id="actor_page_box" style="display:none">
      <button class="pg-btn" id="actor_pBtn" onclick="actorPagePrev()" disabled>Previous</button>
      <span class="pg-info" id="actor_pgInfo">Page 1</span>
      <button class="pg-btn" id="actor_nBtn" onclick="actorPageNext()">Next</button>
    </div>
  </div>

  <div id="tab-gallery" class="actor-panel">{gallery_html}</div>
</div>

<div id="actorLightboxModal" class="lightbox" onclick="closeLightbox()">
  <button class="lightbox-close" onclick="closeLightbox()">&times;</button>
  <img id="lightboxTargetImg" class="lightbox-img" src="" onclick="event.stopPropagation()">
</div>

<input type="hidden" id="actor_master_tags_payload" value="{tags_json}">
{edit_modal}

<script>
  var actCurPage=1, actOffset=0, actNextOffset="", actPrevOffsets=[0];
  var actCol="all", actMode="tg";
  var ACT_ID="{actor_id}";

  // ── Dropdown (unified handler) ──
  function closeActorCdds(){{
    ['cddColMenuActor','cddModeMenuActor'].forEach(function(id){{document.getElementById(id).style.display='none'}});
    ['cddColBtnActor','cddModeBtnActor'].forEach(function(id){{document.getElementById(id).classList.remove('open')}});
  }}
  function toggleActorCdd(which,e){{
    e&&e.stopPropagation();
    var menuId=which==='col'?'cddColMenuActor':'cddModeMenuActor';
    var btnId=which==='col'?'cddColBtnActor':'cddModeBtnActor';
    var menu=document.getElementById(menuId),btn=document.getElementById(btnId);
    var isOpen=menu.style.display==='block';
    closeActorCdds();
    if(!isOpen){{menu.style.display='block';btn.classList.add('open')}}
  }}
  function pickActorCdd(which,val,label,el,e){{
    e&&e.stopPropagation();
    var labelId=which==='col'?'cddColLabelActor':'cddModeLabelActor';
    var menuId=which==='col'?'cddColMenuActor':'cddModeMenuActor';
    if(which==='col') actCol=val; else actMode=val;
    document.getElementById(labelId).textContent=label;
    document.querySelectorAll('#'+menuId+' .cdd-item-actor').forEach(function(i){{i.classList.remove('selected')}});
    el.classList.add('selected');
    closeActorCdds();
    resetActorSearchPage();
    triggerActorSearchAjax();
  }}
  document.addEventListener('click',closeActorCdds);

  // ── Lightbox ──
  function openLightbox(src){{
    var lb=document.getElementById('actorLightboxModal');
    document.getElementById('lightboxTargetImg').src=src;
    lb.style.display='flex';
    requestAnimationFrame(function(){{lb.classList.add('open')}});
  }}
  function closeLightbox(){{
    var lb=document.getElementById('actorLightboxModal');
    lb.classList.remove('open');
    setTimeout(function(){{lb.style.display='none';document.getElementById('lightboxTargetImg').src=''}},250);
  }}
  document.addEventListener('keydown',function(e){{if(e.key==='Escape')closeLightbox()}});

  // ── Tabs ──
  function switchActorTab(evt,tabId){{
    document.querySelectorAll('.actor-panel').forEach(function(p){{p.classList.remove('active')}});
    document.querySelectorAll('.actor-tab').forEach(function(t){{t.classList.remove('active')}});
    document.getElementById(tabId).classList.add('active');
    evt.currentTarget.classList.add('active');
    if(tabId==='tab-video'&&document.getElementById('actor_video_results').innerHTML==='')triggerActorSearchAjax();
  }}

  // ── Edit modal ──
  function openActorEditModal(){{document.getElementById('actorEditModal').classList.add('open')}}
  function closeActorEditModal(){{document.getElementById('actorEditModal').classList.remove('open')}}
  function resetActorSearchPage(){{actCurPage=1;actOffset=0;actNextOffset="";actPrevOffsets=[0]}}

  // ── Search ──
  async function triggerActorSearchAjax(){{
    var q=document.getElementById('actor_movie_q').value.trim();
    var grid=document.getElementById('actor_video_results');
    grid.className='res-grid mode-'+actMode;
    grid.innerHTML='<div class="spin-wrap"><div class="spinner"></div><span>Loading...</span></div>';
    try{{
      var url='/api/actor/search?q='+encodeURIComponent(q)+'&offset='+actOffset+'&col='+actCol+'&id='+ACT_ID;
      var d=await(await fetch(url)).json();
      if(!d.results||!d.results.length){{
        grid.innerHTML='<div class="empty"><p>No results found.</p></div>';
        document.getElementById('actor_page_box').style.display='none';
        return;
      }}
      var h='';
      d.results.forEach(function(f){{
        var sc=(f.source||'primary').toLowerCase();
        var poster=actMode!=='none'
          ?'<div class="poster-box"><img src="'+f.tg_thumb+'" class="fc-poster" onload="this.classList.add(\'loaded\')" loading="lazy"><div class="poster-top"><span class="type-chip">'+f.type+'</span><span class="size-chip">'+f.size+'</span><span class="source-pill '+sc+'"><span class="source-dot"></span>'+sc.toUpperCase()+'</span></div></div>'
          :'<div class="fc-text-info"><span class="tc-type">'+f.type+'</span><span class="tc-size">'+f.size+'</span><span class="source-pill '+sc+'" style="margin-left:auto"><span class="source-dot"></span>'+sc.toUpperCase()+'</span></div>';
        h+='<div class="file-card" onclick="window.open(\''+f.watch+'\',\'_blank\')">'+poster+'<div class="fc-body"><div class="fc-name">'+f.name+'</div></div></div>';
      }});
      grid.innerHTML=h;
      actNextOffset=d.next_offset||"";
      document.getElementById('actor_page_box').style.display='flex';
      document.getElementById('actor_pBtn').disabled=(actCurPage<=1);
      document.getElementById('actor_nBtn').disabled=!actNextOffset;
      document.getElementById('actor_pgInfo').textContent='Page '+actCurPage;
    }}catch(e){{grid.innerHTML='<div class="empty"><p>Load error. Try again.</p></div>'}}
  }}

  // ── Pagination — ✅ FIX: offset stack ──
  function actorPageNext(){{
    if(!actNextOffset)return;
    actPrevOffsets.push(actOffset);
    actOffset=actNextOffset;
    actCurPage++;
    triggerActorSearchAjax();
    window.scrollTo(0,350);
  }}
  function actorPagePrev(){{
    if(actCurPage<=1)return;
    actOffset=actPrevOffsets.pop()||0;
    actCurPage--;
    triggerActorSearchAjax();
    window.scrollTo(0,350);
  }}

  // ── Avatar update ──
  async function updateActorAvatar(actorId){{
    var fi=document.getElementById('avatarUpdateInput');
    if(!fi.files||!fi.files[0])return;
    var fd=new FormData();
    fd.append('actor_id',actorId);
    fd.append('photo',fi.files[0]);
    try{{
      var d=await(await fetch('/api/actor/update_avatar',{{method:'POST',body:fd}})).json();
      if(d.success){{
        var newV=d.photo_updated_at||Date.now();
        var img=document.getElementById('actorMasterAvatarImage');
        img.classList.remove('av-loaded');
        img.src='/api/actor/photo?id='+actorId+'&v='+newV;
        img.onload=function(){{img.classList.add('av-loaded')}};
        alert("Profile photo updated successfully!");
      }}else{{alert(d.error||"Upload failed!")}}
    }}catch(e){{alert("Network error!")}}
  }}

  // ── Gallery delete ──
  async function deleteGalleryImage(actorId,idx,e){{
    e&&e.stopPropagation();
    if(!confirm("Delete this photo permanently?"))return;
    try{{
      var d=await(await fetch('/api/actor/gallery_delete',{{method:'POST',body:JSON.stringify({{actor_id:actorId,index:idx}}),headers:{{'Content-Type':'application/json'}}}})).json();
      if(d.success){{window.location.reload()}}else{{alert(d.error||"Delete failed!")}}
    }}catch(e){{alert("Network error!")}}
  }}

  // ── Profile delete ──
  async function deleteActorProfile(id){{
    if(!confirm("Permanently delete this actor profile?"))return;
    try{{
      var d=await(await fetch('/api/actor/delete?id='+id,{{method:'POST'}})).json();
      if(d.success){{window.location.href='/actors'}}else{{alert(d.error||"Delete failed!")}}
    }}catch(e){{alert("Network error!")}}
  }}

  document.getElementById('actor_movie_q').addEventListener('keydown',function(e){{if(e.key==='Enter'){{resetActorSearchPage();triggerActorSearchAjax()}}}});
</script>'''

    return build_page(f"{actor_name} - Profile", page, "", "actors", role)


# ─────────────────────────────────────────────────────────
# ⚙️ AJAX SEARCH API
# ─────────────────────────────────────────────────────────
@actor_routes.get('/api/actor/search')
async def api_actor_search_handler(req):
    role, _ = await get_auth(req)
    if not role: return web.json_response({"error": "Unauthorized"}, status=403)

    actor_id  = req.query.get("id")
    q_custom  = req.query.get("q", "").strip()
    col       = req.query.get("col", "all").lower()
    try: off = max(0, int(req.query.get("offset", 0)))
    except: off = 0

    if not actor_id: return web.json_response({"results": [], "next_offset": ""})

    actor = await actors.find_one({"_id": ObjectId(actor_id)})
    if not actor: return web.json_response({"results": [], "next_offset": ""})

    tags_list = actor.get("tags", [])
    if q_custom:
        search_query, final_tags = q_custom, []
    elif tags_list:
        search_query, final_tags = tags_list[0], tags_list
    else:
        return web.json_response({"results": [], "next_offset": ""})

    all_m, next_offset = await get_actor_search_results(
        search_query, final_tags, max_results=21, offset=off, collection_type=col
    )

    results = []
    for d in all_m:
        fid        = d.get("file_ref") or d.get("_id")
        db_id      = d.get("_id")
        source_col = d.get("source_col", "primary")
        raw_thumb  = d.get("thumb_url", "")
        v_salt     = raw_thumb[-8:] if (raw_thumb and raw_thumb.startswith("TG_ID:")) else "0"
        results.append({
            "file_id": db_id,
            "name":    d.get("file_name", "Unknown File"),
            "size":    get_size(d.get("file_size", 0)),
            "type":    d.get("file_type", "document").upper(),
            "source":  source_col.capitalize(),
            "tg_thumb":f"/api/thumb?file_id={db_id}&col={source_col}&v={v_salt}",
            "watch":   f"/setup_stream?file_id={fid}&mode=watch"
        })

    return web.json_response({"results": results, "next_offset": next_offset})


# ─────────────────────────────────────────────────────────
# ⚙️ UPDATE PROFILE
# ─────────────────────────────────────────────────────────
@actor_routes.post('/api/actor/update_profile')
async def api_actor_update_profile(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403)

    d        = await req.post()
    actor_id = d.get('actor_id')
    name     = d.get('name', '').strip()
    bio      = d.get('bio', '').strip()
    if not actor_id or not name or not bio:
        return web.HTTPFound('/actors?err=Missing required fields')

    tags_list = [t.strip() for t in d.get('tags','').split(",") if t.strip()]
    await actors.update_one({"_id": ObjectId(actor_id)}, {"$set": {
        "name": name, "bio": bio, "tags": tags_list,
        "social_links": {
            "instagram": d.get('insta','').strip(),
            "youtube":   d.get('yt','').strip(),
            "twitter":   d.get('twitter','').strip()
        }
    }})
    return web.HTTPFound(f'/actor/{actor_id}?msg=Profile updated successfully!')


# ─────────────────────────────────────────────────────────
# ⚙️ UPDATE AVATAR
# ─────────────────────────────────────────────────────────
@actor_routes.post('/api/actor/update_avatar')
async def api_actor_update_avatar(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403)

    try:
        data       = await req.post()
        actor_id   = data.get("actor_id")
        photo_part = data.get("photo")
        if not actor_id or not photo_part:
            return web.json_response({"success": False, "error": "Invalid data"})

        with io.BytesIO(photo_part.file.read()) as buf:
            buf.name = f"avatar_{actor_id}.jpg"
            msg = await temp.BOT.send_photo(chat_id=BIN_CHANNEL, photo=buf)

        if not msg or not msg.photo:
            return web.json_response({"success": False, "error": "Telegram upload failed"})

        # ✅ FIX: Pyrogram Photo is a list
        tg_photo_id = msg.photo[-1].file_id
        new_ts = int(time.time())
        await actors.update_one({"_id": ObjectId(actor_id)},
            {"$set": {"photo_url": f"TG_ID:{tg_photo_id}", "photo_updated_at": new_ts}})
        return web.json_response({"success": True, "photo_updated_at": new_ts})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)})


# ─────────────────────────────────────────────────────────
# ⚙️ GALLERY UPLOAD
# ─────────────────────────────────────────────────────────
@actor_routes.post('/api/actor/gallery_upload')
async def api_actor_gallery_upload(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403)

    try:
        reader = await req.multipart()
        actor_id, image_bytes = None, None
        while True:
            part = await reader.next()
            if part is None: break
            if part.name == 'actor_id':   actor_id    = (await part.read()).decode().strip()
            elif part.name == 'gallery_img': image_bytes = await part.read()

        if not actor_id or not image_bytes:
            return web.HTTPFound('/actors?err=Upload data missing')

        with io.BytesIO(image_bytes) as buf:
            buf.name = f"gallery_{actor_id}.jpg"
            msg = await temp.BOT.send_photo(chat_id=BIN_CHANNEL, photo=buf)

        if not msg or not msg.photo:
            return web.HTTPFound(f'/actor/{actor_id}?err=Telegram upload failed')

        # ✅ FIX: Pyrogram Photo is a list
        tg_photo_id = msg.photo[-1].file_id
        await actors.update_one({"_id": ObjectId(actor_id)},
            {"$push": {"gallery": f"TG_ID:{tg_photo_id}"}})
        return web.HTTPFound(f'/actor/{actor_id}?msg=Image added to gallery!')
    except Exception as e:
        return web.HTTPFound(f'/actors?err=Error: {str(e)}')


# ─────────────────────────────────────────────────────────
# ⚙️ GALLERY DELETE — ✅ FIX: $pull atomic (no race condition)
# ─────────────────────────────────────────────────────────
@actor_routes.post('/api/actor/gallery_delete')
async def api_actor_gallery_delete(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403)

    try:
        body     = await req.json()
        actor_id = body.get("actor_id")
        idx      = body.get("index")
        if actor_id is None or idx is None or not isinstance(idx, int):
            return web.json_response({"success": False, "error": "Invalid parameters"})

        actor = await actors.find_one({"_id": ObjectId(actor_id)}, {"gallery": 1})
        if not actor:
            return web.json_response({"success": False, "error": "Actor not found"})

        gallery = actor.get("gallery", [])
        if idx < 0 or idx >= len(gallery):
            return web.json_response({"success": False, "error": "Index out of bounds"})

        target = gallery[idx]
        # ✅ atomic $pull by value — race-condition proof
        await actors.update_one({"_id": ObjectId(actor_id)},
            {"$pull": {"gallery": target}})
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)})


# ─────────────────────────────────────────────────────────
# ⚙️ DELETE ACTOR
# ─────────────────────────────────────────────────────────
@actor_routes.post('/api/actor/delete')
async def api_actor_delete(req):
    role, _ = await get_auth(req)
    if role != 'admin': return web.json_response({"error": "Unauthorized"}, status=403)

    actor_id = req.query.get("id")
    if not actor_id: return web.json_response({"error": "Missing ID"}, status=400)

    try:
        await actors.delete_one({"_id": ObjectId(actor_id)})
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
