from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
app_path = ROOT / "app.js"
css_path = ROOT / "styles.css"
html_path = ROOT / "index.html"

app = app_path.read_text(encoding="utf-8")
css = css_path.read_text(encoding="utf-8")
html = html_path.read_text(encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)

# 1) Fresh authentication on every page load. Keep the authenticated session only
# for the current page lifetime; a refresh/new visit must go through password + MFA.
app = replace_once(
    app,
    'let session = JSON.parse(localStorage.getItem("rm_admin_session") || "null");',
    'let session = null; localStorage.removeItem("rm_admin_session");',
    "fresh-login session bootstrap",
)

# 2) Clean stale/unverified TOTP factors before creating a new one. This fixes
# Supabase's duplicate friendly-name error after an interrupted enrollment.
old_mfa = '''async function startMfa(){const button=$("mfa-toggle");button.disabled=true;try{const data=await factorRequest("",{factor_type:"totp",friendly_name:"RoutineMan Admin"});enrollFactor=data;$("mfa-qr").src=data.totp.qr_code;$("mfa-secret").textContent=data.totp.secret;$("mfa-enroll-box").classList.remove("hidden");toast("QR امنیتی آماده شد")}catch(e){toast(e.message,true)}finally{button.disabled=false}}'''
new_mfa = '''async function startMfa(){const button=$("mfa-toggle");button.disabled=true;try{await refreshUser();const factors=(session?.user?.factors||[]).filter(x=>x.factor_type==="totp");const verified=factors.find(x=>x.status==="verified");if(verified){renderSecurity();toast("ورود دومرحله‌ای از قبل فعال است");return}for(const factor of factors.filter(x=>x.status!=="verified")){try{await factorRequest(`/${factor.id}`,null,"DELETE")}catch{}}await refreshUser();const data=await factorRequest("",{factor_type:"totp",friendly_name:"RoutineMan Admin"});enrollFactor=data;$("mfa-qr").src=data.totp.qr_code;$("mfa-secret").textContent=data.totp.secret;$("mfa-enroll-code").value="";$("mfa-enroll-box").classList.remove("hidden");toast("QR امنیتی آماده شد")}catch(e){toast(e.message,true)}finally{button.disabled=false}}'''
app = replace_once(app, old_mfa, new_mfa, "MFA enrollment")

# 3) Show only one card for the same physical/browser device. Prefer the current
# auth session; otherwise keep the most recently active session.
old_sessions = '''async function loadSessions(){const box=$("sessions-list");box.innerHTML='<div class="empty">درحال دریافت نشست‌ها…</div>';try{await registerCurrentSession();const data=await api("list_admin_sessions"),current=jwtClaims().session_id,rows=data.sessions||[];$("session-count").textContent=`${fa.format(rows.length)} نشست`;box.innerHTML=rows.map(x=>`<article class="session-card${x.session_id===current?" current":""}"><div class="session-main"><strong>${escapeHtml(x.device_model||"دستگاه ناشناس")}</strong><span>${escapeHtml([x.platform,x.browser].filter(Boolean).join(" — ")||"اطلاعات دستگاه ثبت نشده")}</span><small>آخرین فعالیت: ${dateFa(x.last_seen_at||x.created_at)}${x.session_id===current?" — همین دستگاه":""}</small></div><button class="btn session-logout" data-session-id="${x.session_id}" data-current="${x.session_id===current}">خروج این نشست</button></article>`).join("")||'<div class="empty">نشست فعالی پیدا نشد.</div>';box.querySelectorAll("[data-session-id]").forEach(b=>b.onclick=()=>revokeSession(b.dataset.sessionId,b.dataset.current==="true"))}catch(e){box.innerHTML='<div class="empty">دریافت نشست‌ها انجام نشد.</div>';toast(e.message,true)}}'''
new_sessions = '''function uniqueDeviceSessions(rows,current){const byDevice=new Map();for(const x of rows||[]){const key=[x.device_model||"",x.platform||"",x.browser||""].map(v=>String(v).trim().toLowerCase()).join("|")||x.session_id;const prev=byDevice.get(key),isCurrent=x.session_id===current,prevCurrent=prev?.session_id===current,t=Date.parse(x.last_seen_at||x.created_at||0)||0,pt=Date.parse(prev?.last_seen_at||prev?.created_at||0)||0;if(!prev||isCurrent||(!prevCurrent&&t>pt))byDevice.set(key,x)}return [...byDevice.values()].sort((a,b)=>(Date.parse(b.last_seen_at||b.created_at||0)||0)-(Date.parse(a.last_seen_at||a.created_at||0)||0))}\nasync function loadSessions(){const box=$("sessions-list");box.innerHTML='<div class="empty">درحال دریافت نشست‌ها…</div>';try{await registerCurrentSession();const data=await api("list_admin_sessions"),current=jwtClaims().session_id,rows=uniqueDeviceSessions(data.sessions||[],current);$("session-count").textContent=`${fa.format(rows.length)} نشست`;box.innerHTML=rows.map(x=>`<article class="session-card${x.session_id===current?" current":""}"><div class="session-main"><strong>${escapeHtml(x.device_model||"دستگاه ناشناس")}</strong><span>${escapeHtml([x.platform,x.browser].filter(Boolean).join(" — ")||"اطلاعات دستگاه ثبت نشده")}</span><small>آخرین فعالیت: ${dateFa(x.last_seen_at||x.created_at)}${x.session_id===current?" — همین دستگاه":""}</small></div><button class="btn session-logout" data-session-id="${x.session_id}" data-current="${x.session_id===current}">خروج این نشست</button></article>`).join("")||'<div class="empty">نشست فعالی پیدا نشد.</div>';box.querySelectorAll("[data-session-id]").forEach(b=>b.onclick=()=>revokeSession(b.dataset.sessionId,b.dataset.current==="true"))}catch(e){box.innerHTML='<div class="empty">دریافت نشست‌ها انجام نشد.</div>';toast(e.message,true)}}'''
app = replace_once(app, old_sessions, new_sessions, "session de-duplication")

# 4) Individual audit deletion: send both commonly-used key names so the Edge
# Function can consume either contract; reject missing ids instead of a no-op.
old_delete = '''async function deleteAuditItem(id){if(!confirm("این مورد از تاریخچه حذف شود؟"))return;try{await api("delete_audit_item",{audit_id:id});toast("مورد انتخاب‌شده حذف شد");await loadAudit()}catch(e){toast(e.message,true)}}'''
new_delete = '''async function deleteAuditItem(id){if(!id){toast("شناسه این مورد از تاریخچه معتبر نیست",true);return}if(!confirm("این مورد از تاریخچه حذف شود؟"))return;try{await api("delete_audit_item",{audit_id:id,id:String(id)});toast("مورد انتخاب‌شده حذف شد");await loadAudit()}catch(e){toast(e.message,true)}}'''
app = replace_once(app, old_delete, new_delete, "single audit delete")

# Black secret/code box requested in Settings > 2FA.
marker = "/* RoutineMan Admin v40 security fixes */"
if marker not in css:
    css += f'''\n\n{marker}\n#mfa-secret.mfa-secret {{\n  display: block;\n  width: 100%;\n  box-sizing: border-box;\n  margin: 14px 0;\n  padding: 14px 16px;\n  background: #050608 !important;\n  color: #ffffff !important;\n  border: 1px solid #343640 !important;\n  border-radius: 14px;\n  direction: ltr;\n  text-align: center;\n  overflow-wrap: anywhere;\n  word-break: break-all;\n}}\n'''

# Cache-bust GitHub Pages assets.
html = html.replace("./styles.css?v=39", "./styles.css?v=40")
html = html.replace("./app.js?v=39", "./app.js?v=40")

app_path.write_text(app, encoding="utf-8")
css_path.write_text(css, encoding="utf-8")
html_path.write_text(html, encoding="utf-8")

# Static assertions used by CI before committing.
checks = {
    "fresh login": 'let session = null; localStorage.removeItem("rm_admin_session");' in app,
    "MFA cleanup": 'factors.filter(x=>x.status!=="verified")' in app,
    "session dedupe": 'function uniqueDeviceSessions' in app,
    "single audit id compatibility": 'audit_id:id,id:String(id)' in app,
    "black MFA secret": '#mfa-secret.mfa-secret' in css and 'background: #050608' in css,
    "cache v40": '?v=40' in html,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise RuntimeError("failed checks: " + ", ".join(failed))
print("v40 patch checks PASS")
