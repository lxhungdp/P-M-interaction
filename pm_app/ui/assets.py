"""Streamlit CSS/JS injection and session defaults."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as stc

from pm_app.config import SESSION_DEFAULTS

_CSS = """
<style>
div[data-testid="stExpander"] summary p {font-size:12px!important;font-weight:700;margin:0;}
div[data-testid="stExpander"] details {border:1px solid #dce0e8!important;border-radius:4px!important;margin-bottom:4px!important;}
label[data-testid="stWidgetLabel"]>p {font-size:13px!important;margin-bottom:1px!important;}
div[data-testid="stNumberInput"] input {padding:2px 6px!important;font-size:14px!important;}
div[data-testid="stSelectbox"]>div>div {font-size:14px!important;}
div[data-testid="stCaptionContainer"] p {font-size:13px!important;}
div[data-testid="stDataEditor"] {font-size:12px!important;}
.pm-main-col0 {
    border-right: 3px solid #90a4ae !important;
    padding-right: 10px !important;
}
div[data-testid="stCode"] code {font-size:0.82rem!important;line-height:1.55!important;}
.pm-verify-lbl {font-size:0.82rem!important;line-height:1.55!important;}
div[data-testid="stNumberInput"] button {display:none!important;width:0!important;height:0!important;padding:0!important;min-height:0!important;}
div[data-testid="stAlert"] p, div[data-testid="stAlert"] li {font-size:16px!important;}
div[data-testid="stMarkdownContainer"] p {font-size:13px!important;}
.pm-verify-msg {font-size:16px!important;line-height:1.5!important;}
iframe[height="1"]{display:none!important;margin:0!important;padding:0!important;}
</style>
"""

_JS = """
<script>
document.addEventListener('keydown',function(e){
  if((e.ctrlKey||e.metaKey)&&e.key==='s'){
    e.preventDefault();
    var pb=window.parent.document.querySelectorAll('[data-testid="baseButton-primary"]');
    if(pb.length>0){pb[pb.length-1].click();return;}
    var btns=window.parent.document.querySelectorAll('button');
    for(var b of btns){if(b.innerText&&b.innerText.includes('계산')){b.click();break;}}
  }
},true);

var _rz={w0:null,w1:null,drag:false,sx:0,sw0:0,sw1:0,bound:false};
function getMainBlock(){
  var doc=window.parent.document;
  var blocks=doc.querySelectorAll('[data-testid="stHorizontalBlock"]');
  for(var i=0;i<blocks.length;i++){
    if(blocks[i].children.length>=2) return blocks[i];
  }
  return null;
}
function applyRz(block){
  if(!_rz.w0||!block) return;
  var c0=block.children[0], c1=block.children[block.children.length-1];
  c0.style.flex='0 0 '+_rz.w0+'px';c0.style.minWidth=_rz.w0+'px';c0.style.maxWidth=_rz.w0+'px';
  c1.style.flex='0 0 '+_rz.w1+'px';c1.style.minWidth=_rz.w1+'px';c1.style.maxWidth=_rz.w1+'px';
}
function initDrag(){
  if(_rz.bound) return true;
  var doc=window.parent.document;
  var block=getMainBlock(); if(!block) return false;
  var overlay=doc.createElement('div');
  overlay.id='_pm_drag_overlay';
  overlay.style.cssText='position:absolute;top:0;bottom:0;right:-6px;width:12px;'
    +'cursor:col-resize;z-index:9999;background:transparent;';
  var c0=block.children[0];
  c0.classList.add('pm-main-col0');
  if(getComputedStyle(c0).position==='static') c0.style.position='relative';
  c0.appendChild(overlay);
  _rz.bound=true;
  overlay.addEventListener('mousedown',function(e){
    var b=getMainBlock(); if(!b) return;
    _rz.drag=true; _rz.sx=e.clientX;
    _rz.sw0=b.children[0].getBoundingClientRect().width;
    _rz.sw1=b.children[b.children.length-1].getBoundingClientRect().width;
    doc.body.style.cursor='col-resize'; doc.body.style.userSelect='none';
    e.preventDefault();
  });
  doc.addEventListener('mousemove',function(e){
    if(!_rz.drag) return;
    var b=getMainBlock(); if(!b) return;
    var dx=e.clientX-_rz.sx, tot=_rz.sw0+_rz.sw1;
    var w0=Math.max(180,Math.min(tot-250,_rz.sw0+dx)), w1=tot-w0;
    _rz.w0=w0; _rz.w1=w1;
    b.children[0].style.flex='0 0 '+w0+'px';
    b.children[0].style.minWidth=w0+'px';b.children[0].style.maxWidth=w0+'px';
    var last=b.children[b.children.length-1];
    last.style.flex='0 0 '+w1+'px';last.style.minWidth=w1+'px';last.style.maxWidth=w1+'px';
  });
  doc.addEventListener('mouseup',function(){
    if(!_rz.drag) return;
    _rz.drag=false; doc.body.style.cursor=''; doc.body.style.userSelect='';
  });
  new MutationObserver(function(){
    var b=getMainBlock(); if(b) applyRz(b);
  }).observe(doc.body,{childList:true,subtree:false});
  return true;
}
var _bt=0;
(function retry(){if(_bt++>100)return;try{if(!initDrag())setTimeout(retry,300);}catch(e){setTimeout(retry,300);}})();
</script>
"""


def init_session_defaults() -> None:
    for key, val in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val


def inject_assets() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    stc.html(_JS, height=1)
