from pathlib import Path

app_path = Path('app.js')
index_path = Path('index.html')
app = app_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')

old = '''async function deleteAuditItem(id){if(!id){toast("شناسه این مورد از تاریخچه معتبر نیست",true);return}if(!confirm("این مورد از تاریخچه حذف شود؟"))return;try{await api("delete_audit_item",{audit_id:id,id:String(id)});toast("مورد انتخاب‌شده حذف شد");await loadAudit()}catch(e){toast(e.message,true)}}'''
new = '''async function deleteAuditItem(id){if(!id){toast("شناسه این مورد از تاریخچه معتبر نیست",true);return}if(!confirm("این مورد از تاریخچه حذف شود؟"))return;const auditId=Number(id);if(!Number.isInteger(auditId)||auditId<=0){toast("شناسه این مورد از تاریخچه معتبر نیست",true);return}try{const res=await fetch(`${SUPABASE_URL}/rest/v1/rpc/routine_delete_audit_item`,{method:"POST",headers:{apikey:API_KEY,authorization:`Bearer ${session.access_token}`,"content-type":"application/json"},body:JSON.stringify({p_audit_id:auditId})});let data=null;try{data=await res.json()}catch{}if(!res.ok){const msg=data?.message||data?.hint||data?.details||data?.error||"حذف تکی تاریخچه انجام نشد";throw new Error(msg)}if(data!==true){throw new Error("این مورد در تاریخچه پیدا نشد یا قبلاً حذف شده است")}toast("مورد انتخاب‌شده حذف شد");await loadAudit()}catch(e){toast(e.message||"حذف تکی تاریخچه انجام نشد",true)}}'''
if old not in app:
    raise SystemExit('deleteAuditItem source pattern not found')
app = app.replace(old, new, 1)

index = index.replace('./styles.css?v=40', './styles.css?v=41')
index = index.replace('./app.js?v=40', './app.js?v=41')

app_path.write_text(app, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')

# Static assertions
assert 'routine_delete_audit_item' in app
assert 'p_audit_id:auditId' in app
assert './app.js?v=41' in index
assert './styles.css?v=41' in index
print('v41 patch applied')
