from aiohttp import web
from web.web_assets import build_page, get_auth, form_wrapper, render_collection_dropdown, render_mode_dropdown
from database.users_chats_db import db as user_db
from utils import temp

dashboard_routes = web.RouteTableDef()

# ─────────────────────────────────────────────────────────
# 🌐 MAIN HOMEPAGE: DASHBOARD
# ─────────────────────────────────────────────────────────
@dashboard_routes.get('/dashboard')
async def dash(req):
    role, tg_id = await get_auth(req)
    if not role:
        return web.HTTPFound('/login')
    
    if role == 'user':
        mp = await user_db.get_plan(tg_id)
        if not mp.get("premium"):
            return web.HTTPFound('/premium_expired')

    # ✅ 100% DRY: कोई CSS/JS रिपीट नहीं। यह सीधे web_assets.py के ग्लोबल इंजन का उपयोग करेगा।
    body = f'''
    <div class="search-zone">
        <div class="search-row1">
            <div class="search-wrap">
                <input class="search-input" id="q" placeholder="Titles, people, genres…">
            </div>
            <button class="search-btn" id="searchBtn" onclick="doSearch(0);triggerRipple(this)">Search</button>
        </div>
        <div class="search-row2">
            {render_collection_dropdown()}
            {render_mode_dropdown()}
        </div>
    </div>
    <div class="main" style="padding-top:4px;">
        <div class="results-info" id="resInfo" style="padding:0 12px 8px; display:none;">
            <span class="results-count" id="resCount"></span>
        </div>
        <div style="padding:0 2px">
            <div id="results" class="res-grid">
                <div class="empty">
                    <div class="empty-icon">&#8981;</div>
                    <p>Find your favorite movies and TV shows.</p>
                </div>
            </div>
            <div class="pagination" id="pageBox" style="display:none;">
                <button class="pg-btn" id="pBtn" onclick="prev()" disabled>Previous</button>
                <span class="pg-info" id="pgInfo">Page 1</span>
                <button class="pg-btn" id="nBtn" onclick="next()">Next</button>
            </div>
        </div>
    </div>
    '''
    
    return build_page("Home - Fast Finder", body, "", "dash", role)

# ─────────────────────────────────────────────────────────
# 🚪 LOGOUT ROUTE
# ─────────────────────────────────────────────────────────
@dashboard_routes.get('/logout')
async def logout(req):
    s_user = req.cookies.get('user_session')
    if s_user and hasattr(temp, 'USER_SESSIONS') and s_user in temp.USER_SESSIONS:
        del temp.USER_SESSIONS[s_user]
    
    res = web.HTTPFound('/login')
    res.del_cookie('user_session')
    return res

# ─────────────────────────────────────────────────────────
# ⏳ PREMIUM EXPIRED ROUTE
# ─────────────────────────────────────────────────────────
@dashboard_routes.get('/premium_expired')
async def premium_expired(req):
    role, tg_id = await get_auth(req)
    if not role:
        return web.HTTPFound('/login')
        
    content = (
        '<div style="text-align:center;">'
        '<div style="font-size:50px;margin-bottom:15px;">&#9203;</div>'
        '<p style="color:var(--muted);margin-bottom:30px;">Your access to Fast Finder Web has expired. '
        'Please renew your plan via our Telegram Bot.</p>'
        '<div class="scard red" style="text-align:left;margin-bottom:25px;padding:15px;">'
        '<div class="scard-label">How to Renew?</div>'
        '<div class="scard-sub" style="color:var(--text)">1. Go to Telegram Bot</div>'
        '<div class="scard-sub" style="color:var(--text)">2. Use command <b>/plan</b></div>'
        '<div class="scard-sub" style="color:var(--text)">3. Pay & Activate instantly</div>'
        '</div>'
        f'<a href="https://t.me/{temp.U_NAME}" class="submit-btn" style="text-decoration:none;display:block;">Open Telegram Bot</a>'
        '<a href="/logout" style="display:block;margin-top:20px;color:var(--muted);text-decoration:none;">Sign Out</a>'
        '</div>'
    )
    return build_page("Premium Expired", form_wrapper("Premium Expired", content), "login-bg")

# ─────────────────────────────────────────────────────────
# 🩺 KOYEB HEALTH CHECK (MICRO-VM PROTECTOR)
# ─────────────────────────────────────────────────────────
@dashboard_routes.get('/health')
async def koyeb_health_check(req):
    # Koyeb को सर्वर Alive दिखाने के लिए 200 OK रिस्पॉन्स देना जरूरी है 
    # वरना Koyeb पोड को स्लीप मोड में डाल देता है।
    return web.json_response({"status": "alive", "platform": "koyeb"})
