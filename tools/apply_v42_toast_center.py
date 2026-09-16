from pathlib import Path

css_path = Path('styles.css')
index_path = Path('index.html')
css = css_path.read_text(encoding='utf-8')
marker = '/* v42 centered global toast */'
patch = r'''

/* v42 centered global toast */
.toast{
  position:fixed!important;
  z-index:9999!important;
  top:50%!important;
  left:50%!important;
  right:auto!important;
  bottom:auto!important;
  width:max-content!important;
  min-width:min(320px,calc(100vw - 32px))!important;
  max-width:min(440px,calc(100vw - 32px))!important;
  padding:15px 22px!important;
  border:1px solid #fff!important;
  border-radius:16px!important;
  background:#111318!important;
  color:#fff!important;
  text-align:center!important;
  line-height:1.7!important;
  box-shadow:0 18px 55px rgba(0,0,0,.55)!important;
  opacity:0;
  transform:translate(-50%,-50%) scale(.96)!important;
  pointer-events:none;
  transition:opacity .22s ease,transform .22s ease!important;
}
.toast.show{
  opacity:1!important;
  transform:translate(-50%,-50%) scale(1)!important;
}
.toast.error{
  background:#111318!important;
  color:#fff!important;
  border-color:#fff!important;
}
@media(max-width:760px){
  .toast{
    min-width:min(290px,calc(100vw - 28px))!important;
    max-width:calc(100vw - 28px)!important;
    padding:14px 18px!important;
    font-size:.95rem!important;
  }
}
'''
if marker not in css:
    css += patch
css_path.write_text(css, encoding='utf-8')

html = index_path.read_text(encoding='utf-8')
import re
html = re.sub(r'styles\.css\?v=\d+', 'styles.css?v=42', html)
index_path.write_text(html, encoding='utf-8')
