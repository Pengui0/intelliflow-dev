"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IntelliFlow — Traffic Operations Centre</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Fraunces:opsz,wght@9..144,700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/babylonjs/6.26.0/babylon.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/babylonjs-materials/6.26.0/babylonjs.materials.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/babylonjs-procedural-textures/6.26.0/babylonjs.proceduralTextures.min.js"></script>
<style>
:root{
  --bg:#111318;--bg-panel:#181c23;--bg-card:#1e2330;--bg-raised:#242938;--bg-input:#141720;
  --border:rgba(255,255,255,0.07);--border-mid:rgba(255,255,255,0.12);--border-str:rgba(255,255,255,0.18);
  --sand:#d4a84b;--sand-lt:#e8c068;--sand-dim:rgba(212,168,75,0.12);
  --green:#3ecf8e;--green-dim:rgba(62,207,142,0.12);
  --red:#e5534b;--red-dim:rgba(229,83,75,0.12);
  --blue:#58a6ff;--blue-dim:rgba(88,166,255,0.10);
  --purple:#a78bfa;--purple-dim:rgba(167,139,250,0.12);
  --text:#cdd5e0;--text-dim:#6e7b8e;--text-faint:#3a4252;
  --shadow:0 2px 12px rgba(0,0,0,0.4);--shadow-lg:0 8px 32px rgba(0,0,0,0.5);
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html{font-size:13px;}
body{font-family:'Sora',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden;}
.shell{max-width:1700px;margin:0 auto;padding:16px 20px 32px;}
.header{display:flex;align-items:center;justify-content:space-between;padding-bottom:14px;margin-bottom:16px;border-bottom:1px solid var(--border);}
.brand{display:flex;align-items:center;gap:12px;}
.brand-mark{width:38px;height:38px;border-radius:9px;background:linear-gradient(135deg,#2a3040,#1e2330);border:1px solid var(--border-mid);display:flex;align-items:center;justify-content:center;box-shadow:var(--shadow);flex-shrink:0;}
.brand-mark svg{width:20px;height:20px;}
.brand-name{font-family:'Fraunces',serif;font-size:19px;font-weight:700;color:#e8e8ea;letter-spacing:-0.01em;line-height:1;}
.brand-sub{font-size:10px;color:var(--text-dim);margin-top:2px;letter-spacing:0.04em;}
.header-right{display:flex;align-items:center;gap:20px;}
.live-pill{display:flex;align-items:center;gap:7px;background:var(--green-dim);border:1px solid rgba(62,207,142,0.2);border-radius:20px;padding:4px 11px 4px 8px;font-size:11px;font-weight:500;color:var(--green);}
.live-dot{width:6px;height:6px;border-radius:50%;background:var(--green);animation:breathe 2s ease-in-out infinite;}
@keyframes breathe{0%,100%{opacity:1;transform:scale(1);}50%{opacity:0.3;transform:scale(0.6);}}
.clock{text-align:right;}
.clock-t{font-family:'JetBrains Mono',monospace;font-size:17px;font-weight:500;color:#e8e8ea;letter-spacing:0.04em;line-height:1;}
.clock-d{font-size:10px;color:var(--text-dim);margin-top:2px;}
.ctrl-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:var(--bg-panel);border:1px solid var(--border);border-radius:10px;padding:10px 14px;margin-bottom:16px;box-shadow:var(--shadow);}
.ctrl-lbl{font-size:10px;font-weight:500;color:var(--text-dim);letter-spacing:0.05em;white-space:nowrap;}
.ctrl-sep{width:1px;height:20px;background:var(--border);flex-shrink:0;}
select,input[type=number]{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text);background:var(--bg-input);border:1px solid var(--border-mid);border-radius:7px;padding:6px 10px;outline:none;appearance:none;transition:border-color .15s;cursor:pointer;}
select{padding-right:26px;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%236e7b8e'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 8px center;}
select:focus,input:focus{border-color:var(--sand);}
.btn{font-family:'Sora',sans-serif;font-size:11px;font-weight:600;letter-spacing:0.03em;border:none;border-radius:7px;padding:7px 14px;cursor:pointer;transition:all .15s;display:flex;align-items:center;gap:5px;white-space:nowrap;}
.btn-primary{background:var(--sand);color:#111318;box-shadow:0 2px 8px rgba(212,168,75,0.25);}
.btn-primary:hover{background:var(--sand-lt);transform:translateY(-1px);}
.btn-green{background:var(--green);color:#0d1f16;}
.btn-green:hover{background:#5edaa8;transform:translateY(-1px);}
.btn-purple{background:var(--purple);color:#0f0d1f;box-shadow:0 2px 8px rgba(167,139,250,0.25);}
.btn-purple:hover{background:#bda9ff;transform:translateY(-1px);}
.btn-ghost{background:var(--bg-raised);color:var(--text-dim);border:1px solid var(--border-mid);}
.btn-ghost:hover{background:var(--bg-card);color:var(--text);}
.status-pill{margin-left:auto;font-size:11px;color:var(--text-dim);background:var(--bg-input);border:1px solid var(--border);border-radius:20px;padding:4px 12px;font-family:'JetBrains Mono',monospace;min-width:200px;text-align:center;}
.kpi-strip{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:14px;}
.kpi{background:var(--bg-panel);border:1px solid var(--border);border-radius:10px;padding:14px 16px;position:relative;overflow:hidden;transition:border-color .2s;}
.kpi:hover{border-color:var(--border-mid);}
.kpi-accent{position:absolute;bottom:0;left:16px;right:16px;height:2px;border-radius:2px 2px 0 0;background:var(--kpi-c,var(--sand));opacity:0.6;}
.kpi-lbl{font-size:9px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-dim);margin-bottom:8px;}
.kpi-val{font-family:'JetBrains Mono',monospace;font-size:26px;font-weight:500;color:var(--text);line-height:1;letter-spacing:-0.02em;}
.kpi-val.lg{font-size:28px;}
.kpi-sub{font-size:10px;color:var(--text-dim);margin-top:5px;}
.phase-tag{display:inline-block;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:500;padding:3px 9px;border-radius:5px;margin-bottom:4px;}
.ph-NS_GREEN{background:var(--green-dim);color:var(--green);border:1px solid rgba(62,207,142,0.22);}
.ph-EW_GREEN{background:var(--blue-dim);color:var(--blue);border:1px solid rgba(88,166,255,0.22);}
.ph-ALL_RED{background:var(--red-dim);color:var(--red);border:1px solid rgba(229,83,75,0.22);}
.ph-NS_MINOR{background:var(--sand-dim);color:var(--sand);border:1px solid rgba(212,168,75,0.22);}
@keyframes kpi-pop{0%{opacity:0.5;}50%{color:var(--sand);}100%{opacity:1;}}
.pop{animation:kpi-pop .4s ease;}
.main-grid{display:grid;grid-template-columns:1fr 310px;gap:14px;}
.left-col{display:flex;flex-direction:column;gap:14px;}
.right-col{display:flex;flex-direction:column;gap:14px;}
.panel{background:var(--bg-panel);border:1px solid var(--border);border-radius:12px;padding:18px;box-shadow:var(--shadow);}
.panel-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;}
.panel-title{font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-dim);}
.panel-tag{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-faint);background:var(--bg-raised);border:1px solid var(--border);border-radius:4px;padding:2px 7px;}
.intersection-wrap{display:flex;gap:12px;align-items:flex-start;}
.map-canvas-wrap{flex-shrink:0;position:relative;width:580px;height:580px;border-radius:14px;overflow:hidden;border:1px solid var(--border-mid);box-shadow:0 0 0 1px rgba(255,255,255,0.04),0 8px 32px rgba(0,0,0,0.6);}
canvas#sat-canvas{position:absolute;inset:0;width:100%;height:100%;}
canvas#road-canvas{position:absolute;inset:0;width:100%;height:100%;}
canvas#car-canvas{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;}
canvas#booth-hint-canvas{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:5;}
.map-aside{flex:1;display:flex;flex-direction:column;gap:8px;min-width:0;}
.sig-panel{background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:14px;}
.sig-lbl{font-size:9px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-dim);margin-bottom:10px;}
.sig-row{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;}
.sig-cell{display:flex;flex-direction:column;align-items:center;gap:5px;}
.sig-dir{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--text-dim);}
.lamp{width:30px;height:30px;border-radius:50%;background:var(--bg-raised);border:1.5px solid var(--border-mid);position:relative;overflow:hidden;transition:box-shadow .3s,background .3s;}
.lamp.green{background:#1a4a30;box-shadow:0 0 0 3px rgba(62,207,142,0.15),0 0 14px rgba(62,207,142,0.5);}
.lamp.green::after{content:'';position:absolute;inset:5px;border-radius:50%;background:var(--green);opacity:0.9;}
.lamp.red{background:#3a1518;}
.lamp.red::after{content:'';position:absolute;inset:5px;border-radius:50%;background:var(--red);opacity:0.5;}
.prog-block{background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:14px;}
.prog-row{display:flex;justify-content:space-between;margin-bottom:8px;font-size:10px;}
.prog-lbl{font-weight:500;color:var(--text-dim);}
.prog-nums{font-family:'JetBrains Mono',monospace;color:var(--text);}
.prog-track{height:5px;background:var(--bg-raised);border-radius:3px;overflow:hidden;}
.prog-fill{height:100%;background:linear-gradient(90deg,var(--sand),var(--sand-lt));border-radius:3px;transition:width .5s cubic-bezier(.4,0,.2,1);}
.score-block{background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:14px;display:flex;align-items:center;gap:14px;}
.ring-wrap{flex-shrink:0;width:78px;height:78px;position:relative;}
.ring-wrap svg{width:100%;height:100%;}
.ring-center{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;}
.ring-val{font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:500;color:var(--text);line-height:1;}
.ring-lbl-sm{font-size:9px;color:var(--text-dim);margin-top:1px;}
.score-info{flex:1;}
.score-stars{font-size:18px;letter-spacing:3px;margin-bottom:5px;}
.score-note{font-size:11px;color:var(--text-dim);line-height:1.5;}
.los-panel{display:grid;grid-template-columns:repeat(6,1fr);gap:0;border:1px solid var(--border);border-radius:8px;overflow:hidden;}
.los-cell{padding:10px 6px;text-align:center;border-right:1px solid var(--border);position:relative;transition:background .3s;}
.los-cell:last-child{border-right:none;}
.los-cell.active{background:var(--los-bg,var(--bg-raised));}
.los-letter{font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:500;color:var(--text-faint);transition:color .3s;}
.los-cell.active .los-letter{color:var(--los-c,var(--text));text-shadow:0 0 12px var(--los-glow,transparent);}
.los-delay{font-size:9px;color:var(--text-dim);margin-top:3px;font-family:'JetBrains Mono',monospace;}
.los-bar{position:absolute;bottom:0;left:0;right:0;height:3px;background:var(--los-c,transparent);opacity:0;transition:opacity .3s;}
.los-cell.active .los-bar{opacity:1;}
.sparkline-wrap{width:100%;height:60px;}
canvas.sparkline{width:100%;height:100%;display:block;}
.lane-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px 20px;}
.lane-item{display:flex;flex-direction:column;gap:3px;}
.lane-label{display:flex;justify-content:space-between;font-size:10px;}
.lane-name{color:var(--text-dim);font-weight:500;}
.lane-pct{font-family:'JetBrains Mono',monospace;color:var(--text);font-size:10px;}
.lane-track{height:4px;background:var(--bg-raised);border-radius:2px;overflow:hidden;}
.lane-fill{height:100%;border-radius:2px;transition:width .35s ease,background .35s ease;}
.metric-list{display:flex;flex-direction:column;}
.mrow{display:flex;align-items:center;justify-content:space-between;padding:7px 0;border-bottom:1px solid var(--border);}
.mrow:last-child{border-bottom:none;}
.mkey{font-size:11px;color:var(--text-dim);}
.mval{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text);}
.mval.g{color:var(--green);}.mval.a{color:var(--sand);}.mval.r{color:var(--red);}.mval.p{color:var(--purple);}
.log-box{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-dim);line-height:1.9;overflow-y:auto;max-height:320px;scrollbar-width:thin;}
.log-row{display:flex;gap:10px;border-bottom:1px solid var(--border);padding:1px 0;}
.log-ts{color:var(--text-faint);flex-shrink:0;}
.log-msg{color:var(--text);}
.log-msg.ok{color:var(--green);}.log-msg.warn{color:var(--sand);}.log-msg.err{color:var(--red);}.log-msg.rl{color:var(--purple);}
.dir-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px 20px;}
.dir-block{background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:12px;}
.dir-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;}
.dir-lbl{font-size:10px;font-weight:600;letter-spacing:0.06em;}
.dir-total{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-dim);}
.dlane{display:flex;align-items:center;gap:7px;margin-bottom:5px;}
.dlane:last-child{margin-bottom:0;}
.dlane-nm{font-size:9px;color:var(--text-dim);width:52px;flex-shrink:0;}
.dlane-track{flex:1;height:7px;background:var(--bg-raised);border-radius:3px;overflow:hidden;}
.dlane-fill{height:100%;border-radius:3px;transition:width .35s ease,background .3s;}
.dlane-pct{font-family:'JetBrains Mono',monospace;font-size:9px;width:26px;text-align:right;flex-shrink:0;}
.corner-score{position:absolute;top:0;width:148px;background:rgba(8,11,18,0.85);border:1px solid rgba(255,255,255,0.12);z-index:20;display:flex;flex-direction:column;align-items:center;padding:10px 12px 12px;gap:4px;pointer-events:none;backdrop-filter:blur(6px);}
.corner-score.left{left:0;border-radius:0 0 10px 0;border-top:none;border-left:none;}
.corner-score.right{right:0;border-radius:0 0 0 10px;border-top:none;border-right:none;}
.cs-label{font-size:8px;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;color:rgba(255,255,255,0.4);}
.cs-val{font-family:'JetBrains Mono',monospace;font-size:26px;font-weight:500;line-height:1;}
.cs-val.green{color:#3ecf8e;}.cs-val.red{color:#e5534b;}
.cs-delta{font-family:'JetBrains Mono',monospace;font-size:11px;height:14px;transition:opacity .4s;}
.cs-delta.green{color:#3ecf8e;}.cs-delta.red{color:#e5534b;}
.cs-bar-track{width:112px;height:4px;background:rgba(255,255,255,0.1);border-radius:2px;overflow:hidden;}
.cs-bar-fill{height:100%;border-radius:2px;transition:width .35s ease;}
.cs-bar-fill.green{background:#3ecf8e;}.cs-bar-fill.red{background:#e5534b;}
.vol-bar{position:absolute;top:0;bottom:0;width:18px;display:flex;flex-direction:column;justify-content:flex-end;padding:8px 3px;gap:2px;z-index:10;pointer-events:none;background:rgba(5,8,15,0.6);backdrop-filter:blur(4px);}
.vol-bar.left{left:0;border-right:1px solid rgba(255,255,255,0.07);}
.vol-bar.right{right:0;border-left:1px solid rgba(255,255,255,0.07);}
.vol-seg{width:12px;height:6px;border-radius:1px;margin:0 auto;background:rgba(255,255,255,0.05);transition:background 0.15s;}
.map-coord{position:absolute;bottom:8px;left:50%;transform:translateX(-50%);font-family:'JetBrains Mono',monospace;font-size:9px;color:rgba(255,255,255,0.5);background:rgba(0,0,0,0.55);padding:2px 8px;border-radius:3px;pointer-events:none;z-index:15;letter-spacing:0.06em;backdrop-filter:blur(4px);}
.decision-panel{background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:14px;}
.decision-phase{display:flex;align-items:center;gap:8px;margin-bottom:10px;}
.decision-reason-list{display:flex;flex-direction:column;gap:5px;}
.decision-reason{display:flex;align-items:flex-start;gap:7px;font-size:10px;color:var(--text-dim);line-height:1.4;}
.decision-reason-dot{width:5px;height:5px;border-radius:50%;flex-shrink:0;margin-top:4px;}
.decision-reason-dot.green{background:var(--green);}.decision-reason-dot.red{background:var(--red);}
.decision-reason-dot.sand{background:var(--sand);}.decision-reason-dot.blue{background:var(--blue);}.decision-reason-dot.purple{background:var(--purple);}
.decision-predicted{margin-top:10px;padding-top:10px;border-top:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
.decision-predicted-lbl{font-size:9px;color:var(--text-dim);}
.decision-predicted-val{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--green);}
.trend-panel{background:var(--bg-panel);border:1px solid var(--border);border-radius:12px;padding:18px;box-shadow:var(--shadow);}
.trend-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;}
.trend-chart-wrap{background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:10px;}
.trend-chart-hd{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;}
.trend-chart-lbl{font-size:9px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:var(--text-dim);}
.trend-chart-val{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text);}
canvas.trend-canvas{width:100%;height:54px;display:block;border-radius:4px;}
.sat-row{display:flex;align-items:center;gap:6px;margin-top:4px;}
.sat-label{font-size:9px;color:var(--text-faint);width:32px;flex-shrink:0;}
.sat-track{flex:1;height:3px;background:var(--bg-raised);border-radius:2px;overflow:hidden;}
.sat-fill{height:100%;border-radius:2px;transition:width .35s ease,background .3s;}
.sat-val{font-family:'JetBrains Mono',monospace;font-size:9px;width:28px;text-align:right;color:var(--text-dim);}
.summary-card{background:var(--bg-panel);border:1px solid var(--border);border-radius:10px;padding:14px 18px;margin-bottom:14px;}
.summary-card-title{font-size:9px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:var(--text-faint);margin-bottom:12px;}
.summary-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:0;}
.summary-item{padding:0 14px;border-right:1px solid var(--border);}
.summary-item:first-child{padding-left:0;}
.summary-item:last-child{border-right:none;}
.summary-item-lbl{font-size:9px;color:var(--text-faint);letter-spacing:0.05em;text-transform:uppercase;margin-bottom:4px;}
.summary-item-val{font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:500;color:var(--text);line-height:1;}
.summary-item-sub{font-size:9px;color:var(--text-faint);margin-top:3px;}
.booth-tooltip{position:absolute;transform:translateX(-50%);background:rgba(0,0,0,0.85);border:1px solid rgba(212,168,75,0.35);color:#d4a84b;font-family:'JetBrains Mono',monospace;font-size:10px;padding:5px 10px;border-radius:5px;pointer-events:none;white-space:nowrap;backdrop-filter:blur(8px);opacity:0;transition:opacity .2s;z-index:30;}
.booth-tooltip.show{opacity:1;}

/* ── RL AGENT PANEL ── */
.rl-panel{background:linear-gradient(135deg,rgba(167,139,250,0.06),rgba(88,166,255,0.04));border:1px solid rgba(167,139,250,0.2);border-radius:12px;padding:16px;margin-bottom:14px;}
.rl-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;}
.rl-title{font-size:10px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:var(--purple);display:flex;align-items:center;gap:7px;}
.rl-dot{width:6px;height:6px;border-radius:50%;background:var(--purple);animation:breathe 1.5s ease-in-out infinite;}
.rl-badge{font-family:'JetBrains Mono',monospace;font-size:9px;padding:2px 8px;border-radius:4px;background:var(--purple-dim);color:var(--purple);border:1px solid rgba(167,139,250,0.25);}
.rl-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px;}
.rl-metric{background:var(--bg-card);border:1px solid var(--border);border-radius:7px;padding:9px 10px;}
.rl-metric-lbl{font-size:8px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-dim);margin-bottom:5px;}
.rl-metric-val{font-family:'JetBrains Mono',monospace;font-size:14px;color:var(--purple);}
.rl-network{display:flex;align-items:center;gap:12px;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:10px 14px;margin-bottom:10px;}
.rl-network-lbl{font-size:9px;color:var(--text-dim);flex-shrink:0;}
.rl-network-arch{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text);}
.rl-qvals{display:flex;gap:6px;margin-left:auto;}
.rl-qval{display:flex;flex-direction:column;align-items:center;gap:2px;}
.rl-qval-lbl{font-size:8px;color:var(--text-faint);}
.rl-qval-num{font-family:'JetBrains Mono',monospace;font-size:10px;}
.rl-qval-num.best{color:var(--green);}.rl-qval-num.other{color:var(--text-dim);}
.rl-train-bar-wrap{display:flex;align-items:center;gap:8px;}
.rl-train-bar-lbl{font-size:9px;color:var(--text-dim);width:80px;flex-shrink:0;}
.rl-train-bar-track{flex:1;height:5px;background:var(--bg-raised);border-radius:3px;overflow:hidden;}
.rl-train-bar-fill{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--purple),#7c3aed);transition:width .4s ease;}
.rl-train-bar-val{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--purple);width:40px;text-align:right;flex-shrink:0;}
canvas#rl-loss-canvas{display:block;width:100%;height:40px;border-radius:4px;background:var(--bg-card);border:1px solid var(--border);margin-top:8px;}

/* BABYLON OVERLAY */
#babylon-overlay{display:none;position:fixed;inset:0;z-index:9999;background:#050810;opacity:0;transition:opacity 0.4s ease;flex-direction:column;}
#babylon-overlay.open{display:flex;}
#babylon-overlay.visible{opacity:1;}
#babylon-canvas-wrap{flex:1;position:relative;overflow:hidden;}
#babylonCanvas{width:100%;height:100%;display:block;outline:none;touch-action:none;}
#bab-hud{position:absolute;top:0;left:0;right:0;height:60px;background:linear-gradient(180deg,rgba(2,4,12,0.97) 0%,rgba(2,4,12,0.0) 100%);display:flex;align-items:stretch;z-index:30;pointer-events:none;}
.bab-metric{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:0 22px;border-right:1px solid rgba(255,255,255,0.06);flex:1;gap:2px;}
.bab-metric:last-child{border-right:none;}
.bab-mlbl{font-size:8px;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;color:rgba(255,255,255,0.32);}
.bab-mval{font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:500;line-height:1;color:#cdd5e0;}
.bab-mval.green{color:#3ecf8e;}.bab-mval.red{color:#e5534b;}.bab-mval.sand{color:#d4a84b;}.bab-mval.purple{color:#a78bfa;}
#bab-controls{position:absolute;bottom:0;left:0;right:0;padding:14px 20px;background:linear-gradient(0deg,rgba(2,4,12,0.97) 0%,rgba(2,4,12,0.0) 100%);display:flex;align-items:center;gap:10px;z-index:30;pointer-events:all;}
.bab-btn{font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:500;background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.14);color:rgba(255,255,255,0.55);border-radius:6px;padding:8px 16px;cursor:pointer;transition:all .15s;white-space:nowrap;}
.bab-btn:hover{background:rgba(255,255,255,0.14);color:#fff;}
.bab-btn.active{background:rgba(212,168,75,0.18);border-color:rgba(212,168,75,0.5);color:#d4a84b;}
.bab-sep{width:1px;height:28px;background:rgba(255,255,255,0.08);}
.bab-phase-btn{font-family:'JetBrains Mono',monospace;font-size:10px;background:transparent;border:1px solid rgba(255,255,255,0.1);color:rgba(255,255,255,0.35);border-radius:6px;padding:8px 14px;cursor:pointer;transition:all .15s;}
.bab-phase-btn:hover{border-color:rgba(255,255,255,0.25);color:rgba(255,255,255,0.7);}
.bab-phase-btn.ns-on{border-color:rgba(62,207,142,0.55);color:#3ecf8e;background:rgba(62,207,142,0.08);}
.bab-phase-btn.ew-on{border-color:rgba(212,168,75,0.55);color:#d4a84b;background:rgba(212,168,75,0.08);}
.bab-phase-btn.rl-on{border-color:rgba(167,139,250,0.55);color:#a78bfa;background:rgba(167,139,250,0.08);}
.bab-exit{margin-left:auto;font-family:'Sora',sans-serif;font-size:10px;font-weight:600;background:rgba(229,83,75,0.1);border:1px solid rgba(229,83,75,0.28);color:rgba(229,83,75,0.75);border-radius:6px;padding:8px 18px;cursor:pointer;transition:all .15s;}
.bab-exit:hover{background:rgba(229,83,75,0.22);color:#e5534b;}
#bab-compass{position:absolute;right:20px;top:76px;width:52px;height:52px;z-index:30;pointer-events:none;}
#bab-compass svg{width:100%;height:100%;}
#bab-info{position:absolute;left:20px;top:76px;background:rgba(2,5,14,0.9);border:1px solid rgba(212,168,75,0.18);border-radius:10px;padding:14px 16px;z-index:30;min-width:200px;backdrop-filter:blur(16px);box-shadow:0 0 30px rgba(212,168,75,0.06),0 8px 32px rgba(0,0,0,0.6);pointer-events:none;}
.bab-info-title{font-size:8px;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;color:rgba(212,168,75,0.55);margin-bottom:10px;display:flex;align-items:center;gap:6px;}
.bab-live-dot{width:5px;height:5px;border-radius:50%;background:#d4a84b;box-shadow:0 0 6px rgba(212,168,75,0.8);animation:breathe 2s ease-in-out infinite;}
.bab-row{display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);}
.bab-row:last-child{border-bottom:none;}
.bab-key{font-size:9px;color:rgba(255,255,255,0.3);}
.bab-val{font-family:'JetBrains Mono',monospace;font-size:10px;color:#e8d5a0;}
.bab-val.g{color:#3ecf8e;}.bab-val.r{color:#e5534b;}.bab-val.s{color:#d4a84b;}.bab-val.p{color:#a78bfa;}
.bab-phase-pill{display:inline-block;font-family:'JetBrains Mono',monospace;font-size:9px;padding:2px 8px;border-radius:4px;margin-bottom:8px;}
#bab-crosshair{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:20px;height:20px;pointer-events:none;z-index:20;opacity:0.4;}
#bab-crosshair::before,#bab-crosshair::after{content:'';position:absolute;background:rgba(255,255,255,0.7);}
#bab-crosshair::before{width:1px;height:100%;left:50%;top:0;}
#bab-crosshair::after{width:100%;height:1px;top:50%;left:0;}
#bab-coords{position:absolute;bottom:80px;left:50%;transform:translateX(-50%);font-family:'JetBrains Mono',monospace;font-size:9px;color:rgba(255,255,255,0.35);background:rgba(0,0,0,0.45);padding:3px 12px;border-radius:4px;pointer-events:none;z-index:20;letter-spacing:0.08em;backdrop-filter:blur(6px);}
#bab-hint{position:absolute;bottom:66px;right:20px;font-family:'JetBrains Mono',monospace;font-size:9px;color:rgba(255,255,255,0.2);line-height:1.8;text-align:right;pointer-events:none;z-index:30;}
#bab-loading{position:absolute;inset:0;z-index:50;background:#050810;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;transition:opacity 0.5s;}
#bab-loading.done{opacity:0;pointer-events:none;}
.bab-spinner{width:40px;height:40px;border:2px solid rgba(212,168,75,0.15);border-top-color:#d4a84b;border-radius:50%;animation:spin 0.8s linear infinite;}
@keyframes spin{to{transform:rotate(360deg);}}
.bab-loading-txt{font-family:'JetBrains Mono',monospace;font-size:11px;color:rgba(212,168,75,0.6);letter-spacing:0.1em;}

::-webkit-scrollbar{width:4px;}::-webkit-scrollbar-track{background:transparent;}::-webkit-scrollbar-thumb{background:var(--border-str);border-radius:2px;}
@keyframes fadeUp{from{opacity:0;transform:translateY(6px);}to{opacity:1;transform:translateY(0);}}
.shell>*{animation:fadeUp .35s ease both;}
.shell>*:nth-child(1){animation-delay:.05s;}.shell>*:nth-child(2){animation-delay:.1s;}
.shell>*:nth-child(3){animation-delay:.15s;}.shell>*:nth-child(4){animation-delay:.2s;}
@media(max-width:1100px){.main-grid{grid-template-columns:1fr;}.kpi-strip{grid-template-columns:repeat(3,1fr);}.trend-grid{grid-template-columns:1fr 1fr;}.summary-grid{grid-template-columns:repeat(2,1fr);gap:10px;}.rl-metrics{grid-template-columns:repeat(2,1fr);}}
@media(max-width:700px){.kpi-strip{grid-template-columns:repeat(2,1fr);}.intersection-wrap{flex-direction:column;}.map-canvas-wrap{width:100%;height:340px;}.trend-grid{grid-template-columns:1fr;}}

/* ── BATTLE PANEL ── */
.battle-panel{background:var(--bg-panel);border:1px solid rgba(212,168,75,0.18);border-radius:14px;padding:20px 22px 24px;margin-top:14px;box-shadow:0 0 40px rgba(212,168,75,0.04),var(--shadow-lg);}
.battle-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:10px;}
.battle-title{font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:var(--sand);display:flex;align-items:center;gap:8px;}
.battle-subtitle{font-size:10px;color:var(--text-dim);}
.winner-banner{display:flex;align-items:center;justify-content:center;gap:12px;background:linear-gradient(135deg,rgba(212,168,75,0.12),rgba(212,168,75,0.04));border:1px solid rgba(212,168,75,0.3);border-radius:10px;padding:12px 20px;margin-bottom:16px;animation:fadeUp .4s ease;}
.winner-icon{font-size:22px;}
.winner-text{font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:500;color:var(--sand);letter-spacing:0.06em;}
.battle-grid{display:grid;grid-template-columns:1fr 90px 1fr;gap:14px;align-items:start;}
.battle-side{background:var(--bg-card);border:1px solid var(--border);border-radius:10px;padding:14px;transition:border-color .3s,box-shadow .3s;}
.battle-side.winning{border-color:rgba(62,207,142,0.4);box-shadow:0 0 20px rgba(62,207,142,0.08);}
.battle-side.losing{border-color:rgba(229,83,75,0.2);opacity:0.85;}
.battle-side-header{display:flex;align-items:center;gap:8px;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid var(--border);}
.battle-side-label{font-size:11px;font-weight:700;letter-spacing:0.06em;flex:1;}
.fixed-header .battle-side-label{color:var(--text-dim);}
.ai-header .battle-side-label{color:var(--purple);}
.battle-side-tag{font-size:9px;color:var(--text-faint);font-family:'JetBrains Mono',monospace;}
.battle-status-dot{width:7px;height:7px;border-radius:50%;background:var(--text-faint);flex-shrink:0;transition:background .3s,box-shadow .3s;}
.battle-status-dot.active{background:var(--green);box-shadow:0 0 6px rgba(62,207,142,0.7);animation:breathe 1.5s ease-in-out infinite;}
.battle-metrics{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;}
.bm-card{background:var(--bg-raised);border:1px solid var(--border);border-radius:7px;padding:8px 10px;}
.bm-label{font-size:8px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-dim);margin-bottom:4px;}
.bm-val{font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:500;color:var(--text);line-height:1;margin-bottom:5px;}
.bm-los{font-size:20px;}
.bm-sub{font-size:9px;color:var(--text-faint);}
.bm-bar-track{height:3px;background:var(--bg-panel);border-radius:2px;overflow:hidden;}
.bm-bar-fill{height:100%;border-radius:2px;transition:width .4s ease;}
.fixed-fill{background:linear-gradient(90deg,var(--text-dim),var(--text-dim));}
.ai-fill{background:linear-gradient(90deg,var(--purple),#7c3aed);}
.battle-chart-wrap{position:relative;}
.battle-chart{width:100%;height:52px;display:block;border-radius:5px;background:var(--bg-raised);}
.battle-chart-lbl{font-size:8px;color:var(--text-faint);margin-top:3px;text-align:center;font-family:'JetBrains Mono',monospace;letter-spacing:0.06em;}
.battle-vs{display:flex;flex-direction:column;align-items:center;justify-content:flex-start;padding-top:48px;gap:12px;}
.vs-ring{width:52px;height:52px;border-radius:50%;border:2px solid rgba(212,168,75,0.4);display:flex;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;color:var(--sand);background:var(--bg-card);box-shadow:0 0 20px rgba(212,168,75,0.08);}
.vs-delta-wrap{display:flex;flex-direction:column;gap:5px;width:100%;}
.vs-delta-row{display:flex;flex-direction:column;align-items:center;gap:1px;}
.vs-delta-lbl{font-size:7px;color:var(--text-faint);letter-spacing:0.08em;text-transform:uppercase;}
.vs-delta-val{font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:500;color:var(--text);}
.vs-delta-val.ai-ahead{color:var(--green);}
.vs-delta-val.fixed-ahead{color:var(--red);}
.vs-step-badge{font-family:'JetBrains Mono',monospace;font-size:8px;padding:3px 8px;border-radius:4px;background:var(--bg-raised);border:1px solid var(--border);color:var(--text-faint);text-align:center;letter-spacing:0.06em;}
@media(max-width:900px){.battle-grid{grid-template-columns:1fr;}.battle-vs{flex-direction:row;padding-top:0;}.vs-delta-wrap{flex-direction:row;justify-content:center;}.vs-ring{width:40px;height:40px;font-size:11px;}}
</style>
</head>
<body>

<!-- BABYLON OVERLAY -->
<div id="babylon-overlay">
  <div id="babylon-canvas-wrap">
    <div id="bab-loading"><div class="bab-spinner"></div><div class="bab-loading-txt">BUILDING 3D ENVIRONMENT…</div></div>
    <canvas id="babylonCanvas"></canvas>
    <div id="bab-hud">
      <div class="bab-metric"><span class="bab-mlbl">Efficiency</span><span class="bab-mval sand" id="bab-eff">—%</span></div>
      <div class="bab-metric"><span class="bab-mlbl">Cleared</span><span class="bab-mval green" id="bab-cleared">0</span></div>
      <div class="bab-metric"><span class="bab-mlbl">Crashes</span><span class="bab-mval red" id="bab-crash">0</span></div>
      <div class="bab-metric"><span class="bab-mlbl">Phase</span><span class="bab-mval" id="bab-phase" style="font-size:13px;letter-spacing:.04em;">NS_GREEN</span></div>
      <div class="bab-metric"><span class="bab-mlbl">Avg Wait</span><span class="bab-mval" id="bab-wait">0.0s</span></div>
      <div class="bab-metric"><span class="bab-mlbl">RL Q-val</span><span class="bab-mval purple" id="bab-qval">—</span></div>
      <div class="bab-metric"><span class="bab-mlbl">ε Explore</span><span class="bab-mval purple" id="bab-eps">1.00</span></div>
    </div>
    <div id="bab-info">
      <div class="bab-info-title"><span class="bab-live-dot"></span>Live Intel · Ground View</div>
      <div id="bab-phase-pill" class="bab-phase-pill ph-NS_GREEN">NS_GREEN</div>
      <div class="bab-row"><span class="bab-key">Throughput</span><span class="bab-val g" id="bab-thru">0 veh</span></div>
      <div class="bab-row"><span class="bab-key">Avg Wait</span><span class="bab-val" id="bab-avgwait">0.0s</span></div>
      <div class="bab-row"><span class="bab-key">NS Queue</span><span class="bab-val g" id="bab-ns2">0 veh</span></div>
      <div class="bab-row"><span class="bab-key">EW Queue</span><span class="bab-val s" id="bab-ew2">0 veh</span></div>
      <div class="bab-row"><span class="bab-key">LOS</span><span class="bab-val" id="bab-los">—</span></div>
      <div class="bab-row"><span class="bab-key">RL Action</span><span class="bab-val p" id="bab-rl-action">—</span></div>
      <div class="bab-row"><span class="bab-key">DQN Loss</span><span class="bab-val p" id="bab-rl-loss">—</span></div>
    </div>
    <div id="bab-compass"><svg viewBox="0 0 52 52" fill="none"><circle cx="26" cy="26" r="24" fill="rgba(2,5,14,0.7)" stroke="rgba(212,168,75,0.3)" stroke-width="1"/><polygon points="26,6 29,24 26,22 23,24" fill="#e5534b"/><polygon points="26,46 29,28 26,30 23,28" fill="rgba(255,255,255,0.4)"/><text x="26" y="18" text-anchor="middle" font-family="monospace" font-size="7" fill="rgba(229,83,75,0.9)">N</text><circle cx="26" cy="26" r="2" fill="rgba(212,168,75,0.6)"/></svg></div>
    <div id="bab-crosshair"></div>
    <div id="bab-coords">LAT 12.9716° N · LON 77.5946° E · ALT 8.4m · GROUND LEVEL</div>
    <div id="bab-hint">Mouse drag · Rotate view<br>Scroll · Zoom in/out<br>WASD · Move camera<br>Right-drag · Pan</div>
    <div id="bab-controls">
      <span class="bab-mlbl" style="color:rgba(255,255,255,0.22);font-size:8px;letter-spacing:.16em;">CAMERA</span>
      <button class="bab-btn active" id="bab-cam-ground" onclick="babSetCam('ground')">🚶 Ground Level</button>
      <button class="bab-btn" id="bab-cam-elevated" onclick="babSetCam('elevated')">🏗 Elevated</button>
      <button class="bab-btn" id="bab-cam-cinematic" onclick="babSetCam('cinematic')">🎬 Cinematic</button>
      <button class="bab-btn" id="bab-cam-overhead" onclick="babSetCam('overhead')">🛸 Overhead</button>
      <div class="bab-sep"></div>
      <span class="bab-mlbl" style="color:rgba(255,255,255,0.22);font-size:8px;letter-spacing:.16em;">PHASE</span>
      <button class="bab-phase-btn" id="bab-force-ns" onclick="babForcePhase('NS_GREEN')">Force N/S Green</button>
      <button class="bab-phase-btn" id="bab-force-ew" onclick="babForcePhase('EW_GREEN')">Force E/W Green</button>
      <div class="bab-sep"></div>
      <button class="bab-phase-btn" id="bab-mode-rl" onclick="setOpMode('rl')">🧠 DQN Policy</button>
      <button class="bab-phase-btn" id="bab-mode-fixed" onclick="setOpMode('fixed')">⏱ Fixed Timer</button>
      <button class="bab-exit" onclick="closeBabylon()">✕ Exit 3D View</button>
    </div>
  </div>
</div>

<!-- MAIN DASHBOARD -->
<div class="shell">
<header class="header">
  <div class="brand">
    <div class="brand-mark">
      <svg viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="7" height="7" rx="1.5" fill="#d4a84b" opacity="0.9"/><rect x="14" y="3" width="7" height="7" rx="1.5" fill="#3ecf8e" opacity="0.5"/><rect x="3" y="14" width="7" height="7" rx="1.5" fill="#3ecf8e" opacity="0.5"/><rect x="14" y="14" width="7" height="7" rx="1.5" fill="#d4a84b" opacity="0.9"/></svg>
    </div>
    <div>
      <div class="brand-name">IntelliFlow</div>
      <div class="brand-sub">Adaptive Traffic Control · DQN Reinforcement Learning · Live Training</div>
    </div>
  </div>
  <div class="header-right">
    <div class="live-pill"><div class="live-dot"></div>Live Environment</div>
<button onclick="toggleFullscreen()" id="btn-fs" style="font-family:'Sora',sans-serif;font-size:10px;font-weight:600;background:var(--bg-raised);border:1px solid var(--border-mid);color:var(--text-dim);border-radius:7px;padding:5px 12px;cursor:pointer;display:flex;align-items:center;gap:5px;transition:all .15s;">
  <svg width="11" height="11" viewBox="0 0 11 11" fill="none"><path d="M1 4V1h3M7 1h3v3M10 7v3H7M4 10H1V7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
  <span id="fs-label">Fullscreen</span>
</button>
    <div class="clock"><div class="clock-t" id="clock-t">--:--:--</div><div class="clock-d" id="clock-d">---</div></div>
  </div>
</header>

<div class="ctrl-bar">
  <span class="ctrl-lbl">Scenario</span>
  <select id="task-sel">
    <option value="task_suburban_steady">Easy — Suburban Steady Flow</option>
    <option value="task_urban_stochastic">Medium — Urban Stochastic Rush</option>
    <option value="task_rush_hour_crisis">Hard — Rush Hour Crisis</option>
  </select>
  <div class="ctrl-sep"></div>
  <span class="ctrl-lbl">Seed</span>
  <input type="number" id="seed-in" placeholder="random" style="width:82px">
  <div class="ctrl-sep"></div>
  <button class="btn btn-primary" id="btn-reset">
    <svg width="11" height="11" viewBox="0 0 12 12" fill="none"><path d="M2 6a4 4 0 1 1 1 2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M2 9V6h3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
    New Episode
  </button>
  <button class="btn btn-purple" id="btn-run-rl">
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><polygon points="2,1 9,5 2,9" fill="currentColor"/></svg>
    Run DQN Agent
  </button>
  <button class="btn btn-green" id="btn-run">
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><polygon points="2,1 9,5 2,9" fill="currentColor"/></svg>
    Run Pressure Policy
  </button>
  <button class="btn btn-ghost" id="btn-stop">
    <svg width="9" height="9" viewBox="0 0 9 9" fill="none"><rect x="1" y="1" width="7" height="7" rx="1.5" fill="currentColor"/></svg>
    Stop
  </button>
  <div class="status-pill" id="status-txt">Standby — press New Episode to begin</div>
</div>

<!-- RL AGENT PANEL -->
<div class="rl-panel" id="rl-panel">
  <div class="rl-header">
    <div class="rl-title"><span class="rl-dot"></span>Deep Q-Network Agent</div>
    <span class="rl-badge" id="rl-status-badge">INITIALISING</span>
  </div>
  <div class="rl-metrics">
    <div class="rl-metric"><div class="rl-metric-lbl">Episodes Trained</div><div class="rl-metric-val" id="rl-episodes">0</div></div>
    <div class="rl-metric"><div class="rl-metric-lbl">Replay Buffer</div><div class="rl-metric-val" id="rl-buffer">0 / 2000</div></div>
    <div class="rl-metric"><div class="rl-metric-lbl">ε Epsilon</div><div class="rl-metric-val" id="rl-epsilon">1.000</div></div>
    <div class="rl-metric"><div class="rl-metric-lbl">Avg Loss</div><div class="rl-metric-val" id="rl-loss-val">—</div></div>
  </div>
  <div class="rl-network">
    <span class="rl-network-lbl">Architecture:</span>
    <span class="rl-network-arch">Input(57) → Dense(128,ReLU) → Dense(128,ReLU) → Dense(64,ReLU) → Q(5)</span>
    <div class="rl-qvals" id="rl-qvals">
      <div class="rl-qval"><span class="rl-qval-lbl">HOLD</span><span class="rl-qval-num other" id="rl-q0">—</span></div>
      <div class="rl-qval"><span class="rl-qval-lbl">SWITCH</span><span class="rl-qval-num other" id="rl-q1">—</span></div>
      <div class="rl-qval"><span class="rl-qval-lbl">EXTEND</span><span class="rl-qval-num other" id="rl-q2">—</span></div>
      <div class="rl-qval"><span class="rl-qval-lbl">ALL_RED</span><span class="rl-qval-num other" id="rl-q3">—</span></div>
      <div class="rl-qval"><span class="rl-qval-lbl">YIELD</span><span class="rl-qval-num other" id="rl-q4">—</span></div>
    </div>
  </div>
  <div class="rl-train-bar-wrap" style="margin-bottom:6px;">
    <span class="rl-train-bar-lbl">Training Progress</span>
    <div class="rl-train-bar-track"><div class="rl-train-bar-fill" id="rl-train-bar" style="width:0%"></div></div>
    <span class="rl-train-bar-val" id="rl-train-pct">0%</span>
  </div>
  <div class="rl-train-bar-wrap">
    <span class="rl-train-bar-lbl">Reward (rolling)</span>
    <div class="rl-train-bar-track"><div class="rl-train-bar-fill" id="rl-reward-bar" style="width:0%;background:linear-gradient(90deg,var(--green),#22c55e)"></div></div>
    <span class="rl-train-bar-val" id="rl-reward-val" style="color:var(--green)">0.0</span>
  </div>
  <canvas id="rl-loss-canvas"></canvas>
</div>

<div class="summary-card">
  <div class="summary-card-title">System Summary</div>
  <div class="summary-grid">
    <div class="summary-item"><div class="summary-item-lbl">Total Vehicles Processed</div><div class="summary-item-val" id="sum-total">—</div><div class="summary-item-sub" id="sum-total-sub">arrived / cleared</div></div>
    <div class="summary-item"><div class="summary-item-lbl">Avg Network Delay</div><div class="summary-item-val" id="sum-delay">—</div><div class="summary-item-sub" id="sum-delay-sub">seconds per vehicle</div></div>
    <div class="summary-item"><div class="summary-item-lbl">Peak Congestion</div><div class="summary-item-val" id="sum-peak">—</div><div class="summary-item-sub" id="sum-peak-sub">max queue observed</div></div>
    <div class="summary-item"><div class="summary-item-lbl">CO₂ Estimate</div><div class="summary-item-val" id="sum-co2">—</div><div class="summary-item-sub">kg (COPERT idle proxy)</div></div>
  </div>
</div>

<div class="kpi-strip">
  <div class="kpi" style="--kpi-c:var(--sand)"><div class="kpi-lbl">Signal Phase</div><div id="phase-tag" class="phase-tag ph-NS_GREEN">NS_GREEN</div><div class="kpi-sub" id="phase-el">Elapsed 0s</div><div class="kpi-accent"></div></div>
  <div class="kpi" style="--kpi-c:var(--blue)"><div class="kpi-lbl">Episode Step</div><div class="kpi-val lg" id="kpi-step">0</div><div class="kpi-sub" id="kpi-hor">of — total</div><div class="kpi-accent"></div></div>
  <div class="kpi" style="--kpi-c:var(--green)"><div class="kpi-lbl">Efficiency Index</div><div class="kpi-val lg" id="kpi-score">—</div><div class="kpi-sub" id="kpi-score-lbl">not evaluated</div><div class="kpi-accent"></div></div>
  <div class="kpi" style="--kpi-c:var(--sand)"><div class="kpi-lbl">Flow Rate (veh/s)</div><div class="kpi-val lg" id="kpi-thru">0</div><div class="kpi-sub">vehicles cleared</div><div class="kpi-accent"></div></div>
  <div class="kpi" style="--kpi-c:var(--red)"><div class="kpi-lbl">Avg Wait Time</div><div class="kpi-val lg" id="kpi-delay">0.0s</div><div class="kpi-sub">per vehicle (HCM)</div><div class="kpi-accent"></div></div>
  <div class="kpi" style="--kpi-c:var(--green)"><div class="kpi-lbl">Level of Service</div><div class="kpi-val lg" id="kpi-los" style="font-size:32px;">—</div><div class="kpi-sub" id="kpi-los-sub">—</div><div class="kpi-accent"></div></div>
</div>

<div class="main-grid">
  <div class="left-col">
    <div class="panel">
      <div class="panel-hd">
        <div class="panel-title">Live Intersection</div>
        <div style="display:flex;gap:8px;align-items:center;">
          <span class="panel-tag" id="map-tag">PHASE: —</span>
          <button class="btn btn-ghost" id="btn-fullscreen" style="padding:4px 10px;font-size:10px;background:linear-gradient(135deg,rgba(212,168,75,0.15),rgba(212,168,75,0.05));border-color:rgba(212,168,75,0.3);color:#d4a84b;" onclick="openBabylon()">
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M1 4V1h3M6 1h3v3M9 6v3H6M4 9H1V6" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>
            Enter 3D Ground View
          </button>
        </div>
      </div>
      <div class="intersection-wrap">
        <div class="map-canvas-wrap" id="map-canvas-wrap">
          <canvas id="sat-canvas" width="860" height="860"></canvas>
          <canvas id="road-canvas" width="860" height="860"></canvas>
          <canvas id="car-canvas"  width="860" height="860"></canvas>
          <canvas id="booth-hint-canvas" width="860" height="860"></canvas>
          <div class="corner-score left" id="cs-tl"><span class="cs-label">Flow Rate</span><span class="cs-val green" id="cs-tl-val">+0</span><span class="cs-delta green" id="cs-tl-delta">&nbsp;</span><div class="cs-bar-track"><div class="cs-bar-fill green" id="cs-tl-bar" style="width:0%"></div></div></div>
          <div class="corner-score right" id="cs-tr"><span class="cs-label">Crashes</span><span class="cs-val red" id="cs-tr-val">-0</span><span class="cs-delta red" id="cs-tr-delta">&nbsp;</span><div class="cs-bar-track"><div class="cs-bar-fill red" id="cs-tr-bar" style="width:0%"></div></div></div>
          <div class="vol-bar left" id="vol-left"></div>
          <div class="vol-bar right" id="vol-right"></div>
          <div class="map-coord">LAT 12.9716° N · LON 77.5946° E · ZOOM 18</div>
          <div class="booth-tooltip" id="booth-tooltip" style="bottom:52%;left:50%;">🏙 Enter 3D Ground View</div>
        </div>
        <div class="map-aside">
          <div class="sig-panel">
            <div class="sig-lbl">Signal State</div>
            <div id="sig-phase-tag" class="phase-tag ph-NS_GREEN" style="font-size:11px;margin-bottom:10px;">NS_GREEN</div>
            <div class="sig-row">
              <div class="sig-cell"><div class="lamp red" id="lamp-N"></div><div class="sig-dir">N</div></div>
              <div class="sig-cell"><div class="lamp red" id="lamp-S"></div><div class="sig-dir">S</div></div>
              <div class="sig-cell"><div class="lamp red" id="lamp-E"></div><div class="sig-dir">E</div></div>
              <div class="sig-cell"><div class="lamp red" id="lamp-W"></div><div class="sig-dir">W</div></div>
            </div>
          </div>
          <div class="prog-block">
            <div class="prog-row"><span class="prog-lbl">Episode Progress</span><span class="prog-nums"><span id="prog-step">0</span> / <span id="prog-hor">—</span></span></div>
            <div class="prog-track"><div class="prog-fill" id="prog-fill" style="width:0%"></div></div>
          </div>
          <div class="score-block">
            <div class="ring-wrap">
              <svg viewBox="0 0 90 90"><circle cx="45" cy="45" r="34" fill="none" stroke="#242938" stroke-width="8"/><circle id="score-ring" cx="45" cy="45" r="34" fill="none" stroke="#d4a84b" stroke-width="8" stroke-linecap="round" stroke-dasharray="0 213.6" stroke-dashoffset="53.4" style="transition:stroke-dasharray .6s cubic-bezier(.4,0,.2,1),stroke .4s;"/></svg>
              <div class="ring-center"><div class="ring-val" id="ring-val">—</div><div class="ring-lbl-sm">eff. idx</div></div>
            </div>
            <div class="score-info"><div class="score-stars" id="score-stars">☆☆☆</div><div class="score-note" id="score-note">Run a policy to evaluate performance.</div></div>
          </div>
          <div class="decision-panel">
            <div class="decision-phase">
              <div class="sig-lbl" style="margin-bottom:0;">Current Decision</div>
              <div id="dec-phase-tag" class="phase-tag ph-NS_GREEN" style="font-size:10px;margin-bottom:0;padding:2px 7px;">NS_GREEN</div>
            </div>
            <div class="decision-reason-list" id="dec-reason-list">
              <div class="decision-reason"><div class="decision-reason-dot sand"></div><span style="color:var(--text-faint);">Awaiting episode data…</span></div>
            </div>
            <div class="decision-predicted"><span class="decision-predicted-lbl">Predicted throughput gain</span><span class="decision-predicted-val" id="dec-gain">—</span></div>
          </div>
          <div class="panel" style="padding:12px;background:var(--bg-card);">
            <div class="metric-list">
              <div class="mrow"><div class="mkey">NS Queue Length</div><div class="mval g" id="m-ns">0 veh</div></div>
              <div class="mrow"><div class="mkey">EW Queue Length</div><div class="mval a" id="m-ew">0 veh</div></div>
              <div class="mrow"><div class="mkey">Efficiency Index</div><div class="mval" id="m-viz-score" style="color:#d4a84b;">0%</div></div>
              <div class="mrow"><div class="mkey">Crashes</div><div class="mval r" id="m-crashes">0</div></div>
              <div class="mrow"><div class="mkey">Vehicles Cleared</div><div class="mval g" id="m-smooth">0</div></div>
              <div class="mrow"><div class="mkey">CO₂ est.</div><div class="mval" id="m-co2">0 kg</div></div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="panel">
      <div class="panel-hd"><div class="panel-title">Approach Queue Occupancy &amp; Saturation</div><span class="panel-tag" id="spill-tag">SPILLBACK: 0 lanes</span></div>
      <div class="dir-grid" id="dir-grid"></div>
    </div>
    <div class="trend-panel">
      <div class="panel-hd"><div class="panel-title">Trend Over Time</div><span class="panel-tag">Last 200 steps</span></div>
      <div class="trend-grid">
        <div class="trend-chart-wrap"><div class="trend-chart-hd"><span class="trend-chart-lbl">Avg Wait Time (s)</span><span class="trend-chart-val" id="trend-delay-val">—</span></div><canvas class="trend-canvas" id="trend-delay-canvas"></canvas></div>
        <div class="trend-chart-wrap"><div class="trend-chart-hd"><span class="trend-chart-lbl">Throughput (veh/step)</span><span class="trend-chart-val" id="trend-thru-val">—</span></div><canvas class="trend-canvas" id="trend-thru-canvas"></canvas></div>
        <div class="trend-chart-wrap"><div class="trend-chart-hd"><span class="trend-chart-lbl">Queue Buildup (veh)</span><span class="trend-chart-val" id="trend-queue-val">—</span></div><canvas class="trend-canvas" id="trend-queue-canvas"></canvas></div>
      </div>
    </div>
  </div>
  <div class="right-col">
    <div class="panel">
      <div class="panel-hd"><div class="panel-title">Level of Service — HCM 2010</div><span class="panel-tag" id="los-tag">LOS —</span></div>
      <div class="los-panel">
        <div class="los-cell" id="los-A" style="--los-c:#3ecf8e;--los-bg:rgba(62,207,142,0.08);--los-glow:rgba(62,207,142,0.5)"><div class="los-letter">A</div><div class="los-delay">≤10s</div><div class="los-bar"></div></div>
        <div class="los-cell" id="los-B" style="--los-c:#5ec4a0;--los-bg:rgba(94,196,160,0.08);--los-glow:rgba(94,196,160,0.4)"><div class="los-letter">B</div><div class="los-delay">≤20s</div><div class="los-bar"></div></div>
        <div class="los-cell" id="los-C" style="--los-c:#b8c44a;--los-bg:rgba(184,196,74,0.08);--los-glow:rgba(184,196,74,0.4)"><div class="los-letter">C</div><div class="los-delay">≤35s</div><div class="los-bar"></div></div>
        <div class="los-cell" id="los-D" style="--los-c:#d4a84b;--los-bg:rgba(212,168,75,0.08);--los-glow:rgba(212,168,75,0.4)"><div class="los-letter">D</div><div class="los-delay">≤55s</div><div class="los-bar"></div></div>
        <div class="los-cell" id="los-E" style="--los-c:#e08840;--los-bg:rgba(224,136,64,0.08);--los-glow:rgba(224,136,64,0.4)"><div class="los-letter">E</div><div class="los-delay">≤80s</div><div class="los-bar"></div></div>
        <div class="los-cell" id="los-F" style="--los-c:#e5534b;--los-bg:rgba(229,83,75,0.08);--los-glow:rgba(229,83,75,0.4)"><div class="los-letter">F</div><div class="los-delay">&gt;80s</div><div class="los-bar"></div></div>
      </div>
      <div style="margin-top:14px;">
        <div class="panel-hd" style="margin-bottom:8px;"><div class="panel-title">Clearance per Step</div><span class="panel-tag" id="spark-latest">— veh</span></div>
        <div class="sparkline-wrap"><canvas class="sparkline" id="spark-canvas"></canvas></div>
        <div style="display:flex;gap:14px;margin-top:6px;">
          <div style="display:flex;align-items:center;gap:5px;font-size:10px;color:var(--text-dim);"><div style="width:14px;height:2px;background:#3ecf8e;border-radius:1px;"></div>NS</div>
          <div style="display:flex;align-items:center;gap:5px;font-size:10px;color:var(--text-dim);"><div style="width:14px;height:2px;background:#d4a84b;border-radius:1px;"></div>EW</div>
        </div>
      </div>
    </div>
    <div class="panel"><div class="panel-hd"><div class="panel-title">Lane Occupancy</div><span class="panel-tag">12 LANES</span></div><div class="lane-grid" id="lane-grid"></div></div>
    <div class="panel">
      <div class="panel-hd"><div class="panel-title">Episode Metrics</div></div>
      <div class="metric-list">
        <div class="mrow"><div class="mkey">Efficiency Ratio</div><div class="mval g" id="dm-eff">—</div></div>
        <div class="mrow"><div class="mkey">Rolling Throughput</div><div class="mval" id="dm-rtp">—</div></div>
        <div class="mrow"><div class="mkey">Peak Wait Time</div><div class="mval r" id="dm-pdly">—</div></div>
        <div class="mrow"><div class="mkey">Peak Queue Length</div><div class="mval a" id="dm-pq">—</div></div>
        <div class="mrow"><div class="mkey">DQN Avg Q-Value</div><div class="mval p" id="dm-qval">—</div></div>
        <div class="mrow"><div class="mkey">Step Cleared</div><div class="mval g" id="dm-sc">—</div></div>
      </div>
    </div>
    <div class="panel" style="flex:1;"><div class="panel-hd"><div class="panel-title">Event Log</div><span class="panel-tag" id="log-count">0 entries</span></div><div class="log-box" id="log-box"></div></div>
  </div>
</div>

<!-- ═══════════════════════════════════════════════════════════════
     BATTLE PANEL — Fixed Timer vs DQN AI
════════════════════════════════════════════════════════════════ -->
<div class="battle-panel" id="battle-panel">
  <div class="battle-header">
    <div class="battle-title">
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M7 1l1.5 3.5L12 5l-2.5 2.5.5 3.5L7 9.5 4 11l.5-3.5L2 5l3.5-.5z" fill="#d4a84b" opacity="0.9"/></svg>
      BATTLE MODE — Fixed Timer vs Your DQN AI
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
      <span class="battle-subtitle">Both running same episode · same seed · same scenario</span>
      <button class="btn btn-primary" id="btn-battle-start" style="font-size:10px;padding:5px 14px;">
        <svg width="9" height="9" viewBox="0 0 10 10" fill="none"><polygon points="2,1 9,5 2,9" fill="currentColor"/></svg>
        Start Battle
      </button>
      <button class="btn btn-ghost" id="btn-battle-stop" style="font-size:10px;padding:5px 12px;display:none;">Stop</button>
    </div>
  </div>

  <!-- Winner banner -->
  <div class="winner-banner" id="winner-banner" style="display:none;">
    <span class="winner-icon" id="winner-icon">🏆</span>
    <span class="winner-text" id="winner-text">—</span>
  </div>

  <!-- Two columns -->
  <div class="battle-grid">

    <!-- LEFT: Fixed Timer -->
    <div class="battle-side" id="battle-left">
      <div class="battle-side-header fixed-header">
        <div class="battle-side-label">⏱ Fixed Timer</div>
        <div class="battle-side-tag">30s cycle · no intelligence</div>
        <div class="battle-status-dot" id="fixed-dot"></div>
      </div>
      <div class="battle-metrics">
        <div class="bm-card">
          <div class="bm-label">Efficiency</div>
          <div class="bm-val" id="fixed-eff">—</div>
          <div class="bm-bar-track"><div class="bm-bar-fill fixed-fill" id="fixed-eff-bar" style="width:0%"></div></div>
        </div>
        <div class="bm-card">
          <div class="bm-label">Avg Wait</div>
          <div class="bm-val" id="fixed-wait">—</div>
          <div class="bm-bar-track"><div class="bm-bar-fill fixed-fill" id="fixed-wait-bar" style="width:0%"></div></div>
        </div>
        <div class="bm-card">
          <div class="bm-label">Vehicles Cleared</div>
          <div class="bm-val" id="fixed-cleared">—</div>
          <div class="bm-bar-track"><div class="bm-bar-fill fixed-fill" id="fixed-cleared-bar" style="width:0%"></div></div>
        </div>
        <div class="bm-card">
          <div class="bm-label">LOS</div>
          <div class="bm-val bm-los" id="fixed-los">—</div>
          <div class="bm-sub" id="fixed-step">Step 0</div>
        </div>
      </div>
      <!-- Mini queue chart -->
      <div class="battle-chart-wrap">
        <canvas id="fixed-chart" class="battle-chart"></canvas>
        <div class="battle-chart-lbl">Queue over time</div>
      </div>
    </div>

    <!-- MIDDLE: VS divider -->
    <div class="battle-vs">
      <div class="vs-ring">VS</div>
      <div class="vs-delta-wrap">
        <div class="vs-delta-row"><span class="vs-delta-lbl">Eff. gap</span><span class="vs-delta-val" id="vs-eff-delta">—</span></div>
        <div class="vs-delta-row"><span class="vs-delta-lbl">Wait gap</span><span class="vs-delta-val" id="vs-wait-delta">—</span></div>
        <div class="vs-delta-row"><span class="vs-delta-lbl">Cleared gap</span><span class="vs-delta-val" id="vs-cleared-delta">—</span></div>
      </div>
      <div class="vs-step-badge" id="vs-step-badge">STANDBY</div>
    </div>

    <!-- RIGHT: DQN AI -->
    <div class="battle-side" id="battle-right">
      <div class="battle-side-header ai-header">
        <div class="battle-side-label">🧠 DQN AI</div>
        <div class="battle-side-tag">Your trained model · ε=0 exploit</div>
        <div class="battle-status-dot" id="ai-dot"></div>
      </div>
      <div class="battle-metrics">
        <div class="bm-card">
          <div class="bm-label">Efficiency</div>
          <div class="bm-val" id="ai-eff">—</div>
          <div class="bm-bar-track"><div class="bm-bar-fill ai-fill" id="ai-eff-bar" style="width:0%"></div></div>
        </div>
        <div class="bm-card">
          <div class="bm-label">Avg Wait</div>
          <div class="bm-val" id="ai-wait">—</div>
          <div class="bm-bar-track"><div class="bm-bar-fill ai-fill" id="ai-wait-bar" style="width:0%"></div></div>
        </div>
        <div class="bm-card">
          <div class="bm-label">Vehicles Cleared</div>
          <div class="bm-val" id="ai-cleared">—</div>
          <div class="bm-bar-track"><div class="bm-bar-fill ai-fill" id="ai-cleared-bar" style="width:0%"></div></div>
        </div>
        <div class="bm-card">
          <div class="bm-label">LOS</div>
          <div class="bm-val bm-los" id="ai-los">—</div>
          <div class="bm-sub" id="ai-step">Step 0</div>
        </div>
      </div>
      <!-- Mini queue chart -->
      <div class="battle-chart-wrap">
        <canvas id="ai-chart" class="battle-chart"></canvas>
        <div class="battle-chart-lbl">Queue over time</div>
      </div>
    </div>

  </div><!-- /battle-grid -->
</div><!-- /battle-panel -->

</div><!-- /shell -->

<script>
'use strict';

/* ═══════════════════════════════════════════════════════════════════════
   DEEP Q-NETWORK (DQN) AGENT — Pure JavaScript Neural Network
   Architecture: 16-input → Dense(128,ReLU) → Dense(128,ReLU) → Dense(64,ReLU) → Q(3 actions)
   Training: Experience Replay + Target Network + Epsilon-Greedy Exploration
   Actions: 0=HOLD current phase, 1=SWITCH phase, 2=EXTEND current phase (extra 10s)
═══════════════════════════════════════════════════════════════════════ */

class Matrix {
  constructor(rows, cols) {
    this.rows = rows; this.cols = cols;
    this.data = new Float32Array(rows * cols);
  }
  get(r, c) { return this.data[r * this.cols + c]; }
  set(r, c, v) { this.data[r * this.cols + c] = v; }
  static zeros(r, c) { return new Matrix(r, c); }
  static random(r, c, scale) {
    var m = new Matrix(r, c);
    var fan = r + c;
    var s = scale || Math.sqrt(2.0 / fan); // He init
    for (var i = 0; i < m.data.length; i++) {
      var u1 = Math.random() + 1e-10, u2 = Math.random();
      m.data[i] = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2) * s;
    }
    return m;
  }
  clone() {
    var m = new Matrix(this.rows, this.cols);
    m.data.set(this.data); return m;
  }
  copyFrom(src) { this.data.set(src.data); }
  toArray() { return Array.from(this.data); }
  static fromArray(rows, cols, arr) {
    var m = new Matrix(rows, cols);
    m.data.set(arr);
    return m;
  }
}

function relu(x) { return x > 0 ? x : 0; }
function reluDeriv(x) { return x > 0 ? 1 : 0; }

class DenseLayer {
  constructor(inDim, outDim) {
    this.W = Matrix.random(outDim, inDim);
    this.b = Matrix.zeros(outDim, 1);
    this.dW = Matrix.zeros(outDim, inDim);
    this.db = Matrix.zeros(outDim, 1);
    this.mW = Matrix.zeros(outDim, inDim); this.vW = Matrix.zeros(outDim, inDim);
    this.mb = Matrix.zeros(outDim, 1);     this.vb = Matrix.zeros(outDim, 1);
    this.inDim = inDim; this.outDim = outDim;
    this.lastIn = null; this.lastOut = null;
  }
  // FIX 1: allocate out once, fill every element cleanly, remove duplicate lastOut assignment
  forward(x, activate) {
    this.lastIn = x.slice();
    var out = new Float32Array(this.outDim);
    for (var r = 0; r < this.outDim; r++) {
      var s = this.b.data[r];
      for (var c = 0; c < this.inDim; c++) s += this.W.get(r, c) * x[c];
      out[r] = activate ? relu(s) : s;
    }
    this.lastOut = out.slice();
    return out;
  }
  backward(dOut, activate) {
    var dAct = new Float32Array(this.outDim);
    for (var r = 0; r < this.outDim; r++) {
      dAct[r] = activate ? dOut[r] * reluDeriv(this.lastOut[r]) : dOut[r];
    }
    for (var r = 0; r < this.outDim; r++)
      for (var c = 0; c < this.inDim; c++)
        this.dW.set(r, c, this.dW.get(r, c) + dAct[r] * this.lastIn[c]);
    for (var r = 0; r < this.outDim; r++)
      this.db.data[r] += dAct[r];
    var dIn = new Float32Array(this.inDim);
    for (var c = 0; c < this.inDim; c++)
      for (var r = 0; r < this.outDim; r++)
        dIn[c] += this.W.get(r, c) * dAct[r];
    return dIn;
  }
  zeroGrad() {
    for (var i = 0; i < this.dW.data.length; i++) this.dW.data[i] = 0;
    for (var i = 0; i < this.db.data.length; i++) this.db.data[i] = 0;
  }
  adamStep(lr, t, beta1, beta2, eps) {
    beta1 = beta1 || 0.9; beta2 = beta2 || 0.999; eps = eps || 1e-8;
    var bc1 = 1 - Math.pow(beta1, t), bc2 = 1 - Math.pow(beta2, t);
    for (var i = 0; i < this.W.data.length; i++) {
      this.mW.data[i] = beta1 * this.mW.data[i] + (1 - beta1) * this.dW.data[i];
      this.vW.data[i] = beta2 * this.vW.data[i] + (1 - beta2) * this.dW.data[i] * this.dW.data[i];
      this.W.data[i] -= lr * (this.mW.data[i] / bc1) / (Math.sqrt(this.vW.data[i] / bc2) + eps);
    }
    for (var i = 0; i < this.b.data.length; i++) {
      this.mb.data[i] = beta1 * this.mb.data[i] + (1 - beta1) * this.db.data[i];
      this.vb.data[i] = beta2 * this.vb.data[i] + (1 - beta2) * this.db.data[i] * this.db.data[i];
      this.b.data[i] -= lr * (this.mb.data[i] / bc1) / (Math.sqrt(this.vb.data[i] / bc2) + eps);
    }
  }
  toJSON() {
    return { W: this.W.toArray(), b: this.b.toArray(), inDim: this.inDim, outDim: this.outDim };
  }
  static fromJSON(j) {
    var l = new DenseLayer(j.inDim, j.outDim);
    l.W = Matrix.fromArray(j.outDim, j.inDim, j.W);
    l.b = Matrix.fromArray(j.outDim, 1, j.b);
    return l;
  }
}

class QNetwork {
  constructor() {
    this.l1 = new DenseLayer(57, 128);
    this.l2 = new DenseLayer(128, 128);
    this.l3 = new DenseLayer(128, 64);
    this.l4 = new DenseLayer(64, 5);
    this.adamT = 0;
  }
  forward(state) {
    var x = new Float32Array(state);
    x = this.l1.forward(x, true);
    x = this.l2.forward(x, true);
    x = this.l3.forward(x, true);
    x = this.l4.forward(x, false);
    return x;
  }
  // FIX 2: accept already-computed q values — no second forward pass that would
  // corrupt all layers' lastIn/lastOut before backward() reads them
  backward(q, target_q, action) {
    var loss = 0.5 * (q[action] - target_q) * (q[action] - target_q);
    var dOut = new Float32Array(5);
    dOut[action] = q[action] - target_q;
    var d = this.l4.backward(dOut, false);
    d = this.l3.backward(d, true);
    d = this.l2.backward(d, true);
    this.l1.backward(d, true);
    return loss;
  }
  // FIX 2: ONE forward pass whose layer state is then consumed by backward()
  accumulateGrad(state, action, target_q) {
  var q = this.forward(state);
  return this.backward(q, target_q, action);
}
applyGradients(lr) {
  this.adamT++;
  this.l1.adamStep(lr, this.adamT); this.l2.adamStep(lr, this.adamT);
  this.l3.adamStep(lr, this.adamT); this.l4.adamStep(lr, this.adamT);
  this.l1.zeroGrad(); this.l2.zeroGrad();
  this.l3.zeroGrad(); this.l4.zeroGrad();
}
  
  copyWeightsFrom(src) {
    function copyLayer(dst, s) {
      dst.W.copyFrom(s.W); dst.b.copyFrom(s.b);
    }
    copyLayer(this.l1, src.l1); copyLayer(this.l2, src.l2);
    copyLayer(this.l3, src.l3); copyLayer(this.l4, src.l4);
  }
  toJSON() {
    return { l1: this.l1.toJSON(), l2: this.l2.toJSON(), l3: this.l3.toJSON(), l4: this.l4.toJSON(), adamT: this.adamT };
  }
  static fromJSON(j) {
    var net = new QNetwork();
    net.l1 = DenseLayer.fromJSON(j.l1);
    net.l2 = DenseLayer.fromJSON(j.l2);
    net.l3 = DenseLayer.fromJSON(j.l3);
    net.l4 = DenseLayer.fromJSON(j.l4);
    net.adamT = j.adamT || 0;
    return net;
  }
}

/* ── DQN Agent ── */
var DQN = {
  online: null,
  target: null,
  replay: [],
  BUFFER_MAX: 2000,
  BATCH_SIZE: 32,
  GAMMA: 0.95,
  LR: 0.0005,
  EPSILON: 1.0,
  EPS_MIN: 0.05,
  EPS_DECAY: 0.9985,
  TARGET_UPDATE_FREQ: 200,
  trainSteps: 0,
  totalSteps: 0,
  episodes: 0,
  lossHist: [],
  rewardHist: [],
  avgQHist: [],
  rollingReward: 0,
  lastState: null,
  lastAction: null,
  lastQVals: null,

  init: function() {
    this.online = new QNetwork();
    this.target = new QNetwork();
    this.target.copyWeightsFrom(this.online);
    this.replay = [];
    this.EPSILON = 1.0;
    this.trainSteps = 0;
    this.lossHist = [];
    this.rewardHist = [];
    this.episodes = 0;
    this.totalSteps = 0;
    this.rollingReward = 0;
    this.lastState = null;
    this.lastAction = null;
    this.lastQVals = null;
    this.updateUI();
    rlLog('DQN agent initialised — 16→128→128→64→3 network, Adam lr=' + this.LR);
  },

  STORAGE_KEY: 'dqn-model-v1',

  saveModel: async function() {
    try {
      var payload = {
        online:        this.online.toJSON(),
        target:        this.target.toJSON(),
        epsilon:       this.EPSILON,
        trainSteps:    this.trainSteps,
        totalSteps:    this.totalSteps,
        episodes:      this.episodes,
        lossHist:      this.lossHist.slice(-120),
        rollingReward: this.rollingReward,
        savedAt:       Date.now()
      };
      var resp = await fetch('/save_weights', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload)
      });
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
    } catch(e) {
      console.warn('DQN save failed:', e);
    }
  },

  loadModel: async function() {
    try {
      var resp = await fetch('/load_weights');
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      var json = await resp.json();
      if (!json.found || !json.data) return false;
      var d = json.data;
      this.online        = QNetwork.fromJSON(d.online);
      this.target        = QNetwork.fromJSON(d.target);
      this.EPSILON       = typeof d.epsilon      === 'number' ? d.epsilon      : 1.0;
      this.trainSteps    = d.trainSteps    || 0;
      this.totalSteps    = d.totalSteps    || 0;
      this.episodes      = d.episodes      || 0;
      this.lossHist      = d.lossHist      || [];
      this.rollingReward = d.rollingReward || 0;
      rlLog('Model restored from server · ε=' + this.EPSILON.toFixed(3) + ' · episodes=' + this.episodes + ' · steps=' + this.totalSteps, 'ok');
      return true;
    } catch(e) {
      rlLog('No saved model on server — starting fresh', 'warn');
      return false;
    }
  },

  maybeSave: function() {
    if (this.trainSteps > 0 && this.trainSteps % 50 === 0) {
      this.saveModel();
    }
  },

  extractState: function(obs) {
    if (!obs) return new Float32Array(57);
    var ql = obs.queue_lengths || [];
    var tp = obs.throughput_recent || [];
    var ai = obs.arrival_intensity || [];
    var ph = obs.phase_onehot || [1, 0, 0, 0];
    var sp = obs.spillback_flags || [];
    var state = new Float32Array(57);
    for(var i=0;i<12;i++) state[i]    = Math.min((ql[i]||0)/15.0, 1.0);
    for(var i=0;i<12;i++) state[12+i] = Math.min((tp[i]||0)/8.0,  1.0);
    for(var i=0;i<12;i++) state[24+i] = Math.min((ai[i]||0)/5.0,  1.0);
    for(var i=0;i<4;i++)  state[36+i] = ph[i]||0;
    state[40] = obs.phase_elapsed_norm||0;
    state[41] = obs.fairness_score||0;
    state[42] = obs.pressure_differential||0;
    state[43] = obs.avg_delay_norm||0;
    state[44] = obs.step_norm||0;
    for(var i=0;i<12;i++) state[45+i] = sp[i]||0;
    return state;
  },

  .computeReward: function(info, prevInfo) {
    if (!info) return 0;
    var r = 0;
    var cleared  = info.step_cleared || 0;
    var nsQ      = info.ns_queue || 0;
    var ewQ      = info.ew_queue || 0;
    var totalQ   = nsQ + ewQ;
    var delay    = info.avg_delay || 0;
    var crashes  = info.step_crashes || 0;
    var spill    = info.spillback_count || 0;

    // Primary signal: throughput
    r += cleared * 2.0;

    // Penalise waiting vehicles — mild, linear
    r -= totalQ * 0.05;

    // Penalise delay — capped so it never drowns throughput signal
    r -= Math.min(delay * 0.1, 5.0);

    // Penalise imbalance — encourages fair service
    r -= Math.abs(nsQ - ewQ) * 0.03;

    // Safety
    r -= crashes * 8.0;

    // Spillback
    r -= spill * 0.2;

    // LOS bonus/penalty — small, to guide but not dominate
    var los = info.los || '';
    if      (los === 'A') r += 0.8;
    else if (los === 'B') r += 0.4;
    else if (los === 'C') r += 0.0;
    else if (los === 'D') r -= 0.3;
    else if (los === 'E') r -= 0.7;
    else if (los === 'F') r -= 1.5;

    // Penalise needless phase switches (action=1) when queues are short
    if (this.lastAction === 1 && totalQ < 4) r -= 1.0;

    return r;
  },

  selectAction: function(obs) {
    var state = this.extractState(obs);
    this.lastState = state;
    var qVals = this.online.forward(state);
    this.lastQVals = qVals;
    var action;
    if (Math.random() < this.EPSILON) {
      action = Math.floor(Math.random() * 5);
    } else {
      action = 0;
      for (var i = 1; i < 5; i++) if (qVals[i] > qVals[action]) action = i;
    }
    this.lastAction = action;
    return action;
  },

  step: function(nextObs, reward, done) {
    if (this.lastState === null) return;
    var nextState = this.extractState(nextObs);
    this.replay.push({
      s: this.lastState,
      a: this.lastAction,
      r: reward,
      ns: nextState,
      done: done ? 1 : 0
    });
    if (this.replay.length > this.BUFFER_MAX) this.replay.shift();

    this.totalSteps++;
    this.rollingReward = 0.95 * this.rollingReward + 0.05 * reward;
    if(this.trainSteps > 15000) this.LR = 0.0002;
    if(this.trainSteps > 25000) this.LR = 0.0001;
    
    if (this.replay.length >= this.BATCH_SIZE) {
      this.trainBatch();
    }

    if (this.EPSILON > this.EPS_MIN) this.EPSILON *= this.EPS_DECAY;

    this.updateUI();
    this.maybeSave();
  },

  trainBatch: function() {
  var batch = [];
  for (var i = 0; i < this.BATCH_SIZE; i++) {
    var idx = Math.floor(Math.random() * this.replay.length);
    batch.push(this.replay[idx]);
  }

  this.online.l1.zeroGrad(); this.online.l2.zeroGrad();
  this.online.l3.zeroGrad(); this.online.l4.zeroGrad();

  var totalLoss = 0;
  for (var bi = 0; bi < batch.length; bi++) {
    var tr = batch[bi];
    var targetQ;
    if (tr.done) {
      targetQ = tr.r;
    } else {
      var nextQOnline = this.online.forward(tr.ns);
      var bestA = 0;
      for (var i = 1; i < 5; i++) if (nextQOnline[i] > nextQOnline[bestA]) bestA = i;
      var nextQTarget = this.target.forward(tr.ns);
      targetQ = tr.r + this.GAMMA * nextQTarget[bestA];
    }
    totalLoss += this.online.accumulateGrad(tr.s, tr.a, targetQ);
  }

  this.online.applyGradients(this.LR);

  this.trainSteps++;
  var avgLoss = totalLoss / this.BATCH_SIZE;
  this.lossHist.push(avgLoss);
  if (this.lossHist.length > 120) this.lossHist.shift();

  if (this.trainSteps % this.TARGET_UPDATE_FREQ === 0) {
    this.target.copyWeightsFrom(this.online);
    rlLog('Target network synced (step ' + this.trainSteps + ')');
  }

  return avgLoss;
},

  updateUI: function() {
    var st = function(id, v) { var e = document.getElementById(id); if (e) e.textContent = v; };
    st('rl-episodes', this.episodes);
    st('rl-buffer', this.replay.length + ' / ' + this.BUFFER_MAX);
    st('rl-epsilon', this.EPSILON.toFixed(3));
    var lastLoss = this.lossHist.length ? this.lossHist[this.lossHist.length - 1].toFixed(4) : '—';
    st('rl-loss-val', lastLoss);
    st('bab-eps', this.EPSILON.toFixed(2));

    var TRAIN_TARGET = 10000;
    var pct = Math.min(Math.round(this.trainSteps / TRAIN_TARGET * 100), 99);
    if (this.trainSteps >= TRAIN_TARGET && this.EPSILON <= this.EPS_MIN + 0.01) pct = 100;
    var barEl = document.getElementById('rl-train-bar');
    if (barEl) barEl.style.width = pct + '%';
    st('rl-train-pct', pct + '%');

    var maxReward = 10, rPct = Math.min(Math.max(this.rollingReward / maxReward, 0), 1) * 100;
    var rbar = document.getElementById('rl-reward-bar'); if (rbar) rbar.style.width = rPct + '%';
    st('rl-reward-val', this.rollingReward.toFixed(2));

    var badge = document.getElementById('rl-status-badge');
    if (badge) {
      if (this.replay.length < this.BATCH_SIZE) { badge.textContent = 'WARMING UP'; badge.style.background = 'rgba(229,83,75,0.15)'; badge.style.color = '#e5534b'; badge.style.borderColor = 'rgba(229,83,75,0.3)'; }
      else if (pct < 30) { badge.textContent = 'EXPLORING'; badge.style.background = 'rgba(88,166,255,0.15)'; badge.style.color = '#58a6ff'; badge.style.borderColor = 'rgba(88,166,255,0.3)'; }
      else if (pct < 70) { badge.textContent = 'LEARNING'; badge.style.background = 'rgba(212,168,75,0.15)'; badge.style.color = '#d4a84b'; badge.style.borderColor = 'rgba(212,168,75,0.3)'; }
      else { badge.textContent = 'EXPLOITING'; badge.style.background = 'rgba(62,207,142,0.15)'; badge.style.color = '#3ecf8e'; badge.style.borderColor = 'rgba(62,207,142,0.3)'; }
    }

    if (this.lastQVals) {
      var bestA = 0;
      for (var i = 1; i < 5; i++) if (this.lastQVals[i] > this.lastQVals[bestA]) bestA = i;
      var qNames = ['rl-q0','rl-q1','rl-q2','rl-q3','rl-q4'];
      qNames.forEach(function(id, i) {
        var e = document.getElementById(id); if (!e) return;
        e.textContent = DQN.lastQVals[i] !== undefined ? DQN.lastQVals[i].toFixed(3) : '—';
        e.className = 'rl-qval-num ' + (i === bestA ? 'best' : 'other');
      });
      var avgQ = (this.lastQVals[0] + this.lastQVals[1] + this.lastQVals[2]) / 3;
      st('dm-qval', avgQ.toFixed(3));
      st('bab-qval', avgQ.toFixed(2));
      st('bab-rl-action', ['HOLD','SWITCH','EXTEND'][this.lastAction !== null ? this.lastAction : 0]);
      st('bab-rl-loss', lastLoss);
    }

    drawRLLossChart();
  }
};

function rlLog(msg) { log(msg, 'rl'); }

function drawRLLossChart() {
  var canvas = document.getElementById('rl-loss-canvas');
  if (!canvas) return;
  // FIX 1: offsetWidth can be 0 if canvas is not yet visible/laid out.
  // Fall back to the canvas's own width attribute so we never get W=0,
  // which would cause the gradient and all tx() calls to produce NaN.
  var W = canvas.offsetWidth || canvas.width || 400;
  var dpr = window.devicePixelRatio || 1, H = 40;
  canvas.width = W * dpr; canvas.height = H * dpr;
  var c = canvas.getContext('2d'); c.scale(dpr, dpr);
  c.fillStyle = '#1a1f2c'; c.fillRect(0, 0, W, H);
  var data = DQN.lossHist; if (data.length < 2) return;
  var maxV = Math.max.apply(null, data.concat([0.01]));
  var px = 2, py = 2, iW = W - px*2, iH = H - py*2;
  var tx = function(i) { return px + (i / Math.max(data.length-1,1)) * iW; };
  var ty = function(v) { return py + iH - (v / maxV) * iH; };
  c.beginPath(); data.forEach(function(v,i){ if(i===0) c.moveTo(tx(i),ty(v)); else c.lineTo(tx(i),ty(v)); });
  c.lineTo(tx(data.length-1),H); c.lineTo(tx(0),H); c.closePath();
  var g = c.createLinearGradient(0,0,0,H); g.addColorStop(0,'rgba(167,139,250,0.35)'); g.addColorStop(1,'rgba(167,139,250,0)');
  c.fillStyle = g; c.fill();
  c.beginPath(); data.forEach(function(v,i){ if(i===0) c.moveTo(tx(i),ty(v)); else c.lineTo(tx(i),ty(v)); });
  c.strokeStyle = '#a78bfa'; c.lineWidth = 1.5; c.lineJoin = 'round'; c.stroke();
  c.fillStyle = 'rgba(167,139,250,0.55)'; c.font = '8px JetBrains Mono'; c.textAlign = 'right';
  c.fillText('DQN Loss', W-4, H-4);
}

/* ── Map DQN action → API action ── */
function dqnActionToApiAction(dqnAction, obs) {
  return dqnAction;  
}

/* ═══════════════════════════════════════════════════════════════════════
   SHARED STATE & HELPERS
═══════════════════════════════════════════════════════════════════════ */
const BASE = window.location.origin;
let sessionId = null, running = false, horizon = 600, logN = 0;
let nsHist = [], ewHist = [];
const MAX_H = 200, TREND_MAX = 200;
let trendDelayHist = [], trendThruHist = [], trendQueueHist = [];
let vizScore = 0, vizCrashes = 0, vizSmooth = 0, csGreenPts = 0, csRedPts = 0;
let _episodeFrozen = false;
var _liveInfo = {};

function addVizPass(n) { if(_episodeFrozen) return; vizSmooth += n; csGreenPts += n; vizScore += n; updateVizUI(); flashDelta('cs-tl-delta', null, '+' + n); }
function addVizCrash(n) { if(_episodeFrozen) return; vizCrashes += n; var pts = n * 12; csRedPts += pts; vizScore = Math.max(0, vizScore - pts); updateVizUI(); flashDelta('cs-tr-delta', null, '-' + pts); }
function flashDelta(id, _, text) {
  var e = document.getElementById(id); if (!e) return;
  e.textContent = text; e.style.opacity = '1';
  clearTimeout(e._ft); e._ft = setTimeout(function() { e.style.opacity = '0'; }, 900);
}
function effPct() { if (vizSmooth === 0) return 0; return Math.min(100, Math.max(0, vizScore)) / (vizSmooth + vizCrashes * 12) * 100; }
function updateVizUI() {
  var pct = effPct().toFixed(1) + '%';
  var st = function(id, v) { var e = document.getElementById(id); if (e) e.textContent = v; };
  st('m-viz-score', pct); st('m-crashes', vizCrashes); st('m-smooth', vizSmooth);
  st('bab-eff', pct); st('bab-crash', vizCrashes); st('bab-cleared', vizSmooth);
  var mx = Math.max(csGreenPts + csRedPts, 1);
  var csv = document.getElementById('cs-tl-val'); if (csv) csv.textContent = '+' + csGreenPts;
  var csr = document.getElementById('cs-tr-val'); if (csr) csr.textContent = '-' + csRedPts;
  var ctb = document.getElementById('cs-tl-bar'); if (ctb) ctb.style.width = Math.min(100, (csGreenPts/mx)*100).toFixed(1) + '%';
  var crb = document.getElementById('cs-tr-bar'); if (crb) crb.style.width = Math.min(100, (csRedPts/mx)*100).toFixed(1) + '%';
}

function initVolBars() {
  ['vol-left','vol-right'].forEach(function(id) {
    var el = document.getElementById(id); if (!el) return; el.innerHTML = '';
    for (var i = 0; i < 16; i++) { var s = document.createElement('div'); s.className = 'vol-seg'; el.appendChild(s); }
  });
}
function applyVolBar(id, frac) {
  var el = document.getElementById(id); if (!el) return;
  var segs = el.querySelectorAll('.vol-seg'); var n = segs.length;
  segs.forEach(function(s, i) {
    var active = frac > (n-1-i)/n; var relPos = i/n;
    if (active) s.style.background = relPos < 0.3 ? '#e5534b' : relPos < 0.6 ? '#d4a84b' : '#3ecf8e';
    else s.style.background = 'rgba(255,255,255,0.05)';
  });
}
function updateVolBars() {
  var nsCars = LANE_NAMES.filter(function(n) { return n[0]==='N'||n[0]==='S'; }).reduce(function(t,n) { return t+LQUEUES[n].filter(function(c){return !c.exited&&!c.crashed;}).length; },0);
  var ewCars = LANE_NAMES.filter(function(n) { return n[0]==='E'||n[0]==='W'; }).reduce(function(t,n) { return t+LQUEUES[n].filter(function(c){return !c.exited&&!c.crashed;}).length; },0);
  applyVolBar('vol-left', Math.min(nsCars/18,1)); applyVolBar('vol-right', Math.min(ewCars/18,1));
}

function tickClock() { var n=new Date(); document.getElementById('clock-t').textContent=n.toLocaleTimeString('en-GB',{hour12:false}); document.getElementById('clock-d').textContent=n.toLocaleDateString('en-GB',{weekday:'short',day:'numeric',month:'short'}).toUpperCase(); }
tickClock(); setInterval(tickClock,1000);

/* ═══════════════════════════════════════════════════════════════════════
   2D CANVAS INTERSECTION
═══════════════════════════════════════════════════════════════════════ */
const LANE_NAMES = ["N_through","N_right","S_through","S_right","E_through","E_right","W_through","W_right","N_left","S_left","E_left","W_left"];
var laneGrid = document.getElementById('lane-grid');
LANE_NAMES.forEach(function(n) { var d=document.createElement('div'); d.className='lane-item'; d.innerHTML='<div class="lane-label"><span class="lane-name">'+n+'</span><span class="lane-pct" id="lp-'+n+'">0%</span></div><div class="lane-track"><div class="lane-fill" id="lf-'+n+'" style="width:0%"></div></div>'; laneGrid.appendChild(d); });
const FOUR=[{id:'N',lbl:'North',col:'var(--green)',lanes:['N_through','N_right','N_left']},{id:'S',lbl:'South',col:'var(--green)',lanes:['S_through','S_right','S_left']},{id:'E',lbl:'East',col:'var(--sand)',lanes:['E_through','E_right','E_left']},{id:'W',lbl:'West',col:'var(--sand)',lanes:['W_through','W_right','W_left']}];
var dirGrid=document.getElementById('dir-grid');
FOUR.forEach(function(dir) { var b=document.createElement('div'); b.className='dir-block'; b.innerHTML='<div class="dir-head"><div class="dir-lbl" style="color:'+dir.col+'">'+dir.lbl+'</div><div class="dir-total" id="dt-'+dir.id+'">0 veh</div></div>'+dir.lanes.map(function(l) { return '<div class="dlane"><div class="dlane-nm">'+l.replace(dir.id+'_','')+'</div><div class="dlane-track"><div class="dlane-fill" id="df-'+l+'" style="width:0%;background:'+dir.col+'"></div></div><div class="dlane-pct" id="dp-'+l+'" style="color:'+dir.col+'">0%</div></div>'; }).join('')+'<div class="sat-row"><div class="sat-label">Sat.</div><div class="sat-track"><div class="sat-fill" id="sat-'+dir.id+'" style="width:0%"></div></div><div class="sat-val" id="satv-'+dir.id+'">0%</div></div>'; dirGrid.appendChild(b); });

const SZ=860; const DPR=window.devicePixelRatio||1; const MID=430; const LW=28; const NL=3;
const ROAD=LW*NL*2; const RL=MID-ROAD/2; const RR=MID+ROAD/2; const RT=MID-ROAD/2; const RB=MID+ROAD/2;
const STOP_SETBACK=28;
const STOP={N_stop:RT-STOP_SETBACK,S_stop:RB+STOP_SETBACK,E_stop:RR+STOP_SETBACK,W_stop:RL-STOP_SETBACK};
const EXIT_MARGIN=600; const SPAWN_MARGIN=300;
const LDEFS={
  N_through:{dir:'S',cx:MID+LW*0.5,stopPos:STOP.N_stop,spawnPos:-SPAWN_MARGIN,exitPos:SZ+EXIT_MARGIN},
  N_right:{dir:'S',cx:MID+LW*1.5,stopPos:STOP.N_stop,spawnPos:-SPAWN_MARGIN,exitPos:SZ+EXIT_MARGIN},
  N_left:{dir:'S',cx:MID+LW*2.5,stopPos:STOP.N_stop,spawnPos:-SPAWN_MARGIN,exitPos:SZ+EXIT_MARGIN},
  S_through:{dir:'N',cx:MID-LW*0.5,stopPos:STOP.S_stop,spawnPos:SZ+SPAWN_MARGIN,exitPos:-EXIT_MARGIN},
  S_right:{dir:'N',cx:MID-LW*1.5,stopPos:STOP.S_stop,spawnPos:SZ+SPAWN_MARGIN,exitPos:-EXIT_MARGIN},
  S_left:{dir:'N',cx:MID-LW*2.5,stopPos:STOP.S_stop,spawnPos:SZ+SPAWN_MARGIN,exitPos:-EXIT_MARGIN},
  E_through:{dir:'W',cy:MID+LW*0.5,stopPos:STOP.E_stop,spawnPos:SZ+SPAWN_MARGIN,exitPos:-EXIT_MARGIN},
  E_right:{dir:'W',cy:MID+LW*1.5,stopPos:STOP.E_stop,spawnPos:SZ+SPAWN_MARGIN,exitPos:-EXIT_MARGIN},
  E_left:{dir:'W',cy:MID+LW*2.5,stopPos:STOP.E_stop,spawnPos:SZ+SPAWN_MARGIN,exitPos:-EXIT_MARGIN},
  W_through:{dir:'E',cy:MID-LW*0.5,stopPos:STOP.W_stop,spawnPos:-SPAWN_MARGIN,exitPos:SZ+EXIT_MARGIN},
  W_right:{dir:'E',cy:MID-LW*1.5,stopPos:STOP.W_stop,spawnPos:-SPAWN_MARGIN,exitPos:SZ+EXIT_MARGIN},
  W_left:{dir:'E',cy:MID-LW*2.5,stopPos:STOP.W_stop,spawnPos:-SPAWN_MARGIN,exitPos:SZ+EXIT_MARGIN},
};
const LCOLORS={N_through:'#4ef0a8',N_right:'#6ef8bc',N_left:'#30d888',S_through:'#70c0ff',S_right:'#90d0ff',S_left:'#50a8f0',E_through:'#f0c060',E_right:'#f8d878',E_left:'#d0a040',W_through:'#f09050',W_right:'#f8b070',W_left:'#d07030'};
const LQUEUES={}; LANE_NAMES.forEach(function(n) { LQUEUES[n]=[]; });
const CAR_L=Math.round(LW*0.75); const CAR_W=Math.round(LW*0.58); const SAFE=CAR_L+12; const CAR_SPEED=2.2; const CRASH_DIST=14;
var sigState={N:false,S:false,E:false,W:false};
function carIsGreen(ln) { return sigState[ln[0]]===true; }
function crossingDirInBox(dir) { var chk=(dir==='N'||dir==='S')?['E','W']:['N','S']; for(var i=0;i<LANE_NAMES.length;i++){var ln=LANE_NAMES[i];if(chk.indexOf(ln[0])<0)continue;for(var j=0;j<LQUEUES[ln].length;j++){var car=LQUEUES[ln][j];if(car.crashed||car.exited)continue;var pos=carXY(ln,car);if(pos.x>RL+4&&pos.x<RR-4&&pos.y>RT+4&&pos.y<RB-4)return true;}} return false; }
function carXY(ln,car) { var def=LDEFS[ln]; if(!def) return {x:0,y:0}; if(def.dir==='S') return {x:def.cx,y:car.pos}; if(def.dir==='N') return {x:def.cx,y:car.pos}; if(def.dir==='E') return {x:car.pos,y:def.cy}; return {x:car.pos,y:def.cy}; }

function spawnVehicle(ln) { if(!running) return; var def=LDEFS[ln]; if(!def) return; var q=LQUEUES[ln]; if(q.length>=9) return; var tail=q[q.length-1]; if(tail&&Math.abs(tail.pos-def.spawnPos)<SAFE*3.5) return; q.push({lane:ln,pos:def.spawnPos,color:LCOLORS[ln]||'#aaa',alpha:0,moving:true,crashed:false,counted:false,exited:false}); }
function spawnFromLaneData(lanes) { if(!running||!lanes||!lanes.length) return; lanes.forEach(function(l) { var lam=l.lambda_est||0; if(lam<=0) return; if(Math.random()<1-Math.exp(-lam/8)) spawnVehicle(l.name); }); }
function spawnCleared(count,phase) {
  if(!running||count<1) return;
  var ns=phase==='NS_GREEN'||phase==='NS_MINOR',ew=phase==='EW_GREEN';
  var pool=ns?['N_through','N_right','N_left','S_through','S_right','S_left']:ew?['E_through','E_right','E_left','W_through','W_right','W_left']:[];
  var n=Math.min(count,5);
  for(var i=0;i<n;i++){(function(idx){var ln=pool[Math.floor(Math.random()*pool.length)];if(ln)setTimeout(function(){if(running)spawnVehicle(ln);},idx*180+Math.random()*80);})(i);}
}

var crashFlash=0; var crashEvents=[];
function checkCrashes() {
  var box=[]; LANE_NAMES.forEach(function(ln) { LQUEUES[ln].forEach(function(car) { if(car.crashed||car.exited) return; var pos=carXY(ln,car); if(pos.x>RL&&pos.x<RR&&pos.y>RT&&pos.y<RB) box.push({car:car,ln:ln,x:pos.x,y:pos.y}); }); });
  for(var i=0;i<box.length;i++){for(var j=i+1;j<box.length;j++){var a=box[i],b=box[j];if(a.ln===b.ln)continue;var aIsNS=a.ln[0]==='N'||a.ln[0]==='S',bIsNS=b.ln[0]==='N'||b.ln[0]==='S';if(aIsNS===bIsNS)continue;var dx=a.x-b.x,dy=a.y-b.y;if(Math.sqrt(dx*dx+dy*dy)<CRASH_DIST){a.car.crashed=true;b.car.crashed=true;crashEvents.push({x:(a.x+b.x)/2,y:(a.y+b.y)/2,t:0});crashFlash=12;addVizCrash(1);log('Crash detected','err');}}}
}
function updateVehicles(dt) {
  LANE_NAMES.forEach(function(ln) {
    var def=LDEFS[ln]; if(!def) return; var q=LQUEUES[ln];
    var green=carIsGreen(ln), stop=def.stopPos;
    var fwd=(def.dir==='S'||def.dir==='E');
    var yieldBlock=crossingDirInBox(ln[0]);

    for(var i=0;i<q.length;i++){
      var car=q[i]; if(car.crashed||car.exited) continue;
      if(car.alpha<1) car.alpha=Math.min(1,car.alpha+0.07);
      var ahead=i>0&&!q[i-1].exited&&!q[i-1].crashed?q[i-1]:null;
      var blockPos;
      if(fwd){
        blockPos=ahead?(ahead.pos-SAFE):Infinity;
        var pastStop=car.pos>=stop;
        if(!pastStop&&(!green||yieldBlock)) blockPos=Math.min(stop,blockPos);
        if(car.moving){var dist=blockPos-car.pos;if(dist>0.5)car.pos+=Math.min(CAR_SPEED*dt,dist-0.5);else car.moving=false;}
        else if(blockPos-car.pos>SAFE*0.4) car.moving=true;
        if(green&&!car.counted&&car.pos>stop&&!yieldBlock){car.counted=true;addVizPass(1);}
        if(car.pos>def.exitPos) car.exited=true;
      } else {
        blockPos=ahead?(ahead.pos+SAFE):-Infinity;
        var pastStop=car.pos<=stop;
        if(!pastStop&&(!green||yieldBlock)) blockPos=Math.max(stop,blockPos);
        if(car.moving){var dist=car.pos-blockPos;if(dist>0.5)car.pos-=Math.min(CAR_SPEED*dt,dist-0.5);else car.moving=false;}
        else if(car.pos-blockPos>SAFE*0.4) car.moving=true;
        if(green&&!car.counted&&car.pos<stop&&!yieldBlock){car.counted=true;addVizPass(1);}
        if(car.pos<def.exitPos) car.exited=true;
      }
    }
    // Single reverse-pass removal (your existing fix was correct)
    for(var i=q.length-1;i>=0;i--){
      if(q[i].crashed||q[i].exited) q.splice(i,1);
    }
  });  // ← FIXED: was }; before

  checkCrashes();
  for(var i=crashEvents.length-1;i>=0;i--){
    crashEvents[i].t+=dt/30;
    if(crashEvents[i].t>1) crashEvents.splice(i,1);
  }
  if(crashFlash>0) crashFlash-=dt;
}  // ← ADDED: this closing brace was missing

// Now drawVehicle is correctly OUTSIDE updateVehicles

function drawVehicle(c,ln,car) {
  if(car.crashed||car.exited) return; var pos=carXY(ln,car); var x=pos.x,y=pos.y; var def=LDEFS[ln];
  var angle=def.dir==='S'?Math.PI/2:def.dir==='N'?-Math.PI/2:def.dir==='E'?0:Math.PI;
  c.save(); c.translate(x,y); c.rotate(angle-Math.PI/2); c.globalAlpha=car.alpha*0.97; c.fillStyle=car.color;
  rrect(c,-CAR_W/2,-CAR_L/2,CAR_W,CAR_L,3); c.fill();
  c.fillStyle='rgba(160,220,255,0.45)'; c.fillRect(-CAR_W/2+2,-CAR_L/2+2,CAR_W-4,5);
  c.fillStyle='rgba(255,250,200,0.95)'; c.beginPath(); c.arc(-CAR_W/2+2.5,-CAR_L/2+2,2,0,Math.PI*2); c.fill();
  c.beginPath(); c.arc(CAR_W/2-2.5,-CAR_L/2+2,2,0,Math.PI*2); c.fill();
  c.globalAlpha=1; c.restore();
}
function rrect(c,x,y,w,h,r) { c.beginPath();c.moveTo(x+r,y);c.lineTo(x+w-r,y);c.arcTo(x+w,y,x+w,y+r,r);c.lineTo(x+w,y+h-r);c.arcTo(x+w,y+h,x+w-r,y+h,r);c.lineTo(x+r,y+h);c.arcTo(x,y+h,x,y+h-r,r);c.lineTo(x,y+r);c.arcTo(x,y,x+r,y,r);c.closePath(); }
function drawPoleCtx(c,x,y,axis,sig_) {
  var g=(axis==='NS')?(sig_.N||sig_.S):(sig_.E||sig_.W);
  c.fillStyle='rgba(20,24,32,0.9)'; c.strokeStyle='rgba(255,255,255,0.2)'; c.lineWidth=1;
  rrect(c,x,y,12,22,3); c.fill(); c.stroke();
  c.beginPath(); c.arc(x+6,y+6,4,0,Math.PI*2); c.fillStyle=g?'rgba(229,83,75,0.2)':'#e5534b';
  if(!g){c.shadowColor='rgba(229,83,75,0.8)';c.shadowBlur=8;} c.fill(); c.shadowBlur=0;
  c.beginPath(); c.arc(x+6,y+16,4,0,Math.PI*2); c.fillStyle=g?'#3ecf8e':'rgba(62,207,142,0.15)';
  if(g){c.shadowColor='rgba(62,207,142,1)';c.shadowBlur=12;} c.fill(); c.shadowBlur=0;
}

function drawSatelliteMap(ctx,W,H) {
  var roadL=RL,roadR=RR,roadT=RT,roadB=RB;

  // Deep earth base
  var baseGrad=ctx.createLinearGradient(0,0,W,H);
  baseGrad.addColorStop(0,'#2a2d1e');
  baseGrad.addColorStop(0.5,'#232618');
  baseGrad.addColorStop(1,'#1e2114');
  ctx.fillStyle=baseGrad;ctx.fillRect(0,0,W,H);

  // Ground texture noise
  var s=0xdeadbeef;
  function R(){s=((s*1664525+1013904223)>>>0);return s/4294967296;}

  // Grass/soil patches
  for(var gi=0;gi<320;gi++){
    var gx=R()*W,gy=R()*H,gr=R()*18+4;
    var inRoad=(gx>roadL-10&&gx<roadR+10&&gy>roadT-10&&gy<roadB+10);
    if(inRoad)continue;
    ctx.beginPath();ctx.arc(gx,gy,gr,0,Math.PI*2);
    var green=R()<0.6;
    ctx.fillStyle=green?'rgba('+(40+R()*20|0)+','+(52+R()*18|0)+','+(22+R()*12|0)+',0.35)':'rgba('+(38+R()*15|0)+','+(32+R()*12|0)+','+(18+R()*10|0)+',0.28)';
    ctx.fill();
  }

  // Realistic buildings with depth/shadow
  var buildings=[
    // Near corners - low shops
    {x:130,y:130,w:110,h:85,floors:3,style:'brick'},
    {x:255,y:110,w:75,h:70,floors:2,style:'concrete'},
    {x:110,y:240,w:80,h:95,floors:3,style:'brick'},
    {x:590,y:130,w:115,h:80,floors:3,style:'brick'},
    {x:700,y:115,w:80,h:70,floors:2,style:'concrete'},
    {x:610,y:240,w:90,h:90,floors:3,style:'brick'},
    {x:130,y:590,w:110,h:80,floors:3,style:'brick'},
    {x:255,y:620,w:75,h:70,floors:2,style:'concrete'},
    {x:110,y:500,w:80,h:85,floors:3,style:'brick'},
    {x:590,y:590,w:115,h:80,floors:3,style:'brick'},
    {x:700,y:615,w:80,h:70,floors:2,style:'concrete'},
    {x:610,y:500,w:90,h:85,floors:3,style:'brick'},
    // Mid towers
    {x:50,y:50,w:70,h:60,floors:8,style:'glass'},
    {x:720,y:50,w:80,h:65,floors:12,style:'glass'},
    {x:50,y:720,w:70,h:60,floors:8,style:'glass'},
    {x:720,y:720,w:80,h:65,floors:10,style:'glass'},
    // Far towers
    {x:20,y:180,w:50,h:140,floors:18,style:'glass'},
    {x:790,y:200,w:55,h:130,floors:22,style:'glass'},
    {x:20,y:500,w:50,h:130,floors:16,style:'glass'},
    {x:790,y:510,w:55,h:120,floors:20,style:'glass'},
    {x:180,y:20,w:140,h:50,floors:14,style:'glass'},
    {x:500,y:20,w:130,h:50,floors:18,style:'glass'},
    {x:180,y:800,w:140,h:50,floors:14,style:'glass'},
    {x:500,y:800,w:130,h:50,floors:16,style:'glass'},
  ];

  var styleBase={
    brick:  [[90,58,38],[82,52,34],[76,48,30],[96,62,40]],
    concrete:[[72,74,78],[64,68,72],[80,80,84],[68,70,76]],
    glass:  [[28,42,68],[22,36,62],[32,48,74],[24,38,65]],
  };

  buildings.forEach(function(b){
    var outside=(b.x+b.w<roadL-30||b.x>roadR+30||b.y+b.h<roadT-30||b.y>roadB+30);
    if(!outside)return;
    var cols=styleBase[b.style];
    var col=cols[Math.floor(R()*cols.length)];

    // Drop shadow
    ctx.fillStyle='rgba(0,0,0,0.45)';
    ctx.fillRect(b.x+6,b.y+6,b.w,b.h);

    // Main roof face
    ctx.fillStyle='rgb('+col[0]+','+col[1]+','+col[2]+')';
    ctx.fillRect(b.x,b.y,b.w,b.h);

    // Roof highlight (top-left lit by sun)
    var rg=ctx.createLinearGradient(b.x,b.y,b.x+b.w,b.y+b.h);
    rg.addColorStop(0,'rgba(255,255,255,0.13)');
    rg.addColorStop(1,'rgba(0,0,0,0.22)');
    ctx.fillStyle=rg;ctx.fillRect(b.x,b.y,b.w,b.h);

    // Windows grid
    if(b.style==='glass'){
      // Full glass facade
      var cols2=Math.max(2,Math.floor(b.w/14));
      var rows2=Math.max(2,Math.floor(b.h/12));
      for(var wr=0;wr<rows2;wr++){
        for(var wc=0;wc<cols2;wc++){
          var lit=R()>0.25;
          ctx.fillStyle=lit?'rgba(180,210,255,0.55)':'rgba(20,35,65,0.7)';
          ctx.fillRect(b.x+2+wc*(b.w/cols2),b.y+2+wr*(b.h/rows2),(b.w/cols2)-2,(b.h/rows2)-2);
        }
      }
    } else {
      // Punched windows
      var wCols=Math.max(2,Math.floor(b.w/22));
      var wRows=Math.max(1,Math.floor(b.h/18));
      for(var wr=0;wr<wRows;wr++){
        for(var wc=0;wc<wCols;wc++){
          var lit=R()>0.35;
          ctx.fillStyle=lit?'rgba(255,240,180,0.75)':'rgba(10,10,15,0.65)';
          ctx.fillRect(b.x+6+wc*((b.w-8)/wCols),b.y+6+wr*((b.h-8)/wRows),10,7);
        }
      }
    }

    // Rooftop details - HVAC, water towers
    if(b.floors>5){
      ctx.fillStyle='rgba(50,52,58,0.9)';
      ctx.fillRect(b.x+b.w*0.2,b.y+b.h*0.15,b.w*0.2,b.h*0.15);
      ctx.fillRect(b.x+b.w*0.6,b.y+b.h*0.6,b.w*0.18,b.h*0.18);
    }
    // Roof edge parapet
    ctx.strokeStyle='rgba(0,0,0,0.4)';ctx.lineWidth=1.5;
    ctx.strokeRect(b.x,b.y,b.w,b.h);
  });

  // Parking lots
  [[165,165,95,90],[590,165,95,90],[165,590,95,90],[590,590,95,90]].forEach(function(p){
    ctx.fillStyle='#1e2024';ctx.fillRect(p[0],p[1],p[2],p[3]);
    ctx.strokeStyle='rgba(255,255,255,0.12)';ctx.lineWidth=1;
    for(var pi=0;pi<5;pi++){ctx.beginPath();ctx.moveTo(p[0]+pi*18,p[1]);ctx.lineTo(p[0]+pi*18,p[1]+p[3]);ctx.stroke();}
    for(var pi=0;pi<5;pi++){ctx.beginPath();ctx.moveTo(p[0],p[1]+pi*18);ctx.lineTo(p[0]+p[2],p[1]+pi*18);ctx.stroke();}
  });

  // Footpaths / sidewalks alongside roads
  ctx.fillStyle='rgba(180,170,150,0.18)';
  ctx.fillRect(roadL-22,0,22,roadT);ctx.fillRect(roadL-22,roadB,22,H-roadB);
  ctx.fillRect(roadR,0,22,roadT);ctx.fillRect(roadR,roadB,22,H-roadB);
  ctx.fillRect(0,roadT-22,roadL,22);ctx.fillRect(roadR,roadT-22,H-roadR,22);
  ctx.fillRect(0,roadB,roadL,22);ctx.fillRect(roadR,roadB,H-roadR,22);

  // Road surfaces - dark tarmac with texture
  var darkRoad='#1a1c22';
  ctx.fillStyle=darkRoad;
  ctx.fillRect(roadL,0,roadR-roadL,roadT);
  ctx.fillRect(roadL,roadB,roadR-roadL,H-roadB);
  ctx.fillRect(0,roadT,roadL,roadB-roadT);
  ctx.fillRect(roadR,roadT,W-roadR,roadB-roadT);
  ctx.fillStyle='#1c1e24';
  ctx.fillRect(roadL,roadT,roadR-roadL,roadB-roadT);

  // Road texture grain
  ctx.save();
  for(var ri=0;ri<180;ri++){
    var rx=roadL+R()*(W-roadL*2),ry=R()*H;
    var inRoadX=(rx>roadL&&rx<roadR)||(ry>roadT&&ry<roadB);
    if(!inRoadX)continue;
    ctx.fillStyle='rgba(255,255,255,'+( 0.02+R()*0.03)+')';
    ctx.fillRect(rx,ry,R()*6+1,1);
  }
  ctx.restore();

  // Lane markings - crisp white dashes
  ctx.strokeStyle='rgba(255,252,200,0.82)';ctx.lineWidth=2.2;ctx.setLineDash([22,16]);
  var MID_X=(roadL+roadR)/2,MID_Y=(roadT+roadB)/2;
  ctx.beginPath();ctx.moveTo(MID_X,0);ctx.lineTo(MID_X,roadT);ctx.stroke();
  ctx.beginPath();ctx.moveTo(MID_X,roadB);ctx.lineTo(MID_X,H);ctx.stroke();
  ctx.beginPath();ctx.moveTo(0,MID_Y);ctx.lineTo(roadL,MID_Y);ctx.stroke();
  ctx.beginPath();ctx.moveTo(roadR,MID_Y);ctx.lineTo(W,MID_Y);ctx.stroke();
  ctx.setLineDash([]);

  // Stop lines
  ctx.strokeStyle='rgba(255,255,255,0.9)';ctx.lineWidth=4;
  ctx.beginPath();ctx.moveTo(roadL,roadT-STOP_SETBACK);ctx.lineTo(roadR,roadT-STOP_SETBACK);ctx.stroke();
  ctx.beginPath();ctx.moveTo(roadL,roadB+STOP_SETBACK);ctx.lineTo(roadR,roadB+STOP_SETBACK);ctx.stroke();
  ctx.beginPath();ctx.moveTo(roadR+STOP_SETBACK,roadT);ctx.lineTo(roadR+STOP_SETBACK,roadB);ctx.stroke();
  ctx.beginPath();ctx.moveTo(roadL-STOP_SETBACK,roadT);ctx.lineTo(roadL-STOP_SETBACK,roadB);ctx.stroke();

  // Zebra crossings - crisp
  ctx.fillStyle='rgba(255,255,255,0.72)';
  for(var zi=0;zi<7;zi++){
    ctx.fillRect(roadL+4,roadT-STOP_SETBACK-16-zi*11,roadR-roadL-8,6);
    ctx.fillRect(roadL+4,roadB+STOP_SETBACK+10+zi*11,roadR-roadL-8,6);
    ctx.fillRect(roadR+STOP_SETBACK+10+zi*11,roadT+4,6,roadB-roadT-8);
    ctx.fillRect(roadL-STOP_SETBACK-16-zi*11,roadT+4,6,roadB-roadT-8);
  }

  // Trees - realistic top-down canopy look
  var treePts=[
    [roadL-35,roadT-60],[roadL-35,roadT-160],[roadL-35,roadT-260],
    [roadL-35,roadB+60],[roadL-35,roadB+160],[roadL-35,roadB+260],
    [roadR+35,roadT-60],[roadR+35,roadT-160],[roadR+35,roadT-260],
    [roadR+35,roadB+60],[roadR+35,roadB+160],[roadR+35,roadB+260],
    [roadL-60,roadT-35],[roadL-160,roadT-35],[roadL-260,roadT-35],
    [roadR+60,roadT-35],[roadR+160,roadT-35],[roadR+260,roadT-35],
    [roadL-60,roadB+35],[roadL-160,roadB+35],[roadL-260,roadB+35],
    [roadR+60,roadB+35],[roadR+160,roadB+35],[roadR+260,roadB+35],
  ];
  treePts.forEach(function(tp){
    var tx=tp[0],ty=tp[1],tr=14+R()*6;
    // Shadow
    ctx.beginPath();ctx.arc(tx+4,ty+4,tr,0,Math.PI*2);
    ctx.fillStyle='rgba(0,0,0,0.35)';ctx.fill();
    // Outer canopy
    ctx.beginPath();ctx.arc(tx,ty,tr,0,Math.PI*2);
    var tg=ctx.createRadialGradient(tx-3,ty-3,0,tx,ty,tr);
    tg.addColorStop(0,'rgba('+(55+R()*20|0)+','+(85+R()*25|0)+','+(28+R()*15|0)+',0.97)');
    tg.addColorStop(0.6,'rgba('+(38+R()*15|0)+','+(65+R()*20|0)+','+(18+R()*10|0)+',0.92)');
    tg.addColorStop(1,'rgba(20,35,10,0.5)');
    ctx.fillStyle=tg;ctx.fill();
    // Inner highlight
    ctx.beginPath();ctx.arc(tx-tr*0.28,ty-tr*0.28,tr*0.38,0,Math.PI*2);
    ctx.fillStyle='rgba(120,180,60,0.22)';ctx.fill();
  });

  // Direction labels
  ctx.fillStyle='rgba(255,255,255,0.45)';
  ctx.font='bold 13px JetBrains Mono';ctx.textAlign='center';ctx.textBaseline='middle';
  ctx.fillText('N',MID_X,14);ctx.fillText('S',MID_X,H-14);
  ctx.textAlign='left';ctx.fillText('W',5,MID_Y);
  ctx.textAlign='right';ctx.fillText('E',W-5,MID_Y);
  ctx.textBaseline='alphabetic';
}

function drawRoadOverlay(ctx,laneData,sig_) {
  ctx.save();ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,ctx.canvas.width,ctx.canvas.height);ctx.restore();
  var MAX_Q=270;
  laneData.forEach(function(l) { var frac=Math.min(l.queue/Math.max(l.capacity,1),1);var len=Math.round(frac*MAX_Q);if(len<1)return;var a=0.14+frac*0.32;var col=frac>0.75?'rgba(229,83,75,'+a+')':frac>0.45?'rgba(212,168,75,'+a+')':'rgba(62,207,142,'+a+')';ctx.fillStyle=col;var def=LDEFS[l.name];if(!def)return;var bw=LW-4;if(def.dir==='S')ctx.fillRect(def.cx-bw/2,RT-len,bw,len);else if(def.dir==='N')ctx.fillRect(def.cx-bw/2,RB,bw,len);else if(def.dir==='W')ctx.fillRect(RR,def.cy-bw/2,len,bw);else if(def.dir==='E')ctx.fillRect(RL-len,def.cy-bw/2,len,bw); });
  drawPoleCtx(ctx,RL-24,RT-26,'NS',sig_);drawPoleCtx(ctx,RR+10,RT-26,'EW',sig_);drawPoleCtx(ctx,RL-24,RB+10,'EW',sig_);drawPoleCtx(ctx,RR+10,RB+10,'NS',sig_);
}

/* Booth hint */
var _boothHover=false;
function drawBoothHint(hover) {
  var cv=document.getElementById('booth-hint-canvas');if(!cv)return;
  var c=cv.getContext('2d');c.save();c.setTransform(1,0,0,1,0,0);c.clearRect(0,0,cv.width,cv.height);c.restore();
  c.save();c.setTransform(DPR,0,0,DPR,0,0);
  var bx=MID,by=MID;
  var grad=c.createRadialGradient(bx,by,0,bx,by,32);grad.addColorStop(0,hover?'rgba(212,168,75,0.4)':'rgba(212,168,75,0.18)');grad.addColorStop(1,'rgba(212,168,75,0)');
  c.fillStyle=grad;c.beginPath();c.arc(bx,by,32,0,Math.PI*2);c.fill();
  c.fillStyle=hover?'rgba(212,168,75,0.6)':'rgba(212,168,75,0.3)';c.strokeStyle=hover?'rgba(212,168,75,0.95)':'rgba(212,168,75,0.55)';c.lineWidth=1.5;
  rrect(c,bx-9,by-11,18,22,3);c.fill();c.stroke();
  c.fillStyle=hover?'rgba(212,168,75,0.85)':'rgba(212,168,75,0.55)';
  c.beginPath();c.moveTo(bx-12,by-11);c.lineTo(bx,by-18);c.lineTo(bx+12,by-11);c.closePath();c.fill();
  c.fillStyle='rgba(100,200,255,0.65)';c.fillRect(bx-4,by-8,8,6);
  if(!hover){c.strokeStyle='rgba(212,168,75,'+(0.2+0.15*Math.sin(Date.now()/600))+')';c.lineWidth=1;c.beginPath();c.arc(bx,by,22,0,Math.PI*2);c.stroke();}
  c.restore();
}
function animateBoothHint(){drawBoothHint(_boothHover);requestAnimationFrame(animateBoothHint);}
animateBoothHint();

var _mapWrap=document.getElementById('map-canvas-wrap');
function mapPixelToSZ(px,py){var rect=_mapWrap.getBoundingClientRect();var scaleX=SZ/rect.width,scaleY=SZ/rect.height;return{x:(px-rect.left)*scaleX,y:(py-rect.top)*scaleY};}
function isNearBooth(px,py){var pos=mapPixelToSZ(px,py);var dx=pos.x-MID,dy=pos.y-MID;return Math.sqrt(dx*dx+dy*dy)<24;}
_mapWrap.addEventListener('mousemove',function(e){var near=isNearBooth(e.clientX,e.clientY);if(near!==_boothHover){_boothHover=near;_mapWrap.style.cursor=near?'pointer':'default';}var tt=document.getElementById('booth-tooltip');if(tt)tt.classList.toggle('show',near);});
_mapWrap.addEventListener('mouseleave',function(){_boothHover=false;_mapWrap.style.cursor='default';var tt=document.getElementById('booth-tooltip');if(tt)tt.classList.remove('show');});
_mapWrap.addEventListener('click',function(e){if(isNearBooth(e.clientX,e.clientY))openBabylon();});

var SAT_CV=document.getElementById('sat-canvas');var RC=document.getElementById('road-canvas'),CC=document.getElementById('car-canvas');
var BH_CV=document.getElementById('booth-hint-canvas');
var SAT_X=SAT_CV.getContext('2d');var RX=RC.getContext('2d');var CX=CC.getContext('2d');
[SAT_CV,RC,CC,BH_CV].forEach(function(cv){cv.width=SZ*DPR;cv.height=SZ*DPR;cv.style.width='100%';cv.style.height='100%';});
SAT_X.scale(DPR,DPR);RX.scale(DPR,DPR);CX.scale(DPR,DPR);
var _laneData=[];
function drawInlineSat(){SAT_X.save();drawSatelliteMap(SAT_X,SZ,SZ);SAT_X.restore();}
drawInlineSat();
function redrawRoad(){RX.save();RX.setTransform(DPR,0,0,DPR,0,0);drawRoadOverlay(RX,_laneData,sigState);RX.restore();}
redrawRoad();

var lastTs=0;
function animate(ts) {
  var raw=ts-lastTs;lastTs=ts;var dt=Math.min(raw/16.67,3);updateVehicles(dt);
  CX.save();CX.setTransform(DPR,0,0,DPR,0,0);CX.clearRect(0,0,SZ,SZ);
  if(crashFlash>0){CX.fillStyle='rgba(229,83,75,'+(crashFlash/12*0.28)+')';CX.fillRect(RL,RT,ROAD,ROAD);}
  LANE_NAMES.forEach(function(ln){LQUEUES[ln].forEach(function(car){drawVehicle(CX,ln,car);});});
  drawCrashParticles(CX);CX.restore();
  updateVolBars();requestAnimationFrame(animate);
}
requestAnimationFrame(animate);

function drawCrashParticles(c){crashEvents.forEach(function(ev){var r=12+ev.t*20;c.save();c.globalAlpha=(1-ev.t)*0.8;c.strokeStyle='#e5534b';c.lineWidth=2;c.beginPath();c.arc(ev.x,ev.y,r,0,Math.PI*2);c.stroke();c.globalAlpha=(1-ev.t)*0.4;c.fillStyle='#e5534b';c.beginPath();c.arc(ev.x,ev.y,r*0.3,0,Math.PI*2);c.fill();c.restore();});}

function updateSignals(phase) {
  var ns=phase==='NS_GREEN'||phase==='NS_MINOR',ew=phase==='EW_GREEN';sigState={N:ns,S:ns,E:ew,W:ew};
  ['N','S'].forEach(function(d){var e=document.getElementById('lamp-'+d);if(e)e.className='lamp '+(ns?'green':'red');});
  ['E','W'].forEach(function(d){var e=document.getElementById('lamp-'+d);if(e)e.className='lamp '+(ew?'green':'red');});
  redrawRoad();updateBabylonTrafficLights(phase);
}
redrawRoad();

/* ═══════════════════════════════════════════════════════════════════════
   BABYLON.JS 3D ENGINE
═══════════════════════════════════════════════════════════════════════ */
var _babEngine=null,_babScene=null,_babCamera=null;
var _babCarMeshes=[];
var _babTLMeshes={N:null,S:null,E:null,W:null};
var _babBuilt=false;
var _babCamMode='ground';
var _babCinematicAngle=0;

const BAB_SCALE=12/ROAD;
function sz2bab(x,y){return{x:(x-MID)*BAB_SCALE,z:(y-MID)*BAB_SCALE};}

/* ── Stable per-car colour lookup so cars never flicker ── */
var _carColorMap={};
var _CAR_PALETTE=[
  new BABYLON.Color3(0.85,0.15,0.15),
  new BABYLON.Color3(0.12,0.38,0.72),
  new BABYLON.Color3(0.88,0.88,0.88),
  new BABYLON.Color3(0.06,0.06,0.07),
  new BABYLON.Color3(0.92,0.72,0.12),
  new BABYLON.Color3(0.18,0.52,0.24),
  new BABYLON.Color3(0.55,0.25,0.62),
  new BABYLON.Color3(0.92,0.42,0.10),
  new BABYLON.Color3(0.28,0.56,0.78),
  new BABYLON.Color3(0.70,0.70,0.68),
  new BABYLON.Color3(0.48,0.18,0.10),
  new BABYLON.Color3(0.82,0.82,0.20),
];
function _stableCarColor(ln,idx){
  var key=ln+'_'+idx;
  if(!_carColorMap[key]){
    var h=0;for(var k=0;k<key.length;k++)h=(h*31+key.charCodeAt(k))>>>0;
    _carColorMap[key]=_CAR_PALETTE[h%_CAR_PALETTE.length];
  }
  return _carColorMap[key];
}

function buildBabylonScene() {
  var canvas = document.getElementById('babylonCanvas');
  _babEngine = new BABYLON.Engine(canvas, true, {
    preserveDrawingBuffer: true, stencil: true, antialias: true
  });
  _babScene = new BABYLON.Scene(_babEngine);
  _babScene.clearColor = new BABYLON.Color4(0.38, 0.52, 0.74, 1);

  _babScene.fogMode = BABYLON.Scene.FOGMODE_EXP2;
  _babScene.fogColor = new BABYLON.Color3(0.58, 0.70, 0.88);
  _babScene.fogDensity = 0.008;

  // Camera
  _babCamera = new BABYLON.UniversalCamera('cam', new BABYLON.Vector3(0, 1.7, 10), _babScene);
  _babCamera.setTarget(new BABYLON.Vector3(0, 1.2, 0));
  _babCamera.fov = 1.05; _babCamera.minZ = 0.1; _babCamera.maxZ = 800;
  _babCamera.speed = 0.35; _babCamera.angularSensibility = 700;
  _babCamera.keysUp = [87]; _babCamera.keysDown = [83];
  _babCamera.keysLeft = [65]; _babCamera.keysRight = [68];
  _babCamera.attachControl(canvas, true);

  // Sky sphere
  var skySphere = BABYLON.MeshBuilder.CreateSphere('sky', { diameter: 700, segments: 8 }, _babScene);
  var skyMatS = new BABYLON.StandardMaterial('skyS', _babScene);
  skyMatS.backFaceCulling = false;
  skyMatS.disableLighting = true;
  skyMatS.diffuseColor = new BABYLON.Color3(0.40, 0.58, 0.88);
  skyMatS.emissiveColor = new BABYLON.Color3(0.40, 0.58, 0.88);
  skySphere.material = skyMatS;
  skySphere.infiniteDistance = true;

  // Sun disc
  var sunDisc = BABYLON.MeshBuilder.CreateSphere('sun', { diameter: 12, segments: 8 }, _babScene);
  var sunMat = new BABYLON.StandardMaterial('sunMat', _babScene);
  sunMat.emissiveColor = new BABYLON.Color3(1.0, 0.97, 0.82);
  sunMat.disableLighting = true;
  sunDisc.material = sunMat;
  sunDisc.position = new BABYLON.Vector3(-120, 90, -200);
  sunDisc.infiniteDistance = true;

  // Haze
  var hazeMat = new BABYLON.StandardMaterial('haze', _babScene);
  hazeMat.diffuseColor = new BABYLON.Color3(0.85, 0.78, 0.60);
  hazeMat.emissiveColor = new BABYLON.Color3(0.62, 0.54, 0.34);
  hazeMat.alpha = 0.18;
  hazeMat.backFaceCulling = false;
  var hazeSphere = BABYLON.MeshBuilder.CreateSphere('hazeS', { diameter: 680, segments: 6 }, _babScene);
  hazeSphere.material = hazeMat;
  hazeSphere.infiniteDistance = true;

  // Lighting
  var hemi = new BABYLON.HemisphericLight('hemi', new BABYLON.Vector3(0, 1, 0), _babScene);
  hemi.intensity = 0.65;
  hemi.groundColor = new BABYLON.Color3(0.35, 0.30, 0.22);
  hemi.diffuse = new BABYLON.Color3(0.75, 0.82, 0.98);
  hemi.specular = new BABYLON.Color3(0.08, 0.08, 0.08);

  var sun = new BABYLON.DirectionalLight('sun', new BABYLON.Vector3(-0.55, -1, -0.45), _babScene);
  sun.intensity = 2.8;
  sun.diffuse = new BABYLON.Color3(1.0, 0.96, 0.84);
  sun.specular = new BABYLON.Color3(1.0, 0.92, 0.72);

  var shadowGen = new BABYLON.ShadowGenerator(4096, sun);
  shadowGen.useBlurExponentialShadowMap = true;
  shadowGen.blurKernel = 32;
  shadowGen.normalBias = 0.015;
  shadowGen.darkness = 0.35;

  var fill = new BABYLON.DirectionalLight('fill', new BABYLON.Vector3(0.5, -0.4, 0.6), _babScene);
  fill.intensity = 0.55;
  fill.diffuse = new BABYLON.Color3(0.50, 0.62, 0.92);

  var bounce = new BABYLON.HemisphericLight('bounce', new BABYLON.Vector3(0, -1, 0), _babScene);
  bounce.intensity = 0.18;
  bounce.diffuse = new BABYLON.Color3(0.65, 0.55, 0.38);

  buildRoadGeometry(_babScene, shadowGen);
  buildBuildings(_babScene, shadowGen);
  buildTrees(_babScene, shadowGen);
  buildTrafficLights(_babScene, shadowGen);
  buildStreetFurniture(_babScene, shadowGen);
  buildDistantCity(_babScene);
  buildCarMeshPool(_babScene, shadowGen);
  buildDustParticles(_babScene);
  buildClouds(_babScene);

  _babEngine.runRenderLoop(function() {
    if (!_babScene) return;
    updateBabylonCars();
    if (_babCamMode === 'cinematic') animateCinematic();
    _babScene.render();
    if (_babCamera) {
      var cx = _babCamera.position.x;
      var cz = _babCamera.position.z;
      var cy = _babCamera.position.y;
      var lat = (12.9716 + cz * 0.000009).toFixed(6);
      var lon = (77.5946 + cx * 0.000009).toFixed(6);
      var alt = Math.max(0, cy).toFixed(1);
      var coordEl = document.getElementById('bab-coords');
      if (coordEl) {
        coordEl.textContent = 'LAT ' + lat + '\u00b0 N \u00b7 LON ' + lon + '\u00b0 E \u00b7 ALT ' + alt + 'm';
      }
    }
  });
  window.addEventListener('resize', function() { if (_babEngine) _babEngine.resize(); });
  _babBuilt = true;
  setTimeout(function() {
    var ld = document.getElementById('bab-loading');
    if (ld) ld.classList.add('done');
  }, 600);
}

function buildRoadGeometry(scene, shadowGen) {
  var ground = BABYLON.MeshBuilder.CreateGround('ground', { width: 600, height: 600, subdivisions: 4 }, scene);
  var groundMat = new BABYLON.StandardMaterial('groundMat', scene);
  groundMat.diffuseColor = new BABYLON.Color3(0.32, 0.28, 0.20);
  groundMat.specularColor = new BABYLON.Color3(0, 0, 0);
  ground.material = groundMat;
  ground.receiveShadows = true;

  var grassMat = new BABYLON.StandardMaterial('grassMat', scene);
  grassMat.diffuseColor = new BABYLON.Color3(0.22, 0.36, 0.14);
  grassMat.specularColor = new BABYLON.Color3(0, 0, 0);
  [[-20, 0, -20], [20, 0, -20], [-20, 0, 20], [20, 0, 20]].forEach(function(p, pi) {
    var g = BABYLON.MeshBuilder.CreateGround('grass' + pi, { width: 22, height: 22, subdivisions: 2 }, scene);
    g.position = new BABYLON.Vector3(p[0], 0.01, p[2]);
    var gm = grassMat.clone('gm' + pi);
    gm.diffuseColor = new BABYLON.Color3(0.20 + Math.random() * 0.06, 0.34 + Math.random() * 0.06, 0.12 + Math.random() * 0.05);
    g.material = gm;
    g.receiveShadows = true;
  });

  var paveMat = new BABYLON.StandardMaterial('paveMat', scene);
  paveMat.diffuseColor = new BABYLON.Color3(0.68, 0.65, 0.58);
  paveMat.specularColor = new BABYLON.Color3(0.05, 0.05, 0.05);
  var paveZones = [
    { x: -9.5, z: -20, w: 2.5, d: 30 }, { x: 9.5, z: -20, w: 2.5, d: 30 },
    { x: -9.5, z: 20, w: 2.5, d: 30 }, { x: 9.5, z: 20, w: 2.5, d: 30 },
    { x: -20, z: -9.5, w: 30, d: 2.5 }, { x: -20, z: 9.5, w: 30, d: 2.5 },
    { x: 20, z: -9.5, w: 30, d: 2.5 }, { x: 20, z: 9.5, w: 30, d: 2.5 },
  ];
  paveZones.forEach(function(pz, pi) {
    var pav = BABYLON.MeshBuilder.CreateBox('pave' + pi, { width: pz.w, height: 0.18, depth: pz.d }, scene);
    pav.position = new BABYLON.Vector3(pz.x, 0.09, pz.z);
    pav.material = paveMat;
    pav.receiveShadows = true;
  });

  var kerbMat = new BABYLON.StandardMaterial('kerbMat', scene);
  kerbMat.diffuseColor = new BABYLON.Color3(0.80, 0.78, 0.72);
  kerbMat.specularColor = new BABYLON.Color3(0.12, 0.12, 0.10);
  [
    { w: 0.28, h: 0.22, d: 30, x: -8.2, z: 0 },
    { w: 0.28, h: 0.22, d: 30, x: 8.2, z: 0 },
    { w: 30, h: 0.22, d: 0.28, x: 0, z: -8.2 },
    { w: 30, h: 0.22, d: 0.28, x: 0, z: 8.2 },
  ].forEach(function(k, ki) {
    var kb = BABYLON.MeshBuilder.CreateBox('kerb' + ki, { width: k.w, height: k.h, depth: k.d }, scene);
    kb.position = new BABYLON.Vector3(k.x, 0.11, k.z);
    kb.material = kerbMat;
    kb.receiveShadows = true;
    shadowGen.addShadowCaster(kb);
  });

  var roadMat = new BABYLON.StandardMaterial('roadMat', scene);
  roadMat.diffuseColor = new BABYLON.Color3(0.16, 0.16, 0.18);
  roadMat.specularColor = new BABYLON.Color3(0.08, 0.08, 0.08);
  roadMat.specularPower = 60;
  var roadNS = BABYLON.MeshBuilder.CreateBox('roadNS', { width: 12, height: 0.20, depth: 120 }, scene);
  roadNS.position = new BABYLON.Vector3(0, 0.10, 0);
  roadNS.material = roadMat;
  roadNS.receiveShadows = true;
  var roadEW = BABYLON.MeshBuilder.CreateBox('roadEW', { width: 120, height: 0.20, depth: 12 }, scene);
  roadEW.position = new BABYLON.Vector3(0, 0.10, 0);
  roadEW.material = roadMat;
  roadEW.receiveShadows = true;

  var interMat = new BABYLON.StandardMaterial('interMat', scene);
  interMat.diffuseColor = new BABYLON.Color3(0.19, 0.19, 0.21);
  interMat.specularColor = new BABYLON.Color3(0.06, 0.06, 0.06);
  var inter = BABYLON.MeshBuilder.CreateBox('inter', { width: 12, height: 0.22, depth: 12 }, scene);
  inter.position = new BABYLON.Vector3(0, 0.11, 0);
  inter.material = interMat;
  inter.receiveShadows = true;

  var dashMat = new BABYLON.StandardMaterial('dashMat', scene);
  dashMat.diffuseColor = new BABYLON.Color3(0.95, 0.92, 0.72);
  dashMat.emissiveColor = new BABYLON.Color3(0.18, 0.16, 0.08);
  for (var di = -8; di <= 8; di++) {
    if (Math.abs(di) < 1) continue;
    var dv = BABYLON.MeshBuilder.CreateBox('dv' + di, { width: 0.10, height: 0.01, depth: 2.5 }, scene);
    dv.position = new BABYLON.Vector3(0, 0.215, di * 4.8);
    dv.material = dashMat;
    var dh = BABYLON.MeshBuilder.CreateBox('dh' + di, { width: 2.5, height: 0.01, depth: 0.10 }, scene);
    dh.position = new BABYLON.Vector3(di * 4.8, 0.215, 0);
    dh.material = dashMat;
  }

  var stopMat = new BABYLON.StandardMaterial('stopMat', scene);
  stopMat.diffuseColor = new BABYLON.Color3(0.94, 0.92, 0.85);
  stopMat.emissiveColor = new BABYLON.Color3(0.22, 0.20, 0.14);
  [[0, 0.215, -7.8], [0, 0.215, 7.8]].forEach(function(p, pi) {
    var sl = BABYLON.MeshBuilder.CreateBox('stop' + pi, { width: 12, height: 0.01, depth: 0.35 }, scene);
    sl.position = new BABYLON.Vector3(p[0], p[1], p[2]);
    sl.material = stopMat;
  });
  [[-7.8, 0.215, 0], [7.8, 0.215, 0]].forEach(function(p, pi) {
    var sl = BABYLON.MeshBuilder.CreateBox('stop2' + pi, { width: 0.35, height: 0.01, depth: 12 }, scene);
    sl.position = new BABYLON.Vector3(p[0], p[1], p[2]);
    sl.material = stopMat;
  });

  var zebraMat = new BABYLON.StandardMaterial('zebraMat', scene);
  zebraMat.diffuseColor = new BABYLON.Color3(0.88, 0.88, 0.82);
  zebraMat.emissiveColor = new BABYLON.Color3(0.14, 0.14, 0.10);
  for (var zi = 0; zi < 9; zi++) {
    var zx = BABYLON.MeshBuilder.CreateBox('zx' + zi, { width: 11.4, height: 0.01, depth: 0.55 }, scene);
    zx.position = new BABYLON.Vector3(0, 0.215, -8.8 - zi * 0.85);
    zx.material = zebraMat;
    var zy = BABYLON.MeshBuilder.CreateBox('zy' + zi, { width: 0.55, height: 0.01, depth: 11.4 }, scene);
    zy.position = new BABYLON.Vector3(-8.8 - zi * 0.85, 0.215, 0);
    zy.material = zebraMat;
    var zx2 = BABYLON.MeshBuilder.CreateBox('zx2' + zi, { width: 11.4, height: 0.01, depth: 0.55 }, scene);
    zx2.position = new BABYLON.Vector3(0, 0.215, 8.8 + zi * 0.85);
    zx2.material = zebraMat;
    var zy2 = BABYLON.MeshBuilder.CreateBox('zy2' + zi, { width: 0.55, height: 0.01, depth: 11.4 }, scene);
    zy2.position = new BABYLON.Vector3(8.8 + zi * 0.85, 0.215, 0);
    zy2.material = zebraMat;
  }

  var reflMat = new BABYLON.StandardMaterial('reflMat', scene);
  reflMat.diffuseColor = new BABYLON.Color3(0.9, 0.8, 0.1);
  reflMat.emissiveColor = new BABYLON.Color3(0.5, 0.42, 0.0);
  [-40, -30, -20, -10, 10, 20, 30, 40].forEach(function(z, ri) {
    [[-6.5, 0, z], [6.5, 0, z], [z, 0, -6.5], [z, 0, 6.5]].forEach(function(rp, rpi) {
      var r = BABYLON.MeshBuilder.CreateBox('refl' + ri + '_' + rpi, { width: 0.16, height: 0.05, depth: 0.16 }, scene);
      r.position = new BABYLON.Vector3(rp[0], 0.215, rp[2]);
      r.material = reflMat;
    });
  });

  var manholeMat = new BABYLON.StandardMaterial('manholeMat', scene);
  manholeMat.diffuseColor = new BABYLON.Color3(0.25, 0.25, 0.27);
  manholeMat.specularColor = new BABYLON.Color3(0.35, 0.35, 0.35);
  [[-3, 0, -3], [3, 0, 3], [-3, 0, 20], [3, 0, -20]].forEach(function(mp, mi) {
    var mh = BABYLON.MeshBuilder.CreateCylinder('mh' + mi, { height: 0.02, diameter: 0.65, tessellation: 16 }, scene);
    mh.position = new BABYLON.Vector3(mp[0], 0.215, mp[2]);
    mh.material = manholeMat;
  });
}


function buildBuildings(scene, shadowGen) {
  var configs = [
    { x: -18, z: -18, w: 9, d: 8, h: 4.5, style: 'shop' },
    { x: 18, z: -18, w: 8, d: 9, h: 4.5, style: 'shop' },
    { x: -18, z: 18, w: 9, d: 8, h: 4.5, style: 'shop' },
    { x: 18, z: 18, w: 8, d: 9, h: 4.5, style: 'shop' },
    { x: -28, z: -24, w: 16, d: 12, h: 28, style: 'office' },
    { x: -24, z: -32, w: 10, d: 10, h: 44, style: 'glass' },
    { x: 28, z: -24, w: 14, d: 14, h: 32, style: 'office' },
    { x: 26, z: -32, w: 9, d: 9, h: 52, style: 'glass' },
    { x: -28, z: 24, w: 15, d: 11, h: 26, style: 'office' },
    { x: -24, z: 32, w: 10, d: 9, h: 36, style: 'brick' },
    { x: 28, z: 24, w: 16, d: 12, h: 30, style: 'office' },
    { x: 26, z: 32, w: 9, d: 10, h: 56, style: 'glass' },
    { x: -55, z: -48, w: 24, d: 20, h: 70, style: 'glass' },
    { x: 55, z: -48, w: 20, d: 24, h: 82, style: 'glass' },
    { x: -55, z: 48, w: 22, d: 18, h: 62, style: 'office' },
    { x: 55, z: 48, w: 18, d: 22, h: 90, style: 'glass' },
    { x: 0, z: -72, w: 30, d: 20, h: 55, style: 'office' },
    { x: 0, z: 72, w: 26, d: 22, h: 65, style: 'glass' },
    { x: -82, z: 0, w: 22, d: 30, h: 50, style: 'brick' },
    { x: 82, z: 0, w: 20, d: 28, h: 75, style: 'glass' },
    { x: -42, z: -14, w: 11, d: 10, h: 38, style: 'office' },
    { x: 42, z: -14, w: 10, d: 11, h: 46, style: 'glass' },
    { x: -42, z: 14, w: 11, d: 10, h: 34, style: 'brick' },
    { x: 42, z: 14, w: 10, d: 11, h: 42, style: 'office' },
    { x: -68, z: -28, w: 14, d: 12, h: 30, style: 'brick' },
    { x: 68, z: -28, w: 12, d: 14, h: 40, style: 'glass' },
    { x: -68, z: 28, w: 14, d: 12, h: 28, style: 'office' },
    { x: 68, z: 28, w: 12, d: 14, h: 38, style: 'glass' },
    { x: -110, z: -60, w: 30, d: 25, h: 95, style: 'glass' },
    { x: 110, z: -60, w: 28, d: 28, h: 110, style: 'glass' },
    { x: -110, z: 60, w: 30, d: 25, h: 80, style: 'glass' },
    { x: 110, z: 60, w: 28, d: 28, h: 100, style: 'glass' },
    { x: -40, z: -100, w: 35, d: 22, h: 72, style: 'office' },
    { x: 40, z: -100, w: 32, d: 25, h: 88, style: 'glass' },
    { x: -40, z: 100, w: 35, d: 22, h: 68, style: 'office' },
    { x: 40, z: 100, w: 32, d: 25, h: 84, style: 'glass' },
  ];

  var styleColors = {
    shop: [
      new BABYLON.Color3(0.72, 0.54, 0.36),
      new BABYLON.Color3(0.65, 0.48, 0.30),
      new BABYLON.Color3(0.76, 0.60, 0.42),
    ],
    office: [
      new BABYLON.Color3(0.30, 0.32, 0.36),
      new BABYLON.Color3(0.26, 0.28, 0.33),
      new BABYLON.Color3(0.34, 0.36, 0.40),
    ],
    glass: [
      new BABYLON.Color3(0.20, 0.30, 0.45),
      new BABYLON.Color3(0.16, 0.26, 0.40),
      new BABYLON.Color3(0.24, 0.34, 0.50),
      new BABYLON.Color3(0.18, 0.28, 0.42),
    ],
    brick: [
      new BABYLON.Color3(0.55, 0.32, 0.20),
      new BABYLON.Color3(0.48, 0.28, 0.16),
      new BABYLON.Color3(0.62, 0.38, 0.24),
    ],
  };

  var winLitMat = new BABYLON.StandardMaterial('winLit', scene);
  winLitMat.diffuseColor = new BABYLON.Color3(0.10, 0.12, 0.14);
  winLitMat.emissiveColor = new BABYLON.Color3(0.75, 0.68, 0.42);

  var winOffMat = new BABYLON.StandardMaterial('winOff', scene);
  winOffMat.diffuseColor = new BABYLON.Color3(0.08, 0.12, 0.18);
  winOffMat.emissiveColor = new BABYLON.Color3(0.02, 0.04, 0.08);

  var winGlassDayMat = new BABYLON.StandardMaterial('winGlassDay', scene);
  winGlassDayMat.diffuseColor = new BABYLON.Color3(0.45, 0.62, 0.80);
  winGlassDayMat.emissiveColor = new BABYLON.Color3(0.10, 0.22, 0.38);
  winGlassDayMat.specularColor = new BABYLON.Color3(0.8, 0.9, 1.0);
  winGlassDayMat.specularPower = 120;
  winGlassDayMat.alpha = 0.85;
  winGlassDayMat.backFaceCulling = false;

  configs.forEach(function(bc, idx) {
    var cols = styleColors[bc.style] || styleColors.office;
    var baseCol = cols[idx % cols.length].clone();
    baseCol.r += (Math.random() - 0.5) * 0.06;
    baseCol.g += (Math.random() - 0.5) * 0.06;
    baseCol.b += (Math.random() - 0.5) * 0.06;

    var bMat = new BABYLON.StandardMaterial('bm' + idx, scene);
    bMat.diffuseColor = baseCol;
    bMat.specularColor = bc.style === 'glass'
      ? new BABYLON.Color3(0.4, 0.5, 0.6)
      : new BABYLON.Color3(0.08, 0.08, 0.10);
    bMat.specularPower = bc.style === 'glass' ? 80 : 30;

    var bld = BABYLON.MeshBuilder.CreateBox('bld' + idx, { width: bc.w, height: bc.h, depth: bc.d }, scene);
    bld.position = new BABYLON.Vector3(bc.x, bc.h / 2, bc.z);
    bld.material = bMat;
    bld.receiveShadows = true;
    shadowGen.addShadowCaster(bld);

    var roofMat = bMat.clone('rf' + idx);
    roofMat.diffuseColor = new BABYLON.Color3(
      baseCol.r * 0.60, baseCol.g * 0.60, baseCol.b * 0.60);
    var roof = BABYLON.MeshBuilder.CreateBox('rf' + idx, { width: bc.w + 0.5, height: 0.7, depth: bc.d + 0.5 }, scene);
    roof.position = new BABYLON.Vector3(bc.x, bc.h + 0.35, bc.z);
    roof.material = roofMat;
    shadowGen.addShadowCaster(roof);

    if (bc.h > 20) {
      var hvacMat = new BABYLON.StandardMaterial('hvac' + idx, scene);
      hvacMat.diffuseColor = new BABYLON.Color3(0.38, 0.38, 0.40);
      var hvac = BABYLON.MeshBuilder.CreateBox('hvac' + idx, { width: bc.w * 0.28, height: 1.5, depth: bc.d * 0.28 }, scene);
      hvac.position = new BABYLON.Vector3(bc.x + bc.w * 0.18, bc.h + 1.1, bc.z + bc.d * 0.18);
      hvac.material = hvacMat;
      shadowGen.addShadowCaster(hvac);

      if (bc.h > 50) {
        var antMat = new BABYLON.StandardMaterial('ant' + idx, scene);
        antMat.diffuseColor = new BABYLON.Color3(0.55, 0.55, 0.58);
        antMat.emissiveColor = new BABYLON.Color3(0.05, 0.05, 0.06);
        var ant = BABYLON.MeshBuilder.CreateCylinder('ant' + idx,
          { height: bc.h * 0.22, diameterTop: 0.06, diameterBottom: 0.18, tessellation: 8 }, scene);
        ant.position = new BABYLON.Vector3(bc.x, bc.h + bc.h * 0.11 + 0.7, bc.z);
        ant.material = antMat;
        shadowGen.addShadowCaster(ant);

        var blinkMat = new BABYLON.StandardMaterial('blink' + idx, scene);
        blinkMat.diffuseColor = new BABYLON.Color3(0.8, 0.05, 0.05);
        blinkMat.emissiveColor = new BABYLON.Color3(1.0, 0.0, 0.0);
        var blink = BABYLON.MeshBuilder.CreateSphere('blink' + idx, { diameter: 0.30, segments: 6 }, scene);
        blink.position = new BABYLON.Vector3(bc.x, bc.h + bc.h * 0.22 + 0.9, bc.z);
        blink.material = blinkMat;
        var blinkLight = new BABYLON.PointLight('blinkL' + idx,
          new BABYLON.Vector3(bc.x, bc.h + bc.h * 0.22 + 0.9, bc.z), scene);
        blinkLight.diffuse = new BABYLON.Color3(1, 0, 0);
        blinkLight.intensity = 0; blinkLight.range = 6;
        // FIX 3: capture blinkT and blinkMat/blinkLight per-building in a closure
        // to prevent all blink callbacks sharing the same blinkT variable
        // (the original let all antennas blink in sync because blinkT was
        // overwritten each iteration and all closures referenced the same binding).
        (function(bMat_, bLight_) {
          var blinkT_ = Math.random() * Math.PI * 2;
          scene.registerBeforeRender(function() {
            blinkT_ += 0.04;
            var on = Math.sin(blinkT_) > 0.6;
            bLight_.intensity = on ? 1.5 : 0;
            bMat_.emissiveColor = on ? new BABYLON.Color3(1, 0, 0) : new BABYLON.Color3(0.2, 0, 0);
          });
        })(blinkMat, blinkLight);
      }
    }

    // FIX 3 continued: wCols/wRows were declared with var inside configs.forEach,
    // so they leaked across iterations (var hoisting). Renamed to wC/wR to be
    // explicit that each building gets its own loop variables.
    if (bc.style === 'glass') {
      var wC = Math.max(3, Math.floor(bc.w / 1.6));
      var wR = Math.max(4, Math.floor(bc.h / 2.0));
      for (var wr = 0; wr < wR; wr++) {
        for (var wc = 0; wc < wC; wc++) {
          var lit = Math.random() > 0.22;
          var gw = BABYLON.MeshBuilder.CreateBox('gw' + idx + wr + '_' + wc,
            { width: (bc.w / wC) * 0.82, height: 1.55, depth: 0.04 }, scene);
          gw.position = new BABYLON.Vector3(
            bc.x - bc.w / 2 + (wc + 0.5) * (bc.w / wC),
            1.8 + wr * (bc.h / wR),
            bc.z + bc.d / 2 + 0.05);
          gw.material = lit ? winGlassDayMat : winOffMat;
        }
      }
    } else {
      var wC = Math.max(2, Math.floor(bc.w / 2.2));
      var wR = Math.max(2, Math.floor(bc.h / 3.0));
      for (var wr = 0; wr < wR; wr++) {
        for (var wc = 0; wc < wC; wc++) {
          var lit = Math.random() > 0.30;
          var win = BABYLON.MeshBuilder.CreateBox('w' + idx + wr + '_' + wc,
            { width: 0.65, height: 0.85, depth: 0.05 }, scene);
          win.position = new BABYLON.Vector3(
            bc.x - bc.w / 2 + (wc + 0.5) * (bc.w / wC),
            1.8 + wr * (bc.h / wR),
            bc.z + bc.d / 2 + 0.05);
          win.material = lit ? winLitMat : winOffMat;
        }
      }
    }
  });
}


function buildTrees(scene, shadowGen) {
  var trunkMat = new BABYLON.StandardMaterial('trunkMat', scene);
  trunkMat.diffuseColor = new BABYLON.Color3(0.28, 0.17, 0.08);
  trunkMat.specularColor = new BABYLON.Color3(0.02, 0.01, 0.01);

  var treePosns = [
    { x: -9.2, z: -24, h: 6.0, r: 1.6 }, { x: -9.2, z: -16, h: 6.5, r: 1.7 },
    { x: -9.2, z: -8, h: 5.8, r: 1.5 }, { x: -9.2, z: 8, h: 6.2, r: 1.6 },
    { x: -9.2, z: 16, h: 6.0, r: 1.7 }, { x: -9.2, z: 24, h: 6.8, r: 1.8 },
    { x: 9.2, z: -24, h: 6.2, r: 1.6 }, { x: 9.2, z: -16, h: 5.8, r: 1.5 },
    { x: 9.2, z: -8, h: 6.5, r: 1.7 }, { x: 9.2, z: 8, h: 6.0, r: 1.6 },
    { x: 9.2, z: 16, h: 6.4, r: 1.7 }, { x: 9.2, z: 24, h: 5.8, r: 1.5 },
    { x: -24, z: -9.2, h: 6.0, r: 1.6 }, { x: -16, z: -9.2, h: 6.5, r: 1.7 },
    { x: -8, z: -9.2, h: 5.8, r: 1.5 }, { x: 8, z: -9.2, h: 6.2, r: 1.6 },
    { x: 16, z: -9.2, h: 6.0, r: 1.7 }, { x: 24, z: -9.2, h: 6.8, r: 1.8 },
    { x: -24, z: 9.2, h: 6.2, r: 1.6 }, { x: -16, z: 9.2, h: 5.8, r: 1.5 },
    { x: -8, z: 9.2, h: 6.5, r: 1.7 }, { x: 8, z: 9.2, h: 6.0, r: 1.6 },
    { x: 16, z: 9.2, h: 6.4, r: 1.7 }, { x: 24, z: 9.2, h: 5.8, r: 1.5 },
    { x: -34, z: -34, h: 8.0, r: 2.4 }, { x: -30, z: -40, h: 7.5, r: 2.2 },
    { x: -40, z: -30, h: 7.8, r: 2.3 },
    { x: 34, z: -34, h: 7.8, r: 2.3 }, { x: 30, z: -40, h: 8.2, r: 2.4 },
    { x: 40, z: -30, h: 7.5, r: 2.2 },
    { x: -34, z: 34, h: 8.0, r: 2.4 }, { x: -30, z: 40, h: 7.5, r: 2.2 },
    { x: -40, z: 30, h: 7.8, r: 2.3 },
    { x: 34, z: 34, h: 7.8, r: 2.3 }, { x: 30, z: 40, h: 8.2, r: 2.4 },
    { x: 40, z: 30, h: 7.5, r: 2.2 },
  ];

  var leafVariants = [
    [new BABYLON.Color3(0.15, 0.44, 0.12), new BABYLON.Color3(0.20, 0.50, 0.16), new BABYLON.Color3(0.12, 0.36, 0.08)],
    [new BABYLON.Color3(0.22, 0.50, 0.18), new BABYLON.Color3(0.26, 0.56, 0.20), new BABYLON.Color3(0.18, 0.42, 0.14)],
    [new BABYLON.Color3(0.28, 0.46, 0.16), new BABYLON.Color3(0.32, 0.52, 0.20), new BABYLON.Color3(0.24, 0.40, 0.12)],
    [new BABYLON.Color3(0.18, 0.52, 0.22), new BABYLON.Color3(0.22, 0.58, 0.26), new BABYLON.Color3(0.14, 0.44, 0.18)],
  ];

  treePosns.forEach(function(tp, ti) {
    var trunk = BABYLON.MeshBuilder.CreateCylinder('tr' + ti,
      { height: tp.h * 0.40, diameterTop: 0.12, diameterBottom: 0.26, tessellation: 10 }, scene);
    trunk.position = new BABYLON.Vector3(tp.x, tp.h * 0.20, tp.z);
    trunk.material = trunkMat;
    trunk.receiveShadows = true;
    shadowGen.addShadowCaster(trunk);

    var variant = leafVariants[ti % leafVariants.length];

    for (var li = 0; li < 4; li++) {
      var leafMat = new BABYLON.StandardMaterial('lm' + ti + '_' + li, scene);
      leafMat.diffuseColor = variant[li % 3].clone();
      leafMat.diffuseColor.r += (Math.random() - 0.5) * 0.06;
      leafMat.diffuseColor.g += (Math.random() - 0.5) * 0.06;
      leafMat.specularColor = new BABYLON.Color3(0.02, 0.05, 0.01);
      var sz = tp.r * (0.55 + li * 0.18) * 2.0;
      var leaf = BABYLON.MeshBuilder.CreateSphere('leaf' + ti + '_' + li, { diameter: sz, segments: 8 }, scene);
      var ox = (li < 2 ? (li === 0 ? -1 : 1) : (li === 2 ? -0.4 : 0.4)) * tp.r * 0.52;
      var oz = (li < 2 ? 0.2 : -0.4) * tp.r * 0.45;
      var oy = tp.h * 0.42 + tp.h * 0.28 + li * 0.5;
      leaf.position = new BABYLON.Vector3(tp.x + ox, oy, tp.z + oz);
      leaf.material = leafMat;
      shadowGen.addShadowCaster(leaf);
      leaf.receiveShadows = true;
    }
  });
}

function buildTrafficLights(scene,shadowGen) {
  var poleMat=new BABYLON.StandardMaterial('poleMat',scene);
  poleMat.diffuseColor=new BABYLON.Color3(0.18,0.18,0.20);
  poleMat.specularColor=new BABYLON.Color3(0.35,0.35,0.35);
  poleMat.specularPower=90;

  var tl_positions=[
    {dir:'N',x:-6.5,z:-7.2,ry:0},
    {dir:'S',x: 6.5,z:  7.2,ry:Math.PI},
    {dir:'E',x: 7.2,z:-6.5,ry:-Math.PI/2},
    {dir:'W',x:-7.2,z: 6.5,ry: Math.PI/2}
  ];
  tl_positions.forEach(function(tp){
    var pole=BABYLON.MeshBuilder.CreateCylinder('pole_'+tp.dir,
      {height:6.0,diameter:0.16,tessellation:10},scene);
    pole.position=new BABYLON.Vector3(tp.x,3.0,tp.z);
    pole.material=poleMat;shadowGen.addShadowCaster(pole);

    var arm=BABYLON.MeshBuilder.CreateCylinder('arm_'+tp.dir,
      {height:1.2,diameter:0.10,tessellation:8},scene);
    arm.rotation.z=Math.PI/2;
    arm.position=new BABYLON.Vector3(tp.x,6.0,tp.z);
    arm.material=poleMat;

    var housingMat=new BABYLON.StandardMaterial('hm_'+tp.dir,scene);
    housingMat.diffuseColor=new BABYLON.Color3(0.08,0.09,0.10);
    housingMat.specularColor=new BABYLON.Color3(0.15,0.15,0.15);
    var housing=BABYLON.MeshBuilder.CreateBox('h_'+tp.dir,
      {width:0.50,height:1.40,depth:0.50},scene);
    housing.position=new BABYLON.Vector3(tp.x,5.5,tp.z);
    housing.rotation.y=tp.ry;housing.material=housingMat;shadowGen.addShadowCaster(housing);

    var visorMat=housingMat.clone('vis_'+tp.dir);
    visorMat.diffuseColor=new BABYLON.Color3(0.06,0.06,0.07);
    var visor=BABYLON.MeshBuilder.CreateBox('vis_'+tp.dir,{width:0.56,height:0.12,depth:0.30},scene);
    visor.position=new BABYLON.Vector3(tp.x,6.26,tp.z+(tp.ry===0?0.22:tp.ry===Math.PI?-0.22:0));
    visor.rotation.y=tp.ry;visor.material=visorMat;

    var redMat=new BABYLON.StandardMaterial('rm_'+tp.dir,scene);
    redMat.diffuseColor=new BABYLON.Color3(0.45,0.04,0.04);
    redMat.emissiveColor=new BABYLON.Color3(0,0,0);
    var faceZ=tp.ry===0?0.26:tp.ry===Math.PI?-0.26:0;
    var faceX=tp.ry===-Math.PI/2?0.26:tp.ry===Math.PI/2?-0.26:0;
    var redL=BABYLON.MeshBuilder.CreateSphere('rl_'+tp.dir,{diameter:0.28,segments:10},scene);
    redL.position=new BABYLON.Vector3(tp.x+faceX,5.85,tp.z+faceZ);redL.material=redMat;

    var amberMat=new BABYLON.StandardMaterial('am_'+tp.dir,scene);
    amberMat.diffuseColor=new BABYLON.Color3(0.45,0.28,0.02);
    amberMat.emissiveColor=new BABYLON.Color3(0,0,0);
    var amberL=BABYLON.MeshBuilder.CreateSphere('al_'+tp.dir,{diameter:0.28,segments:10},scene);
    amberL.position=new BABYLON.Vector3(tp.x+faceX,5.50,tp.z+faceZ);amberL.material=amberMat;

    var greenMat=new BABYLON.StandardMaterial('gm_'+tp.dir,scene);
    greenMat.diffuseColor=new BABYLON.Color3(0.04,0.38,0.10);
    greenMat.emissiveColor=new BABYLON.Color3(0,0,0);
    var greenL=BABYLON.MeshBuilder.CreateSphere('gl_'+tp.dir,{diameter:0.28,segments:10},scene);
    greenL.position=new BABYLON.Vector3(tp.x+faceX,5.15,tp.z+faceZ);greenL.material=greenMat;

    var tlGlow=new BABYLON.PointLight('glw_'+tp.dir,
      new BABYLON.Vector3(tp.x+faceX,5.15,tp.z+faceZ),scene);
    tlGlow.diffuse=new BABYLON.Color3(0.2,1.0,0.4);
    tlGlow.intensity=0;tlGlow.range=8;

    // FIX 4: _babTLMeshes was being assigned inside the forEach loop but the
    // direction key used tp.dir correctly — however redMat/greenMat/amberMat
    // were declared with var so they were function-scoped and the last
    // iteration's values would bleed into closure captures.  Wrapping the
    // assignment in the loop body (already closure-safe via forEach) is fine,
    // but we must ensure we assign after all materials are created for this
    // direction, which the original already did.  No change needed there.
    _babTLMeshes[tp.dir]={redMat:redMat,greenMat:greenMat,amberMat:amberMat,glow:tlGlow};
  });
}

function buildStreetFurniture(scene,shadowGen) {
  var metalMat=new BABYLON.StandardMaterial('metalMat',scene);
  metalMat.diffuseColor=new BABYLON.Color3(0.28,0.29,0.32);
  metalMat.specularColor=new BABYLON.Color3(0.45,0.45,0.45);
  metalMat.specularPower=100;

  var lampPositions=[
    {x:-8.6,z:-20},{x:-8.6,z:-8},{x:-8.6,z:8},{x:-8.6,z:20},
    {x: 8.6,z:-20},{x: 8.6,z:-8},{x: 8.6,z:8},{x: 8.6,z:20},
    {x:-20,z:-8.6},{x:-8,z:-8.6},{x: 8,z:-8.6},{x:20,z:-8.6},
    {x:-20,z: 8.6},{x:-8,z: 8.6},{x: 8,z: 8.6},{x:20,z: 8.6},
  ];

  lampPositions.forEach(function(lp,li){
    var lpole=BABYLON.MeshBuilder.CreateCylinder('lp'+li,
      {height:7.0,diameterTop:0.08,diameterBottom:0.14,tessellation:8},scene);
    lpole.position=new BABYLON.Vector3(lp.x,3.5,lp.z);lpole.material=metalMat;
    shadowGen.addShadowCaster(lpole);

    var larm=BABYLON.MeshBuilder.CreateCylinder('la'+li,
      {height:0.9,diameter:0.07,tessellation:7},scene);
    larm.rotation.z=Math.PI/2;
    larm.position=new BABYLON.Vector3(lp.x+(lp.x>0?0.4:-0.4),7.0,lp.z+(lp.z>0?0.4:-0.4));
    larm.material=metalMat;

    var lhMat=new BABYLON.StandardMaterial('lhm'+li,scene);
    lhMat.diffuseColor=new BABYLON.Color3(0.25,0.25,0.22);
    lhMat.emissiveColor=new BABYLON.Color3(0.0,0.0,0.0);
    var lhead=BABYLON.MeshBuilder.CreateBox('lh'+li,{width:0.55,height:0.20,depth:0.30},scene);
    lhead.position=new BABYLON.Vector3(lp.x+(lp.x>0?0.4:-0.4),7.15,lp.z+(lp.z>0?0.4:-0.4));
    lhead.material=lhMat;

    var lensMat=new BABYLON.StandardMaterial('lens'+li,scene);
    lensMat.diffuseColor=new BABYLON.Color3(1.0,0.96,0.80);
    lensMat.emissiveColor=new BABYLON.Color3(0.90,0.82,0.45);
    var lens=BABYLON.MeshBuilder.CreateBox('lens'+li,{width:0.38,height:0.08,depth:0.22},scene);
    lens.position=new BABYLON.Vector3(lp.x+(lp.x>0?0.4:-0.4),7.05,lp.z+(lp.z>0?0.4:-0.4));
    lens.material=lensMat;

    var ll=new BABYLON.PointLight('ll'+li,
      new BABYLON.Vector3(lp.x+(lp.x>0?0.4:-0.4),6.8,lp.z+(lp.z>0?0.4:-0.4)),scene);
    ll.diffuse=new BABYLON.Color3(1.0,0.95,0.72);
    ll.intensity=0.6;ll.range=18;
  });

  var bollardMat=new BABYLON.StandardMaterial('bollardMat',scene);
  bollardMat.diffuseColor=new BABYLON.Color3(0.12,0.12,0.13);
  bollardMat.specularColor=new BABYLON.Color3(0.20,0.20,0.20);
  var bandMat=new BABYLON.StandardMaterial('bandMat',scene);
  bandMat.diffuseColor=new BABYLON.Color3(0.90,0.72,0.05);
  bandMat.emissiveColor=new BABYLON.Color3(0.18,0.14,0.0);

  [[-7.0,-9.2],[7.0,-9.2],[-7.0,9.2],[7.0,9.2],
   [-9.2,-7.0],[-9.2,7.0],[9.2,-7.0],[9.2,7.0]].forEach(function(bp,bi){
    var bolt=BABYLON.MeshBuilder.CreateCylinder('bolt'+bi,
      {height:0.85,diameterTop:0.14,diameterBottom:0.18,tessellation:9},scene);
    bolt.position=new BABYLON.Vector3(bp[0],0.42,bp[1]);bolt.material=bollardMat;
    var band=BABYLON.MeshBuilder.CreateCylinder('band'+bi,
      {height:0.10,diameterTop:0.16,diameterBottom:0.16,tessellation:9},scene);
    band.position=new BABYLON.Vector3(bp[0],0.65,bp[1]);band.material=bandMat;
  });

  var shelterMat=new BABYLON.StandardMaterial('shelterMat',scene);
  shelterMat.diffuseColor=new BABYLON.Color3(0.75,0.78,0.82);
  shelterMat.alpha=0.70;shelterMat.backFaceCulling=false;
  var shelterFrame=new BABYLON.StandardMaterial('shelterFrame',scene);
  shelterFrame.diffuseColor=new BABYLON.Color3(0.25,0.26,0.30);
  shelterFrame.specularColor=new BABYLON.Color3(0.5,0.5,0.5);
  var sw=BABYLON.MeshBuilder.CreateBox('sw',{width:3.0,height:2.4,depth:0.08},scene);
  sw.position=new BABYLON.Vector3(-11.5,1.2,-9.8);sw.material=shelterMat;
  var sr=BABYLON.MeshBuilder.CreateBox('sr',{width:3.2,height:0.10,depth:1.2},scene);
  sr.position=new BABYLON.Vector3(-11.5,2.4,-9.4);sr.material=shelterFrame;
  var sp1=BABYLON.MeshBuilder.CreateBox('sp1',{width:0.08,height:2.4,depth:0.08},scene);
  sp1.position=new BABYLON.Vector3(-13.0,1.2,-9.4);sp1.material=shelterFrame;
  var sp2=BABYLON.MeshBuilder.CreateBox('sp2',{width:0.08,height:2.4,depth:0.08},scene);
  sp2.position=new BABYLON.Vector3(-10.0,1.2,-9.4);sp2.material=shelterFrame;

  var sigBoxMat=new BABYLON.StandardMaterial('sigBoxMat',scene);
  sigBoxMat.diffuseColor=new BABYLON.Color3(0.18,0.18,0.20);
  [[-7.2,-7.8],[7.2,7.8],[-7.8,-7.2],[7.8,7.2]].forEach(function(pb,pbi){
    var pb2=BABYLON.MeshBuilder.CreateBox('pb'+pbi,{width:0.22,height:0.38,depth:0.14},scene);
    pb2.position=new BABYLON.Vector3(pb[0],1.2,pb[1]);pb2.material=sigBoxMat;
  });
}
function buildDistantCity(scene) {
  // Distant skyline backdrop — very far, low detail, pure silhouette
  var silMat = new BABYLON.StandardMaterial('silMat', scene);
  silMat.diffuseColor = new BABYLON.Color3(0.22, 0.28, 0.38);
  silMat.emissiveColor = new BABYLON.Color3(0.10, 0.14, 0.22);
  silMat.specularColor = new BABYLON.Color3(0, 0, 0);

  var silMat2 = silMat.clone('silMat2');
  silMat2.diffuseColor = new BABYLON.Color3(0.18, 0.24, 0.34);
  silMat2.emissiveColor = new BABYLON.Color3(0.08, 0.12, 0.20);

  // Ring of distant towers on all sides
  var distBuildings = [
    { x: -180, z: -150, w: 40, d: 30, h: 140 },
    { x: -140, z: -180, w: 35, d: 28, h: 110 },
    { x: 180, z: -150, w: 38, d: 32, h: 160 },
    { x: 150, z: -185, w: 30, d: 25, h: 120 },
    { x: -180, z: 150, w: 40, d: 30, h: 130 },
    { x: -145, z: 185, w: 32, d: 26, h: 105 },
    { x: 180, z: 150, w: 38, d: 32, h: 155 },
    { x: 150, z: 185, w: 28, d: 24, h: 118 },
    { x: 0, z: -200, w: 50, d: 35, h: 145 },
    { x: 0, z: 200, w: 48, d: 32, h: 138 },
    { x: -210, z: 0, w: 35, d: 50, h: 125 },
    { x: 210, z: 0, w: 32, d: 48, h: 148 },
    { x: -220, z: -80, w: 30, d: 28, h: 90 },
    { x: 220, z: 80, w: 28, d: 30, h: 95 },
    { x: 80, z: -220, w: 28, d: 30, h: 105 },
    { x: -80, z: 220, w: 30, d: 28, h: 98 },
  ];

  distBuildings.forEach(function(db, di) {
    var bld = BABYLON.MeshBuilder.CreateBox('distB' + di,
      { width: db.w, height: db.h, depth: db.d }, scene);
    bld.position = new BABYLON.Vector3(db.x, db.h / 2, db.z);
    bld.material = di % 2 === 0 ? silMat : silMat2;

    // Random lit windows as emissive dots on distant buildings
    var winCount = Math.floor(db.w / 6) * Math.floor(db.h / 8);
    for (var wi = 0; wi < Math.min(winCount, 20); wi++) {
      if (Math.random() > 0.5) continue;
      var wm = new BABYLON.StandardMaterial('dw' + di + wi, scene);
      wm.emissiveColor = Math.random() > 0.3
        ? new BABYLON.Color3(0.8, 0.72, 0.42)
        : new BABYLON.Color3(0.4, 0.6, 0.9);
      wm.disableLighting = true;
      var dw = BABYLON.MeshBuilder.CreateBox('dw' + di + '_' + wi,
        { width: 1.5, height: 1.2, depth: 0.1 }, scene);
      dw.position = new BABYLON.Vector3(
        db.x + (Math.random() - 0.5) * db.w * 0.8,
        Math.random() * db.h * 0.85 + 2,
        db.z + db.d / 2 + 0.1);
      dw.material = wm;
    }
  });

  // Ground plane extending far — fade to horizon
  var farGroundMat = new BABYLON.StandardMaterial('farGround', scene);
  farGroundMat.diffuseColor = new BABYLON.Color3(0.20, 0.22, 0.18);
  farGroundMat.specularColor = new BABYLON.Color3(0, 0, 0);
  var farGround = BABYLON.MeshBuilder.CreateGround('farGround',
    { width: 1200, height: 1200, subdivisions: 2 }, scene);
  farGround.position = new BABYLON.Vector3(0, -0.05, 0);
  farGround.material = farGroundMat;
}

function buildClouds(scene) {
  var cloudMat = new BABYLON.StandardMaterial('cloudMat', scene);
  cloudMat.diffuseColor = new BABYLON.Color3(1, 1, 1);
  cloudMat.emissiveColor = new BABYLON.Color3(0.85, 0.88, 0.95);
  cloudMat.alpha = 0.55;
  cloudMat.backFaceCulling = false;
  cloudMat.disableLighting = true;

  var cloudPositions = [
    { x: -80, y: 55, z: -100, sx: 28, sy: 7, sz: 14 },
    { x: 60, y: 62, z: -130, sx: 22, sy: 5, sz: 10 },
    { x: -120, y: 50, z: 80, sx: 32, sy: 8, sz: 16 },
    { x: 100, y: 58, z: 90, sx: 25, sy: 6, sz: 12 },
    { x: 20, y: 65, z: -160, sx: 35, sy: 9, sz: 18 },
    { x: -50, y: 52, z: 140, sx: 20, sy: 5, sz: 10 },
    { x: 140, y: 60, z: -40, sx: 26, sy: 7, sz: 13 },
    { x: -160, y: 55, z: 20, sx: 30, sy: 7, sz: 15 },
  ];

  cloudPositions.forEach(function(cp, ci) {
    // Each cloud = cluster of ellipsoid spheres
    for (var ci2 = 0; ci2 < 4; ci2++) {
      var cloud = BABYLON.MeshBuilder.CreateSphere('cloud' + ci + '_' + ci2,
        { diameter: 1, segments: 5 }, scene);
      cloud.scaling = new BABYLON.Vector3(
        cp.sx * (0.6 + Math.random() * 0.6),
        cp.sy * (0.5 + Math.random() * 0.5),
        cp.sz * (0.5 + Math.random() * 0.5));
      cloud.position = new BABYLON.Vector3(
        cp.x + (Math.random() - 0.5) * cp.sx * 0.8,
        cp.y + (Math.random() - 0.5) * cp.sy,
        cp.z + (Math.random() - 0.5) * cp.sz * 0.8);
      var cm = cloudMat.clone('cm' + ci + ci2);
      cm.alpha = 0.35 + Math.random() * 0.30;
      cloud.material = cm;
      cloud.infiniteDistance = false;

      // FIX 1: wrap in IIFE so each cloud sphere gets its own closed-over
      // cloud reference, driftSpeed, and origX — prevents all 4 spheres in
      // a cloud from sharing the last iteration's values.
      (function(c_, speed_, ox_) {
        scene.registerBeforeRender(function() {
          c_.position.x += speed_;
          if (c_.position.x > ox_ + 40) c_.position.x = ox_ - 40;
        });
      })(cloud, 0.0008 + Math.random() * 0.0006, cloud.position.x);
    }
  });
}

function buildCarMeshPool(scene,shadowGen) {
  /* Build 48 cars — 4 per lane × 12 lanes — each with a FIXED stable colour */
  _babCarMeshes=[];
  LANE_NAMES.forEach(function(ln,li){
    for(var ci=0;ci<4;ci++){
      var col=_stableCarColor(ln,ci);
      var carGroup=buildSingleCar(scene,'car_'+ln+'_'+ci,col);
      shadowGen.addShadowCaster(carGroup.body);
      carGroup.root.setEnabled(false);
      _babCarMeshes.push({mesh:carGroup,lane:ln,slotIdx:ci});
    }
  });
}

function buildSingleCar(scene,name,col) {
  var root=new BABYLON.TransformNode(name+'_root',scene);

  /* body */
  var bodyMat=new BABYLON.StandardMaterial(name+'_body',scene);
  bodyMat.diffuseColor=col.clone();
  bodyMat.specularColor=new BABYLON.Color3(0.75,0.75,0.75);
  bodyMat.specularPower=80;
  var body=BABYLON.MeshBuilder.CreateBox(name+'_b',{width:0.95,height:0.40,depth:1.80},scene);
  body.material=bodyMat;body.position.y=0.30;body.parent=root;

  /* cabin */
  var cabMat=new BABYLON.StandardMaterial(name+'_cab',scene);
  cabMat.diffuseColor=new BABYLON.Color3(col.r*0.80,col.g*0.80,col.b*0.80);
  cabMat.specularColor=new BABYLON.Color3(0.50,0.50,0.50);
  var cab=BABYLON.MeshBuilder.CreateBox(name+'_c',{width:0.82,height:0.32,depth:0.90},scene);
  cab.material=cabMat;cab.position=new BABYLON.Vector3(0,0.61,-0.06);cab.parent=root;

  /* windshield */
  var winMat=new BABYLON.StandardMaterial(name+'_w',scene);
  winMat.diffuseColor=new BABYLON.Color3(0.50,0.68,0.88);
  winMat.alpha=0.72;winMat.backFaceCulling=false;
  winMat.specularColor=new BABYLON.Color3(0.8,0.8,0.8);winMat.specularPower=120;
  var ws=BABYLON.MeshBuilder.CreateBox(name+'_ws',{width:0.76,height:0.24,depth:0.04},scene);
  ws.material=winMat;ws.position=new BABYLON.Vector3(0,0.63,0.40);ws.parent=root;
  /* rear window */
  var rw=BABYLON.MeshBuilder.CreateBox(name+'_rw',{width:0.72,height:0.22,depth:0.04},scene);
  rw.material=winMat;rw.position=new BABYLON.Vector3(0,0.62,-0.44);rw.parent=root;

  /* side windows */
  var swL=BABYLON.MeshBuilder.CreateBox(name+'_swL',{width:0.04,height:0.20,depth:0.55},scene);
  swL.material=winMat;swL.position=new BABYLON.Vector3(-0.47,0.62,0.04);swL.parent=root;
  var swR=swL.clone(name+'_swR');swR.position=new BABYLON.Vector3(0.47,0.62,0.04);swR.parent=root;

  /* wheels */
  var wheelMat=new BABYLON.StandardMaterial(name+'_wh',scene);
  wheelMat.diffuseColor=new BABYLON.Color3(0.08,0.08,0.09);
  wheelMat.specularColor=new BABYLON.Color3(0.05,0.05,0.05);
  var rimMat=new BABYLON.StandardMaterial(name+'_rim',scene);
  rimMat.diffuseColor=new BABYLON.Color3(0.68,0.68,0.70);
  rimMat.specularColor=new BABYLON.Color3(0.9,0.9,0.9);rimMat.specularPower=120;

  [[-.50,.14,.62],[.50,.14,.62],[-.50,.14,-.62],[.50,.14,-.62]].forEach(function(wp,wi){
    var wheel=BABYLON.MeshBuilder.CreateCylinder(name+'_wheel'+wi,
      {height:0.22,diameter:0.32,tessellation:14},scene);
    wheel.rotation.z=Math.PI/2;
    wheel.position=new BABYLON.Vector3(wp[0],wp[1],wp[2]);
    wheel.material=wheelMat;wheel.parent=root;
    /* rim disc */
    var rim=BABYLON.MeshBuilder.CreateCylinder(name+'_rim'+wi,
      {height:0.04,diameter:0.20,tessellation:14},scene);
    rim.rotation.z=Math.PI/2;
    rim.position=new BABYLON.Vector3(wp[0]+(wp[0]>0?0.12:-0.12),wp[1],wp[2]);
    rim.material=rimMat;rim.parent=root;
  });

  /* headlights */
  var hlMat=new BABYLON.StandardMaterial(name+'_hl',scene);
  hlMat.diffuseColor=new BABYLON.Color3(0.98,0.97,0.92);
  hlMat.emissiveColor=new BABYLON.Color3(0.85,0.82,0.60);
  [[-.30,.30],[.30,.30]].forEach(function(hlp,hli){
    var hl=BABYLON.MeshBuilder.CreateBox(name+'_hl'+hli,{width:0.20,height:0.12,depth:0.05},scene);
    hl.position=new BABYLON.Vector3(hlp[0],hlp[1],0.91);hl.material=hlMat;hl.parent=root;
  });

  /* tail lights */
  var tlMat=new BABYLON.StandardMaterial(name+'_tl',scene);
  tlMat.diffuseColor=new BABYLON.Color3(0.6,0.04,0.04);
  tlMat.emissiveColor=new BABYLON.Color3(0.45,0.02,0.02);
  [[-.30,.30],[.30,.30]].forEach(function(tlp,tli){
    var tl=BABYLON.MeshBuilder.CreateBox(name+'_tl'+tli,{width:0.20,height:0.12,depth:0.05},scene);
    tl.position=new BABYLON.Vector3(tlp[0],tlp[1],-0.91);tl.material=tlMat;tl.parent=root;
  });

  /* licence plate front */
  var plateMat=new BABYLON.StandardMaterial(name+'_plate',scene);
  plateMat.diffuseColor=new BABYLON.Color3(0.92,0.92,0.30);
  plateMat.emissiveColor=new BABYLON.Color3(0.10,0.10,0.02);
  var plate=BABYLON.MeshBuilder.CreateBox(name+'_plate',{width:0.40,height:0.12,depth:0.03},scene);
  plate.position=new BABYLON.Vector3(0,0.22,0.92);plate.material=plateMat;plate.parent=root;

  return{root:root,body:body};
}

function buildDustParticles(scene) {
  try{
    /* exhaust/heat shimmer particles from road */
    var dustPS=new BABYLON.ParticleSystem('dust',300,scene);
    dustPS.emitter=new BABYLON.Vector3(0,0.3,0);
    dustPS.minEmitBox=new BABYLON.Vector3(-25,0,-25);
    dustPS.maxEmitBox=new BABYLON.Vector3(25,0.5,25);
    dustPS.color1=new BABYLON.Color4(0.92,0.88,0.78,0.06);
    dustPS.color2=new BABYLON.Color4(0.82,0.80,0.72,0.02);
    dustPS.colorDead=new BABYLON.Color4(0,0,0,0);
    dustPS.minSize=0.04;dustPS.maxSize=0.22;
    dustPS.minLifeTime=5;dustPS.maxLifeTime=12;
    dustPS.emitRate=25;
    dustPS.gravity=new BABYLON.Vector3(0,0.04,0);
    dustPS.direction1=new BABYLON.Vector3(-0.15,0.12,-0.15);
    dustPS.direction2=new BABYLON.Vector3(0.15,0.20,0.15);
    dustPS.minAngularSpeed=0;dustPS.maxAngularSpeed=Math.PI/6;
    dustPS.minEmitPower=0.04;dustPS.maxEmitPower=0.18;
    dustPS.blendMode=BABYLON.ParticleSystem.BLENDMODE_STANDARD;
    dustPS.start();
  }catch(e){}
}

function updateBabylonCars() {
  const BLAB_LANE_X = {
    N_through:  1.0, N_right:  3.0, N_left:  5.0,
    S_through: -1.0, S_right: -3.0, S_left: -5.0,
  };
  const BLAB_LANE_Z = {
    E_through:  1.0, E_right:  3.0, E_left:  5.0,
    W_through: -1.0, W_right: -3.0, W_left: -5.0,
  };

  const VISIBLE_RANGE = 200;
  const posScale = 28 / VISIBLE_RANGE;

  var laneCarList = {};
  LANE_NAMES.forEach(function(ln) {
    laneCarList[ln] = LQUEUES[ln].filter(function(c) {
      return !c.crashed && !c.exited;
    });
  });

  _babCarMeshes.forEach(function(entry) {
    var ln = entry.lane, slot = entry.slotIdx, mesh = entry.mesh;
    var carsInLane = laneCarList[ln];

    if (slot >= carsInLane.length) {
      mesh.root.setEnabled(false);
      return;
    }

    var car = carsInLane[slot];
    var def = LDEFS[ln];
    var babX, babZ, angle;

    if (def.dir === 'S' || def.dir === 'N') {
      babX = BLAB_LANE_X[ln] || 0;
      babZ = (car.pos - MID) * posScale;
      angle = def.dir === 'S' ? 0 : Math.PI;

      if (Math.abs(babZ) > 32) {
        mesh.root.setEnabled(false);
        return;
      }
    } else {
      babZ = BLAB_LANE_Z[ln] || 0;
      babX = (car.pos - MID) * posScale;
      angle = def.dir === 'E' ? -Math.PI / 2 : Math.PI / 2;

      if (Math.abs(babX) > 32) {
        mesh.root.setEnabled(false);
        return;
      }
    }

    mesh.root.position.x = babX;
    mesh.root.position.y = 0.16;
    mesh.root.position.z = babZ;
    mesh.root.rotation.y = angle;
    mesh.root.setEnabled(true);
  });
}

function updateBabylonTrafficLights(phase) {
  var nsG=phase==='NS_GREEN'||phase==='NS_MINOR', ewG=phase==='EW_GREEN';
  function setTL(dir,isGreen){
    var tl=_babTLMeshes[dir];if(!tl)return;
    if(isGreen){
      tl.redMat.emissiveColor   =new BABYLON.Color3(0.08,0.0,0.0);
      tl.amberMat.emissiveColor =new BABYLON.Color3(0,0,0);
      tl.greenMat.emissiveColor =new BABYLON.Color3(0.0,1.0,0.32);
      tl.glow.diffuse=new BABYLON.Color3(0.2,1.0,0.4);
      tl.glow.intensity=1.8;tl.glow.range=10;
    }else{
      tl.redMat.emissiveColor   =new BABYLON.Color3(1.0,0.05,0.05);
      tl.amberMat.emissiveColor =new BABYLON.Color3(0,0,0);
      tl.greenMat.emissiveColor =new BABYLON.Color3(0.0,0.06,0.02);
      tl.glow.diffuse=new BABYLON.Color3(1.0,0.1,0.1);
      tl.glow.intensity=1.4;tl.glow.range=8;
    }
  }
  setTL('N',nsG);setTL('S',nsG);setTL('E',ewG);setTL('W',ewG);
}

function babSetCam(mode) {
  _babCamMode=mode;
  ['ground','elevated','cinematic','overhead'].forEach(function(m){var b=document.getElementById('bab-cam-'+m);if(b)b.classList.toggle('active',m===mode);});
  if(!_babCamera||!_babScene) return;
  if(mode==='ground'){_babCamera.position=new BABYLON.Vector3(0,1.7,10);_babCamera.setTarget(new BABYLON.Vector3(0,1.4,0));_babCamera.fov=1.1;}
  else if(mode==='elevated'){_babCamera.position=new BABYLON.Vector3(12,8,14);_babCamera.setTarget(new BABYLON.Vector3(0,0,0));_babCamera.fov=0.85;}
  else if(mode==='cinematic'){_babCinematicAngle=0;}
  else if(mode==='overhead'){_babCamera.position=new BABYLON.Vector3(0,40,0.1);_babCamera.setTarget(new BABYLON.Vector3(0,0,0));_babCamera.fov=0.7;}
}
function animateCinematic(){if(!_babCamera)return;_babCinematicAngle+=0.003;var r=18,h=4;_babCamera.position=new BABYLON.Vector3(Math.sin(_babCinematicAngle)*r,h+Math.sin(_babCinematicAngle*0.4)*1.5,Math.cos(_babCinematicAngle)*r);_babCamera.setTarget(new BABYLON.Vector3(0,1.5,0));}

function babForcePhase(phase) {
  forcePhase(phase);
  var nsB=document.getElementById('bab-force-ns'),ewB=document.getElementById('bab-force-ew');
  if(nsB)nsB.classList.toggle('ns-on',phase==='NS_GREEN');
  if(ewB)ewB.classList.toggle('ew-on',phase==='EW_GREEN');
}

function openBabylon() {
  var overlay=document.getElementById('babylon-overlay');overlay.classList.add('open');
  requestAnimationFrame(function(){requestAnimationFrame(function(){overlay.classList.add('visible');
    setTimeout(function(){
      if(!_babBuilt){buildBabylonScene();}else{if(_babEngine)_babEngine.resize();}
      var phase=sigState.N?'NS_GREEN':sigState.E?'EW_GREEN':'ALL_RED';updateBabylonTrafficLights(phase);log('3D Ground View opened','ok');
    },80);
  });});
}
function closeBabylon(){var overlay=document.getElementById('babylon-overlay');overlay.classList.remove('visible');setTimeout(function(){overlay.classList.remove('open');},400);}

function syncBabylonHUD(info) {
  if(!info) return;_liveInfo=info;
  var st=function(id,v){var e=document.getElementById(id);if(e)e.textContent=v;};
  var phase=info.phase||'NS_GREEN';
  st('bab-phase',phase);st('bab-wait',(info.avg_delay||0).toFixed(1)+'s');
  st('bab-thru',(info.total_cleared||0)+' veh');st('bab-avgwait',(info.avg_delay||0).toFixed(1)+'s');
  st('bab-ns2',Math.round(info.ns_queue||0)+' veh');st('bab-ew2',Math.round(info.ew_queue||0)+' veh');
  st('bab-los',info.los||'—');
  var pp=document.getElementById('bab-phase-pill');if(pp){pp.className='bab-phase-pill ph-'+phase;pp.textContent=phase;}
}

/* ═══════════════════════════════════════════════════════════════════════
   CHART HELPERS
═══════════════════════════════════════════════════════════════════════ */
function updateRing(score) { if(score===null||isNaN(score))return;var t=Math.max(0,Math.min(1,score)),arc=213.6;var el=document.getElementById('score-ring');el.style.strokeDasharray=(t*arc)+' '+(arc-t*arc);el.style.stroke=t<0.4?'var(--red)':t<0.65?'var(--sand)':'var(--green)';document.getElementById('ring-val').textContent=(score*100).toFixed(0)+'%'; }
var LOS_DESC={A:'Free flow — <=10s',B:'Stable — <=20s',C:'Acceptable — <=35s',D:'Near unstable — <=55s',E:'Unstable — <=80s',F:'Breakdown — >80s'};
function updateLOS(l) { if(!l)return;'ABCDEF'.split('').forEach(function(g){var el=document.getElementById('los-'+g);if(el)el.classList.toggle('active',g===l);});document.getElementById('kpi-los').textContent=l;document.getElementById('kpi-los').style.color=l==='A'?'var(--green)':l==='B'?'#5ec4a0':l==='C'?'#b8c44a':l==='D'?'var(--sand)':l==='E'?'#e08840':'var(--red)';document.getElementById('kpi-los-sub').textContent=LOS_DESC[l]||'';document.getElementById('los-tag').textContent='LOS '+l; }
function drawSparkline() { var canvas=document.getElementById('spark-canvas');if(!canvas||!canvas.offsetWidth)return;var dpr=window.devicePixelRatio||1,W=canvas.offsetWidth,H=canvas.offsetHeight||60;canvas.width=W*dpr;canvas.height=H*dpr;var c=canvas.getContext('2d');c.scale(dpr,dpr);c.clearRect(0,0,W,H);c.fillStyle='#242938';c.fillRect(0,0,W,H);var ns=nsHist.slice(-MAX_H),ew=ewHist.slice(-MAX_H);var all=ns.concat(ew);if(all.length<2)return;var maxV=Math.max.apply(null,all.concat([1])),px=3,py=4,iW=W-px*2,iH=H-py*2;var tx=function(i,len){return px+(i/Math.max(len-1,1))*iW;},ty=function(v){return py+iH-(v/maxV)*iH;};function series(data,col){if(data.length<2)return;c.beginPath();data.forEach(function(v,i){if(i===0)c.moveTo(tx(i,data.length),ty(v));else c.lineTo(tx(i,data.length),ty(v));});c.strokeStyle=col;c.lineWidth=1.5;c.lineJoin='round';c.stroke();c.beginPath();c.arc(tx(data.length-1,data.length),ty(data[data.length-1]),3,0,Math.PI*2);c.fillStyle=col;c.fill();}series(ew,'#d4a84b');series(ns,'#3ecf8e');document.getElementById('spark-latest').textContent='NS:'+(ns[ns.length-1]||0).toFixed(0)+' EW:'+(ew[ew.length-1]||0).toFixed(0)+' veh'; }
function drawTrendChart(id,data,color) { var canvas=document.getElementById(id);if(!canvas||!canvas.offsetWidth)return;var dpr=window.devicePixelRatio||1,W=canvas.offsetWidth,H=canvas.offsetHeight||54;canvas.width=W*dpr;canvas.height=H*dpr;var c=canvas.getContext('2d');c.scale(dpr,dpr);c.clearRect(0,0,W,H);c.fillStyle='#1a1f2c';c.fillRect(0,0,W,H);if(data.length<2)return;var maxV=Math.max.apply(null,data.concat([0.001])),minV=Math.min.apply(null,data.concat([0]));var range=maxV-minV||1;var px=2,py=4,iW=W-px*2,iH=H-py*2;var tx=function(i){return px+(i/Math.max(data.length-1,1))*iW;},ty=function(v){return py+iH-((v-minV)/range)*iH;};c.beginPath();data.forEach(function(v,i){if(i===0)c.moveTo(tx(i),ty(v));else c.lineTo(tx(i),ty(v));});c.lineTo(tx(data.length-1),H);c.lineTo(tx(0),H);c.closePath();var g=c.createLinearGradient(0,0,0,H);g.addColorStop(0,color+'33');g.addColorStop(1,color+'00');c.fillStyle=g;c.fill();c.beginPath();data.forEach(function(v,i){if(i===0)c.moveTo(tx(i),ty(v));else c.lineTo(tx(i),ty(v));});c.strokeStyle=color;c.lineWidth=1.5;c.lineJoin='round';c.stroke(); }
function drawAllTrendCharts() { drawTrendChart('trend-delay-canvas',trendDelayHist,'#e5534b');drawTrendChart('trend-thru-canvas',trendThruHist,'#3ecf8e');drawTrendChart('trend-queue-canvas',trendQueueHist,'#d4a84b'); }
function pushTrendData(delay,thru,queue) { trendDelayHist.push(delay);trendThruHist.push(thru);trendQueueHist.push(queue);if(trendDelayHist.length>TREND_MAX){trendDelayHist.shift();trendThruHist.shift();trendQueueHist.shift();}var st=function(id,v){var e=document.getElementById(id);if(e)e.textContent=v;};st('trend-delay-val',delay.toFixed(1)+'s');st('trend-thru-val',thru.toFixed(1)+' v/s');st('trend-queue-val',Math.round(queue)+' veh');drawAllTrendCharts(); }

function updateDecisionPanel(info) {
  if(!info)return;var phase=info.phase||'NS_GREEN';
  var decTag=document.getElementById('dec-phase-tag');if(decTag){decTag.className='phase-tag ph-'+phase;decTag.textContent=phase;}
  var nsQ=Math.round(info.ns_queue||0),ewQ=Math.round(info.ew_queue||0);
  var isNS=phase==='NS_GREEN'||phase==='NS_MINOR',isEW=phase==='EW_GREEN',isRed=phase==='ALL_RED';
  var reasons=[];
  if(opMode==='rl'&&DQN.lastQVals){
    var actionNames=['HOLD','SWITCH','EXTEND'];var bestA=0;for(var i=1;i<3;i++)if(DQN.lastQVals[i]>DQN.lastQVals[bestA])bestA=i;
    reasons.push({dot:'purple',text:'DQN chose: '+actionNames[bestA]+' (Q='+DQN.lastQVals[bestA].toFixed(2)+')'});
    reasons.push({dot:'purple',text:'ε='+DQN.EPSILON.toFixed(3)+' · replay='+DQN.replay.length+' · steps='+DQN.totalSteps});
  }
  if(isNS){reasons.push({dot:'green',text:'N/S queue '+nsQ+' veh — granting N/S green'});if(ewQ>0)reasons.push({dot:'sand',text:'E/W holding at '+ewQ+' veh'});}
  else if(isEW){reasons.push({dot:'green',text:'E/W queue '+ewQ+' veh — granting E/W green'});if(nsQ>0)reasons.push({dot:'sand',text:'N/S holding at '+nsQ+' veh'});}
  else if(isRed){reasons.push({dot:'red',text:'All-red clearance — purging intersection'});}
  if((info.avg_delay||0)>0)reasons.push({dot:'blue',text:'Avg wait: '+(info.avg_delay||0).toFixed(1)+'s'});
  var listEl=document.getElementById('dec-reason-list');if(listEl)listEl.innerHTML=reasons.map(function(r){return'<div class="decision-reason"><div class="decision-reason-dot '+r.dot+'"></div><span>'+r.text+'</span></div>';}).join('');
  var gainEl=document.getElementById('dec-gain');if(gainEl)gainEl.textContent=(isNS?nsQ:ewQ)>0?'+'+Math.min(Math.round((isNS?nsQ:ewQ)*0.15),20)+'%':'—';
}

function updateSaturation(lanes){['N','S','E','W'].forEach(function(dir){var dl=lanes.filter(function(l){return l.name[0]===dir;});if(!dl.length)return;var sat=Math.min(dl.reduce(function(s,l){return s+l.queue;},0)/dl.reduce(function(s,l){return s+Math.max(l.capacity,1);},0),1);var pct=(sat*100).toFixed(0);var fe=document.getElementById('sat-'+dir),ve=document.getElementById('satv-'+dir);if(fe){fe.style.width=pct+'%';fe.style.background=sat>0.75?'var(--red)':sat>0.45?'var(--sand)':'var(--green)';}if(ve)ve.textContent=pct+'%';});}
function updateSummaryCard(info){if(!info||_episodeFrozen)return;var st=function(id,v){var e=document.getElementById(id);if(e)e.textContent=v;};var arrived=info.total_arrived||0,cleared=info.total_cleared||0;st('sum-total',cleared.toLocaleString());st('sum-total-sub',arrived.toLocaleString()+' arrived / '+cleared.toLocaleString()+' cleared');var delay=info.avg_delay||0;st('sum-delay',delay.toFixed(1)+'s');st('sum-delay-sub',delay<=10?'LOS A — free flow':delay<=35?'LOS B/C — acceptable':'LOS D+ — congested');st('sum-peak',Math.round(info.peak_queue||0)+' veh');st('sum-co2',(info.emission_kg_co2||0).toFixed(3)+' kg');}

function log(msg,type){type=type||'';var box=document.getElementById('log-box');var ts=new Date().toLocaleTimeString('en-GB',{hour12:false});var r=document.createElement('div');r.className='log-row';r.innerHTML='<span class="log-ts">'+ts+'</span><span class="log-msg '+type+'">'+msg+'</span>';box.insertBefore(r,box.firstChild);while(box.children.length>100)box.removeChild(box.lastChild);logN++;document.getElementById('log-count').textContent=logN+' entries';}
function gradeLabel(s){if(s===null||s===undefined)return{stars:'☆☆☆',note:'Not evaluated yet.'};var p=Math.round(s*100);if(p>=80)return{stars:'★★★',note:'Excellent — '+p+'% efficiency'};if(p>=60)return{stars:'★★☆',note:'Good — '+p+'% efficiency'};return{stars:'★☆☆',note:'Needs work — '+p+'%'};}
function flash(id){var e=document.getElementById(id);if(!e)return;e.classList.remove('pop');void e.offsetWidth;e.classList.add('pop');}

/* ═══════════════════════════════════════════════════════════════════════
   API CALLS
═══════════════════════════════════════════════════════════════════════ */
async function doReset() {
  var task=document.getElementById('task-sel').value;var seed=document.getElementById('seed-in').value;var body={task_id:task};if(seed)body.seed=parseInt(seed);
  var r=await fetch(BASE+'/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});var d=await r.json();
  sessionId=d.session_id;horizon=d.horizon||600;nsHist=[];ewHist=[];trendDelayHist=[];trendThruHist=[];trendQueueHist=[];
  _episodeFrozen = false;
  vizScore=0;vizCrashes=0;vizSmooth=0;csGreenPts=0;csRedPts=0;updateVizUI();
  LANE_NAMES.forEach(function(n){LQUEUES[n]=[];});
  document.getElementById('kpi-hor').textContent='of '+horizon+' total';document.getElementById('prog-hor').textContent=horizon;
  document.getElementById('prog-fill').style.width='0%';document.getElementById('prog-step').textContent='0';document.getElementById('kpi-step').textContent='0';
  ['kpi-score','kpi-thru'].forEach(function(id){document.getElementById(id).textContent='—';});
  document.getElementById('kpi-delay').textContent='0.0s';document.getElementById('kpi-score-lbl').textContent='not evaluated';
  document.getElementById('score-stars').textContent='☆☆☆';document.getElementById('score-note').textContent='Run a policy to evaluate.';
  updateRing(0);drawSparkline();drawAllTrendCharts();
  DQN.lastState = null;
  DQN.lastAction = null;
  log('Episode started · '+task+' · '+d.session_id.slice(0,10)+'…','ok');return d;
}
async function doStep(action){if(!sessionId)return null;var r=await fetch(BASE+'/step',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sessionId,action:action})});return r.json();}
async function doGrade() {
  if(!sessionId)return;var r=await fetch(BASE+'/grader',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sessionId})});var d=await r.json();
  var score=d.score!=null?d.score:null;var g=gradeLabel(score);
  if(score!==null){document.getElementById('kpi-score').textContent=(score*100).toFixed(1)+'%';document.getElementById('kpi-score-lbl').textContent=g.note;document.getElementById('score-stars').textContent=g.stars;document.getElementById('score-note').textContent=g.note;document.getElementById('ring-val').textContent=(score*100).toFixed(0)+'%';updateRing(score);flash('kpi-score');var snap=d.analytics_snapshot||{};if(snap.los)updateLOS(snap.los);}
  return d;
}

async function updateUI(sd) {
  if(!sd)return;var step=sd.step||0,info=sd.info||{},phase=info.phase||'NS_GREEN';
  if(_episodeFrozen)return;
  document.getElementById('kpi-step').textContent=step;document.getElementById('prog-step').textContent=step;
  document.getElementById('prog-fill').style.width=(horizon>0?(step/horizon*100).toFixed(1):0)+'%';
  var phCls='phase-tag ph-'+phase;
  ['phase-tag','sig-phase-tag'].forEach(function(id){var e=document.getElementById(id);if(e){e.className=phCls;e.textContent=phase;}});
  document.getElementById('phase-el').textContent='Elapsed '+(info.phase_elapsed||0)+'s';
  document.getElementById('map-tag').textContent='PHASE: '+phase;
  document.getElementById('kpi-thru').textContent=(info.total_cleared||0).toLocaleString();
  document.getElementById('kpi-delay').textContent=(info.avg_delay||0).toFixed(1)+'s';
  if(info.los)updateLOS(info.los);
  if(info.rolling_throughput_rate!==undefined)document.getElementById('dm-rtp').textContent=info.rolling_throughput_rate.toFixed(3)+' v/s';
  if(info.peak_delay!==undefined)document.getElementById('dm-pdly').textContent=info.peak_delay.toFixed(1)+'s';
  if(info.peak_queue!==undefined)document.getElementById('dm-pq').textContent=Math.round(info.peak_queue)+' veh';
  if(info.step_cleared!==undefined)document.getElementById('dm-sc').textContent=info.step_cleared+' veh';
  if(info.efficiency_ratio!==undefined)document.getElementById('dm-eff').textContent=(info.efficiency_ratio*100).toFixed(1)+'%';
  if(info.ns_queue!==undefined)document.getElementById('m-ns').textContent=Math.round(info.ns_queue)+' veh';
  if(info.ew_queue!==undefined)document.getElementById('m-ew').textContent=Math.round(info.ew_queue)+' veh';
  if(info.emission_kg_co2!==undefined)document.getElementById('m-co2').textContent=info.emission_kg_co2.toFixed(3)+' kg';
  if(info.spillback_count!==undefined){document.getElementById('spill-tag').textContent='SPILLBACK: '+info.spillback_count+' lanes';document.getElementById('spill-tag').style.color=info.spillback_count>0?'var(--red)':'var(--text-faint)';}
  updateSummaryCard(info);updateDecisionPanel(info);syncBabylonHUD(info);
  try {
    var sr=await fetch(BASE+'/state?session_id='+sessionId);var st=await sr.json();var lanes=st.lanes||[];_laneData=lanes;
    updateSignals(phase);
    var dirTotals={N:0,S:0,E:0,W:0};
    lanes.forEach(function(l){var dir=l.name[0];dirTotals[dir]=(dirTotals[dir]||0)+l.queue;var pct=Math.min(l.queue_pct||0,100);var frac=pct/100;var pctStr=pct.toFixed(0)+'%';var dirCol=(dir==='N'||dir==='S')?'var(--green)':'var(--sand)';var barCol=frac>0.75?'var(--red)':frac>0.45?'var(--sand)':dirCol;var fill=document.getElementById('lf-'+l.name);if(fill){fill.style.width=pctStr;fill.style.background=barCol;}var pctEl=document.getElementById('lp-'+l.name);if(pctEl)pctEl.textContent=pctStr;var df=document.getElementById('df-'+l.name);if(df){df.style.width=pctStr;df.style.background=barCol;}var dp=document.getElementById('dp-'+l.name);if(dp){dp.textContent=pctStr;dp.style.color=barCol;}});
    ['N','S','E','W'].forEach(function(d){var el=document.getElementById('dt-'+d);if(el)el.textContent=Math.round(dirTotals[d]||0)+' veh';});
    updateSaturation(lanes);
    nsHist.push(st.direction_summary&&st.direction_summary.NS?st.direction_summary.NS.queue:(info.ns_queue||0));
    ewHist.push(st.direction_summary&&st.direction_summary.EW?st.direction_summary.EW.queue:(info.ew_queue||0));
    if(nsHist.length>MAX_H){nsHist.shift();ewHist.shift();}drawSparkline();
    spawnFromLaneData(lanes);pushTrendData(info.avg_delay||0,info.rolling_throughput_rate||0,(info.ns_queue||0)+(info.ew_queue||0));
  } catch(e){}
  if((info.step_cleared||0)>0)spawnCleared(info.step_cleared,phase);
  if(step>0&&step%50===0){await doGrade();var warn=info.los==='F'||info.los==='E'||(info.spillback_count||0)>2;log('Step '+step+' · cleared '+(info.total_cleared||0)+' · wait '+(info.avg_delay||0).toFixed(1)+'s · '+phase+' · LOS '+(info.los||'?'),warn?'warn':'');}
}

/* ═══════════════════════════════════════════════════════════════════════
   POLICY FUNCTIONS
═══════════════════════════════════════════════════════════════════════ */
function pressureAction(obs) {
  if(!obs)return 0;var ql=obs.queue_lengths||[],ph=obs.phase_onehot||[1,0,0,0];
  var pi=ph.indexOf(Math.max.apply(null,ph));var elapsed=(obs.phase_elapsed_norm||0)*90;
  if(elapsed<5)return 0;
  var ns=[0,1,2,3,8,9].reduce(function(s,i){return s+(ql[i]||0);},0);
  var ew=[4,5,6,7,10,11].reduce(function(s,i){return s+(ql[i]||0);},0);
  if(pi===0&&ew-ns>0.3)return 1;if(pi===1&&ns-ew>0.3)return 1;if(pi===2)return 0;
  if(pi===0&&ns>0.75)return 2;if(pi===1&&ew>0.75)return 2;return 0;
}

function dqnPolicy(obs, prevInfo) {
  if (DQN.lastState !== null && prevInfo !== null) {
    var reward = DQN.computeReward(prevInfo, DQN._prevPrevInfo || null);
    DQN.step(obs, reward, false);
  }
  DQN._prevPrevInfo = prevInfo;
  var action = DQN.selectAction(obs);
  return dqnActionToApiAction(action, obs);
}

/* ─ Op mode & control ─ */
var opMode='pressure', simSpeed=1, forcedPhase=null, fixedTimer=0;
var FIXED_CYCLE=30;
var runInterval=null, _lastObs=null, _lastInfo=null;

function setOpMode(mode) {
  opMode=mode;forcedPhase=null;
  ['bab-mode-rl','bab-mode-fixed'].forEach(function(id){var b=document.getElementById(id);if(b)b.classList.toggle('rl-on',id.includes('rl')&&mode==='rl');});
  if(running){if(runInterval){clearInterval(runInterval);runInterval=null;}applySimSpeed();}
}

function forcePhase(phase) {
  if(opMode!=='manual')opMode='manual';forcedPhase=phase;
  updateSignals(phase);document.getElementById('map-tag').textContent='PHASE: '+phase+' [OVERRIDE]';log('Forced: '+phase,'warn');
}

function applySimSpeed() {
  if(runInterval){clearInterval(runInterval);runInterval=null;}if(!running)return;
  var ms=Math.round(120/simSpeed);
  runInterval=setInterval(async function() {
    if(!running||!sessionId)return;
    try{
      var action;
      if(opMode==='rl'){
        action=dqnPolicy(_lastObs, _lastInfo);
      }else if(opMode==='pressure'){
        action=pressureAction(_lastObs);
      }else if(opMode==='manual'){
        action=0;
      }else{
        fixedTimer++;forcedPhase=Math.floor(fixedTimer/FIXED_CYCLE)%2===0?'NS_GREEN':'EW_GREEN';action=0;
      }
      var sd=await doStep(action);if(!sd)return;
      _lastInfo=sd.info||null;
      _lastObs=sd.observation;
      if(forcedPhase&&(opMode==='manual'||opMode==='fixed'))updateSignals(forcedPhase);
      await updateUI(sd);
      if(sd.done){
        running=false;
        if(opMode==='rl'&&DQN.lastState!==null){
          var finalReward=DQN.computeReward(sd.info||{});
          DQN.step(sd.observation,finalReward,true);
          DQN.episodes++;
          DQN.updateUI();
          rlLog('Episode done. Replay:'+DQN.replay.length+' ε:'+DQN.EPSILON.toFixed(3)+' steps:'+DQN.totalSteps);
          DQN.saveModel();
        }
        await doGrade();
        _episodeFrozen = true;
        document.getElementById('status-txt').textContent='Episode complete ✓ — metrics preserved';
        log('Episode finished. Efficiency: '+effPct().toFixed(1)+'%','ok');
      }
    }catch(e){log('Step error: '+e.message,'err');}
  },ms);
}

document.getElementById('btn-reset').addEventListener('click',async function() {
  running=false;_episodeFrozen=false;
  if(runInterval){clearInterval(runInterval);runInterval=null;}LANE_NAMES.forEach(function(n){LQUEUES[n]=[];});
  _lastObs=null;_lastInfo=null;
  document.getElementById('status-txt').textContent='Initialising…';
  try{await doReset();document.getElementById('status-txt').textContent='Ready — press Run';}catch(e){document.getElementById('status-txt').textContent='Error — server?';log('Connection error: '+e.message,'err');}
});

document.getElementById('btn-run-rl').addEventListener('click',async function() {
  opMode='rl';
  _lastObs=null;_lastInfo=null;
  if(!sessionId)await doReset();if(runInterval){clearInterval(runInterval);runInterval=null;}
  running=true;document.getElementById('status-txt').textContent='DQN agent running — training live…';fixedTimer=0;forcedPhase=null;applySimSpeed();
  log('DQN policy started — ε='+DQN.EPSILON.toFixed(3),'rl');
});

document.getElementById('btn-run').addEventListener('click',async function() {
  opMode='pressure';_lastObs=null;_lastInfo=null;
  if(!sessionId)await doReset();if(runInterval){clearInterval(runInterval);runInterval=null;}
  running=true;document.getElementById('status-txt').textContent='Pressure policy running…';fixedTimer=0;forcedPhase=null;applySimSpeed();
});

document.getElementById('btn-stop').addEventListener('click',function() {
  running=false;if(runInterval){clearInterval(runInterval);runInterval=null;}
  document.getElementById('status-txt').textContent='Stopped.';log('Policy stopped.','warn');
  if(opMode==='rl') DQN.saveModel();
});

/* ═══════════════════════════════════════════════════════════════════════
   BATTLE MODE — Fixed Timer vs DQN AI
═══════════════════════════════════════════════════════════════════════ */
var BATTLE = {
  running: false,
  fixedSessionId: null,
  aiSessionId:    null,
  fixedStep: 0,
  aiStep:    0,
  horizon:   600,
  fixedTimer: 0,
  FIXED_CYCLE: 30,
  fixedQHist: [],
  aiQHist:    [],
  interval:   null,

  fixed: { cleared: 0, totalWait: 0, waitCount: 0, los: '—', step: 0 },
  ai:    { cleared: 0, totalWait: 0, waitCount: 0, los: '—', step: 0 },

  async start() {
    if (this.running) return;
    var task = document.getElementById('task-sel').value;
    var seedRaw = document.getElementById('seed-in').value;
    var seed = seedRaw ? parseInt(seedRaw) : Math.floor(Math.random() * 9999);

    this.fixedQHist = []; this.aiQHist = [];
    this.fixedTimer = 0;
    this.fixed = { cleared: 0, totalWait: 0, waitCount: 0, los: '—', step: 0 };
    this.ai    = { cleared: 0, totalWait: 0, waitCount: 0, los: '—', step: 0 };
    this.resetUI();

    try {
      var [rd1, rd2] = await Promise.all([
        fetch(BASE+'/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task_id:task,seed:seed})}).then(r=>r.json()),
        fetch(BASE+'/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task_id:task,seed:seed})}).then(r=>r.json())
      ]);
      this.fixedSessionId = rd1.session_id;
      this.aiSessionId    = rd2.session_id;
      this.horizon        = rd1.horizon || 600;
    } catch(e) {
      log('Battle start error: ' + e.message, 'err'); return;
    }

    this.running = true;
    document.getElementById('btn-battle-start').style.display = 'none';
    document.getElementById('btn-battle-stop').style.display  = 'flex';
    document.getElementById('fixed-dot').classList.add('active');
    document.getElementById('ai-dot').classList.add('active');
    document.getElementById('winner-banner').style.display = 'none';
    document.getElementById('vs-step-badge').textContent = 'RUNNING';
    log('Battle started · task=' + task + ' · seed=' + seed, 'ok');

    this._aiLastObs = null;
    this.fixedStep = 0;
    this.aiStep = 0;
    this.interval = setInterval(() => this.tick(), 160);
  },

  async tick() {
    if (!this.running) return;
    var done1 = this.fixed.step >= this.horizon;
    var done2 = this.ai.step    >= this.horizon;
    if (done1 && done2) { this.finish(); return; }

    var promises = [];

    if (!done1) {
      this.fixedTimer++;
      var fixedAction = Math.floor(this.fixedTimer / this.FIXED_CYCLE) % 2 === 0 ? 0 : 1;
      promises.push(
        fetch(BASE+'/step',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({session_id:this.fixedSessionId,action:fixedAction})})
        .then(r=>{ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
        .catch(e=>{log('Battle step err: '+e.message,'err');return null;})
      );
    } else { promises.push(Promise.resolve(null)); }

    if (!done2) {
      // FIX 3: use this._aiLastObs (not {}) for the actual obs passed to
      // dqnActionToApiAction, and drop the stale DQN.lastQVals guard so the
      // AI always picks an action even before the main episode has run.
      var aiAction = 0;
      if (DQN.online) {
        var tmpState = DQN.extractState(this._aiLastObs || null);
        var qv = DQN.online.forward(tmpState);
        var rawA = 0;
        for(var i=1;i<5;i++) if(qv[i]>qv[rawA]) rawA=i;
        aiAction = rawA;
      }
      promises.push(
        fetch(BASE+'/step',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({session_id:this.aiSessionId,action:aiAction})})
        .then(r=>{ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
        .catch(e=>{log('Battle step err: '+e.message,'err');return null;})
      );
    } else { promises.push(Promise.resolve(null)); }

    var [fixedSd, aiSd] = await Promise.all(promises);

    if (fixedSd) {
      this.fixed.step = fixedSd.step || 0;
      var fi = fixedSd.info || {};
      this.fixed.cleared = fi.total_cleared || 0;
      if (fi.avg_delay > 0) { this.fixed.totalWait += fi.avg_delay; this.fixed.waitCount++; }
      if (fi.los) this.fixed.los = fi.los;
      this.fixedQHist.push((fi.ns_queue||0)+(fi.ew_queue||0));
      if (this.fixedQHist.length > 120) this.fixedQHist.shift();
    }

    if (aiSd) {
      this._aiLastObs = aiSd.observation;
      this.ai.step = aiSd.step || 0;
      var ai = aiSd.info || {};
      this.ai.cleared = ai.total_cleared || 0;
      if (ai.avg_delay > 0) { this.ai.totalWait += ai.avg_delay; this.ai.waitCount++; }
      if (ai.los) this.ai.los = ai.los;
      this.aiQHist.push((ai.ns_queue||0)+(ai.ew_queue||0));
      if (this.aiQHist.length > 120) this.aiQHist.shift();
    }

    this.updateUI();
    if (this.fixed.step >= this.horizon && this.ai.step >= this.horizon) { this.finish(); }
  },

  finish() {
    this.running = false;
    clearInterval(this.interval); this.interval = null;
    document.getElementById('fixed-dot').classList.remove('active');
    document.getElementById('ai-dot').classList.remove('active');
    document.getElementById('btn-battle-start').style.display = 'flex';
    document.getElementById('btn-battle-stop').style.display  = 'none';
    document.getElementById('vs-step-badge').textContent = 'DONE';

    // FIX 4: replaced the meaningless cleared/(cleared+1) formula with a
    // proper efficiency percentage relative to episode horizon throughput.
    var aiEff   = Math.min(100, this.ai.cleared    / Math.max(this.horizon * 0.5, 1) * 100);
    var fixEff  = Math.min(100, this.fixed.cleared / Math.max(this.horizon * 0.5, 1) * 100);
    var aiWait  = this.ai.waitCount    > 0 ? this.ai.totalWait    / this.ai.waitCount    : 0;
    var fixWait = this.fixed.waitCount > 0 ? this.fixed.totalWait / this.fixed.waitCount : 0;

    var aiScore  = this.ai.cleared    - aiWait  * 2;
    var fixScore = this.fixed.cleared - fixWait * 2;

    var banner = document.getElementById('winner-banner');
    var icon   = document.getElementById('winner-icon');
    var text   = document.getElementById('winner-text');
    banner.style.display = 'flex';

    if (aiScore > fixScore) {
      icon.textContent = '🏆';
      text.textContent = 'DQN AI WINS · +' + (this.ai.cleared - this.fixed.cleared) + ' vehicles cleared · ' + (fixWait - aiWait).toFixed(1) + 's less waiting';
      banner.style.background = 'linear-gradient(135deg,rgba(167,139,250,0.15),rgba(167,139,250,0.04))';
      banner.style.borderColor = 'rgba(167,139,250,0.4)';
      text.style.color = 'var(--purple)';
      document.getElementById('battle-right').classList.add('winning');
      document.getElementById('battle-left').classList.add('losing');
    } else if (fixScore > aiScore) {
      icon.textContent = '⚠️';
      text.textContent = 'FIXED TIMER WINS · Train the DQN more before battling!';
      banner.style.background = 'linear-gradient(135deg,rgba(229,83,75,0.12),rgba(229,83,75,0.04))';
      banner.style.borderColor = 'rgba(229,83,75,0.3)';
      text.style.color = 'var(--red)';
      document.getElementById('battle-left').classList.add('winning');
      document.getElementById('battle-right').classList.add('losing');
    } else {
      icon.textContent = '🤝';
      text.textContent = "IT'S A TIE — both equally matched";
      text.style.color = 'var(--sand)';
    }
    log('Battle complete · AI cleared=' + this.ai.cleared + ' Fixed cleared=' + this.fixed.cleared, 'ok');
  },

  stop() {
    this.running = false;
    clearInterval(this.interval); this.interval = null;
    document.getElementById('fixed-dot').classList.remove('active');
    document.getElementById('ai-dot').classList.remove('active');
    document.getElementById('btn-battle-start').style.display = 'flex';
    document.getElementById('btn-battle-stop').style.display  = 'none';
    document.getElementById('vs-step-badge').textContent = 'STOPPED';
    log('Battle stopped.', 'warn');
  },

  resetUI() {
    ['fixed','ai'].forEach(side => {
      var el = document.getElementById(side+'-eff');    if(el) el.textContent='—';
      var el2= document.getElementById(side+'-wait');   if(el2) el2.textContent='—';
      var el3= document.getElementById(side+'-cleared');if(el3) el3.textContent='—';
      var el4= document.getElementById(side+'-los');    if(el4) el4.textContent='—';
      var el5= document.getElementById(side+'-step');   if(el5) el5.textContent='Step 0';
      var b1 = document.getElementById(side+'-eff-bar');    if(b1) b1.style.width='0%';
      var b2 = document.getElementById(side+'-wait-bar');   if(b2) b2.style.width='0%';
      var b3 = document.getElementById(side+'-cleared-bar');if(b3) b3.style.width='0%';
    });
    ['battle-left','battle-right'].forEach(id=>{
      var el=document.getElementById(id);
      if(el){el.classList.remove('winning');el.classList.remove('losing');}
    });
    ['vs-eff-delta','vs-wait-delta','vs-cleared-delta'].forEach(id=>{
      var el=document.getElementById(id);if(el){el.textContent='—';el.className='vs-delta-val';}
    });
    this._aiLastObs = null;
    this.fixedStep = 0;
    this.aiStep = 0;
  },

  updateUI() {
    var st = (id, v) => { var e = document.getElementById(id); if(e) e.textContent = v; };

    var fixWait = this.fixed.waitCount > 0 ? (this.fixed.totalWait / this.fixed.waitCount).toFixed(1) + 's' : '—';
    var aiWait  = this.ai.waitCount    > 0 ? (this.ai.totalWait    / this.ai.waitCount   ).toFixed(1) + 's' : '—';
    var fixEff = this.fixed.cleared > 0 ? Math.min(100, this.fixed.cleared / Math.max(this.horizon * 0.5, 1) * 100).toFixed(0) + '%' : '—';
    st('fixed-eff',     fixEff);
    st('fixed-wait',    fixWait);
    st('fixed-cleared', this.fixed.cleared > 0 ? this.fixed.cleared : '—');
    st('fixed-los',     this.fixed.los);
    st('fixed-step',    'Step ' + this.fixed.step);
    var fp = Math.min(this.fixed.step / Math.max(this.horizon, 1) * 100, 100);
    var fb = document.getElementById('fixed-eff-bar'); if(fb) fb.style.width = fp + '%';
    var fw = this.fixed.waitCount > 0 ? Math.min(100, 100 - (this.fixed.totalWait/this.fixed.waitCount)/80*100) : 0;
    var fwb = document.getElementById('fixed-wait-bar'); if(fwb) fwb.style.width = Math.max(0,fw) + '%';
    var fcb = document.getElementById('fixed-cleared-bar'); if(fcb) fcb.style.width = Math.min(100, this.fixed.cleared / Math.max(this.horizon * 0.5, 1) * 100) + '%';

    var aiEff = this.ai.cleared > 0 ? Math.min(100, this.ai.cleared / Math.max(this.horizon * 0.5, 1) * 100).toFixed(0) + '%' : '—';
    st('ai-eff',     aiEff);
    st('ai-wait',    aiWait);
    st('ai-cleared', this.ai.cleared > 0 ? this.ai.cleared : '—');
    st('ai-los',     this.ai.los);
    st('ai-step',    'Step ' + this.ai.step);
    var ap = Math.min(this.ai.step / Math.max(this.horizon, 1) * 100, 100);
    var ab = document.getElementById('ai-eff-bar'); if(ab) ab.style.width = ap + '%';
    var aw = this.ai.waitCount > 0 ? Math.min(100, 100 - (this.ai.totalWait/this.ai.waitCount)/80*100) : 0;
    var awb = document.getElementById('ai-wait-bar'); if(awb) awb.style.width = Math.max(0,aw) + '%';
    var acb = document.getElementById('ai-cleared-bar'); if(acb) acb.style.width = Math.min(100, this.ai.cleared / Math.max(this.horizon * 0.5, 1) * 100) + '%';

    var clearDiff = this.ai.cleared - this.fixed.cleared;
    var fixWaitNum = this.fixed.waitCount > 0 ? this.fixed.totalWait / this.fixed.waitCount : 0;
    var aiWaitNum  = this.ai.waitCount    > 0 ? this.ai.totalWait    / this.ai.waitCount    : 0;
    var waitDiff = fixWaitNum - aiWaitNum;

    var effEl = document.getElementById('vs-eff-delta');
    if (effEl && this.fixed.cleared > 0 && this.ai.cleared > 0) {
      var effDiff = this.ai.cleared - this.fixed.cleared;
      effEl.textContent = (effDiff >= 0 ? '+' : '') + effDiff + ' veh';
      effEl.className = 'vs-delta-val ' + (effDiff > 0 ? 'ai-ahead' : effDiff < 0 ? 'fixed-ahead' : '');
    }
    var waitEl = document.getElementById('vs-wait-delta');
    if (waitEl && fixWaitNum > 0 && aiWaitNum > 0) {
      waitEl.textContent = (waitDiff >= 0 ? '-' : '+') + Math.abs(waitDiff).toFixed(1) + 's';
      waitEl.className = 'vs-delta-val ' + (waitDiff > 0 ? 'ai-ahead' : waitDiff < 0 ? 'fixed-ahead' : '');
    }
    var clrEl = document.getElementById('vs-cleared-delta');
    if (clrEl && clearDiff !== 0) {
      clrEl.textContent = (clearDiff >= 0 ? '+' : '') + clearDiff;
      clrEl.className = 'vs-delta-val ' + (clearDiff > 0 ? 'ai-ahead' : 'fixed-ahead');
    }

    var step = Math.max(this.fixed.step, this.ai.step);
    st('vs-step-badge', 'STEP ' + step);

    this.drawMiniChart('fixed-chart', this.fixedQHist, '#6e7b8e');
    this.drawMiniChart('ai-chart',    this.aiQHist,    '#a78bfa');
  },

  drawMiniChart(id, data, color) {
    var canvas = document.getElementById(id); if (!canvas) return;
    var dpr = window.devicePixelRatio || 1;
    var W = canvas.offsetWidth || 200, H = 52;
    canvas.width = W * dpr; canvas.height = H * dpr;
    var c = canvas.getContext('2d'); c.scale(dpr, dpr);
    c.fillStyle = '#1e2330'; c.fillRect(0, 0, W, H);
    if (data.length < 2) return;
    var maxV = Math.max.apply(null, data.concat([1]));
    var px = 2, py = 3, iW = W - px*2, iH = H - py*2;
    var tx = i => px + (i / Math.max(data.length-1,1)) * iW;
    var ty = v => py + iH - (v / maxV) * iH;
    c.beginPath();
    data.forEach((v,i) => i===0 ? c.moveTo(tx(i),ty(v)) : c.lineTo(tx(i),ty(v)));
    c.lineTo(tx(data.length-1), H); c.lineTo(tx(0), H); c.closePath();
    var g = c.createLinearGradient(0,0,0,H);
    g.addColorStop(0, color + '44'); g.addColorStop(1, color + '00');
    c.fillStyle = g; c.fill();
    c.beginPath();
    data.forEach((v,i) => i===0 ? c.moveTo(tx(i),ty(v)) : c.lineTo(tx(i),ty(v)));
    c.strokeStyle = color; c.lineWidth = 1.5; c.lineJoin = 'round'; c.stroke();
  }
};

document.getElementById('btn-battle-start').addEventListener('click', () => BATTLE.start());
document.getElementById('btn-battle-stop').addEventListener('click',  () => BATTLE.stop());

/* ═══════════════════════════════════════════════════════════════════════
   STARTUP
═══════════════════════════════════════════════════════════════════════ */
(async function startup() {
  DQN.online = new QNetwork();
  DQN.target = new QNetwork();
  DQN.target.copyWeightsFrom(DQN.online);
  var restored = await DQN.loadModel();
  if (!restored) {
    DQN.init();
  } else {
    DQN.updateUI();
  }
  initVolBars();drawSparkline();drawAllTrendCharts();
  log('Dashboard ready — DQN agent ' + (restored ? 'restored from server checkpoint' : 'initialised fresh') + ' (57→128→128→64→5).', 'rl');
  log('Architecture: Double DQN · Adam lr=0.0005 · γ=0.95 · Replay 2000 · Batch 32 · ε-greedy · 5 actions · full 57-dim obs', 'rl');
  log('Weights auto-save to server every 50 train steps and on episode end / stop.', 'rl');
})();

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen();
    document.getElementById('fs-label').textContent = 'Exit Fullscreen';
    var b = document.getElementById('btn-fs');
    b.style.background = 'rgba(212,168,75,0.12)';
    b.style.borderColor = 'rgba(212,168,75,0.3)';
    b.style.color = '#d4a84b';
  } else {
    document.exitFullscreen();
    document.getElementById('fs-label').textContent = 'Fullscreen';
    var b = document.getElementById('btn-fs');
    b.style.background = 'var(--bg-raised)';
    b.style.borderColor = 'var(--border-mid)';
    b.style.color = 'var(--text-dim)';
  }
}

document.addEventListener('fullscreenchange', function() {
  if (!document.fullscreenElement) {
    document.getElementById('fs-label').textContent = 'Fullscreen';
    var b = document.getElementById('btn-fs');
    b.style.background = 'var(--bg-raised)';
    b.style.borderColor = 'var(--border-mid)';
    b.style.color = 'var(--text-dim)';
  }
});
</script>
</body>
</html>"""

DASHBOARD_HTML = __doc__

def render_dashboard():
    return DASHBOARD_HTML