import json
import random
from collections import defaultdict

# Data
FALLBACK = ("bulbasaur ivysaur venusaur charmander charmeleon charizard squirtle "
"wartortle blastoise caterpie metapod butterfree weedle kakuna beedrill pidgey "
"pidgeotto pidgeot rattata raticate spearow fearow ekans arbok pikachu raichu "
"sandshrew sandslash nidoran nidorina nidoqueen nidorino nidoking clefairy "
"clefable vulpix ninetales jigglypuff wigglytuff zubat golbat oddish gloom "
"vileplume paras parasect venonat venomoth diglett dugtrio meowth persian "
"psyduck golduck mankey primeape growlithe arcanine poliwag poliwhirl "
"poliwrath abra kadabra alakazam machop machoke machamp bellsprout weepinbell "
"victreebel tentacool tentacruel geodude graveler golem ponyta rapidash "
"slowpoke slowbro magnemite magneton farfetchd doduo dodrio seel dewgong "
"grimer muk shellder cloyster gastly haunter gengar onix drowzee hypno krabby "
"kingler voltorb electrode exeggcute exeggutor cubone marowak hitmonlee "
"hitmonchan lickitung koffing weezing rhyhorn rhydon chansey tangela "
"kangaskhan horsea seadra goldeen seaking staryu starmie scyther jynx "
"electabuzz magmar pinsir tauros magikarp gyarados lapras ditto eevee "
"vaporeon jolteon flareon porygon omanyte omastar kabuto kabutops aerodactyl "
"snorlax articuno zapdos moltres dratini dragonair dragonite mewtwo mew "
"chikorita bayleef meganium cyndaquil quilava typhlosion totodile croconaw "
"feraligatr sentret furret hoothoot noctowl ledyba ledian spinarak ariados "
"crobat chinchou lanturn togepi togetic natu xatu mareep flaaffy ampharos "
"bellossom marill azumarill sudowoodo politoed hoppip skiploom jumpluff "
"aipom sunkern sunflora yanma wooper quagsire espeon umbreon murkrow slowking "
"misdreavus unown wobbuffet girafarig pineco forretress dunsparce gligar "
"steelix snubbull granbull qwilfish scizor shuckle heracross sneasel teddiursa "
"ursaring slugma magcargo swinub piloswine corsola remoraid octillery delibird "
"mantine skarmory houndour houndoom kingdra phanpy donphan porygon2 stantler "
"smeargle tyrogue hitmontop smoochum elekid magby miltank blissey raikou entei "
"suicune larvitar pupitar tyranitar lugia celebi").split()


def load_names():
    try:
        import requests
        resp = requests.get("https://pokeapi.co/api/v2/pokemon?limit=2000", timeout=30)
        raw = [p["name"] for p in resp.json()["results"]]
        src = f"PokeAPI ({len(raw)} entries)"
    except Exception as e:
        print("  PokeAPI unavailable:", str(e)[:60])
        raw, src = FALLBACK, "embedded gen 1-2 list (fallback)"
    names = sorted({n.split("-")[0] for n in raw if len(n.split("-")[0]) >= 4})
    return names, src


names, source = load_names()
print(f"Loaded {len(names)} names via {source}")

# training
START, END = "^", "$"


def transition_pairs(order):
    rows = []
    for name in names:
        padded = START * order + name + END
        for i in range(len(padded) - order):
            rows.append((padded[i:i + order], padded[i + order]))
    return rows


def build_model(order):
    rows = transition_pairs(order)
    try:
        df = spark.createDataFrame(rows, ["context", "next_char"])
        counted = df.groupBy("context", "next_char").count().collect()
        counted = [(r["context"], r["next_char"], r["count"]) for r in counted]
    except NameError:  # not in Databricks -> plain Python groupBy
        agg = defaultdict(int)
        for ctx, nxt in rows:
            agg[(ctx, nxt)] += 1
        counted = [(c, n, v) for (c, n), v in agg.items()]
    model = defaultdict(dict)
    for ctx, nxt, cnt in counted:
        model[ctx][nxt] = cnt
    return dict(model)


MODELS = {order: build_model(order) for order in (1, 2, 3)}
for o, m in MODELS.items():
    print(f"  order {o}: {len(m)} contexts")

# generation check

def sample(counts, temperature=1.0):
    chars = list(counts.keys())
    weights = [c ** (1.0 / temperature) for c in counts.values()]
    return random.choices(chars, weights=weights)[0]


def generate(order=2, temperature=1.0, max_len=14):
    context, out = START * order, []
    while len(out) < max_len:
        ch = sample(MODELS[order][context], temperature)
        if ch == END:
            break
        out.append(ch)
        context = context[1:] + ch
    return "".join(out).capitalize()


print("samples:", [generate() for _ in range(5)])

# widget
HTML = r"""
<div id="pk-root">
<style>
  #pk-root{
    --paper:#eef1f6; --panel:#ffffff; --ink:#1b2a4a; --line:#cdd6e5;
    --coral:#ff5d73; --teal:#2bb3a3; --amber:#c07d12; --muted:#6b7689;
    background:var(--paper); color:var(--ink); border-radius:16px;
    padding:22px 22px 26px; font-family:"Segoe UI",system-ui,sans-serif;
    box-sizing:border-box;
  }
  #pk-root *{box-sizing:border-box;}
  .pk-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px 16px;margin-bottom:4px;}
  .pk-title{font-size:26px;font-weight:800;letter-spacing:-0.02em;margin:0;}
  .pk-controls{display:flex;flex-wrap:wrap;gap:12px;margin:16px 0 18px;align-items:center;}
  .pk-btn{font:inherit;font-weight:700;font-size:15px;border:0;border-radius:10px;
    background:var(--coral);color:#fff;padding:10px 20px;cursor:pointer;
    transition:transform .08s ease,opacity .15s;}
  .pk-btn:active{transform:scale(.96);} .pk-btn:disabled{opacity:.45;cursor:default;}
  .pk-btn.alt{background:var(--ink);}
  .pk-toggle{display:inline-flex;border:1.5px solid var(--line);border-radius:10px;
    overflow:hidden;background:var(--panel);}
  .pk-toggle button{font:inherit;font-weight:600;font-size:14px;border:0;background:transparent;
    color:var(--muted);padding:9px 14px;cursor:pointer;}
  .pk-toggle button.on{background:var(--ink);color:#fff;}
  .pk-slider{display:flex;align-items:center;gap:8px;background:var(--panel);
    border:1.5px solid var(--line);border-radius:10px;padding:6px 14px;}
  .pk-slider input{accent-color:var(--coral);width:130px;}
  .pk-slider label{font-size:13px;font-weight:600;color:var(--muted);white-space:nowrap;}
  .pk-note{font-size:12px;color:var(--muted);flex-basis:100%;margin:0 2px;}
  .pk-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;}
  @media(max-width:700px){.pk-grid{grid-template-columns:1fr;}}
  .pk-card{background:var(--panel);border-radius:14px;padding:16px;}
  .pk-label{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
    color:var(--muted);margin:0 0 12px;}
  #pk-name{min-height:64px;font-size:44px;font-weight:800;letter-spacing:.01em;
    font-family:ui-monospace,Consolas,monospace;display:flex;align-items:center;flex-wrap:wrap;}
  #pk-name span{display:inline-block;animation:pk-pop .18s ease;cursor:default;}
  @keyframes pk-pop{from{transform:scale(1.7);opacity:0;}to{transform:scale(1);opacity:1;}}
  @media(prefers-reduced-motion:reduce){
    #pk-name span{animation:none;}
    .pk-fill{transition:none;}
  }
  .pk-badge{display:inline-block;font-size:12px;font-weight:700;border-radius:8px;
    padding:4px 10px;margin-top:10px;}
  .pk-badge.new{background:rgba(43,179,163,.14);color:var(--teal);}
  .pk-badge.plag{background:rgba(255,93,115,.14);color:var(--coral);}
  .pk-badge.near{background:rgba(224,145,47,.16);color:var(--amber);}
  #pk-bits{font-size:12px;color:var(--muted);margin:10px 0 0;
    font-family:ui-monospace,Consolas,monospace;min-height:16px;}
  #pk-bits b{color:var(--ink);}
  #pk-from{font-size:12px;color:var(--muted);margin:8px 0 0;min-height:18px;
    display:flex;flex-wrap:wrap;align-items:center;gap:5px;}
  #pk-from .src{font-family:ui-monospace,Consolas,monospace;background:#f4f6fa;
    border-radius:8px;padding:2px 8px;color:var(--ink);cursor:help;}
  #pk-from .src.whole{background:rgba(255,93,115,.12);color:var(--coral);}
  #pk-history{margin:14px 0 0;padding:0;list-style:none;font-size:13px;color:var(--muted);
    display:flex;flex-wrap:wrap;gap:6px;}
  #pk-history li{background:#f4f6fa;border-radius:8px;padding:3px 10px;
    font-family:ui-monospace,Consolas,monospace;}
  #pk-history li.plag{color:var(--coral);text-decoration:line-through;}
  #pk-history li.near{color:var(--amber);text-decoration:underline wavy;}
  #pk-ctx{font-size:13px;color:var(--muted);margin:0 0 10px;min-height:18px;}
  #pk-ctx b{color:var(--ink);font-family:ui-monospace,Consolas,monospace;}
  .pk-bar-row{display:flex;align-items:center;gap:8px;margin:4px 0;}
  .pk-bar-ch{width:34px;text-align:center;font-family:ui-monospace,Consolas,monospace;
    font-size:13px;font-weight:700;color:var(--muted);background:#f4f6fa;border-radius:6px;padding:1px 0;}
  .pk-track{flex:1;height:13px;background:#f0f3f8;border-radius:7px;overflow:hidden;}
  .pk-fill{height:100%;width:0%;border-radius:7px;background:var(--teal);transition:width .12s linear;}
  .pk-bar-row.win .pk-fill{background:var(--coral);}
  .pk-bar-row.win .pk-bar-ch{color:#fff;background:var(--coral);}
  .pk-pct{width:44px;font-size:11px;color:var(--muted);text-align:right;
    font-family:ui-monospace,Consolas,monospace;}
</style>
  <div class="pk-head">
    <h2 class="pk-title">Invent a Pok&eacute;mon</h2>
  </div>
  <div class="pk-controls">
    <button class="pk-btn" id="pk-go">&#10024; Generate</button>
    <button class="pk-btn alt" id="pk-greedy">&#9650; Most likely</button>
    <span class="pk-toggle" role="group" aria-label="memory">
      <button data-o="1">1 letter</button>
      <button data-o="2" class="on">2 letters</button>
      <button data-o="3">3 letters</button>
    </span>
    <span class="pk-slider">
      <label id="pk-tlabel">Chaos 1.0</label>
      <input type="range" id="pk-temp" min="0.5" max="2.5" step="0.1" value="1.0">
    </span>
    <p class="pk-note" id="pk-note"></p>
  </div>
  <div class="pk-grid">
    <div class="pk-card">
      <p class="pk-label">1 &middot; The name being born</p>
      <div id="pk-name"><span style="color:var(--muted);font-size:16px;font-weight:400">
        press the button, professor</span></div>
      <span id="pk-badge"></span>
      <p id="pk-bits"></p>
      <p id="pk-from"></p>
      <ul id="pk-history"></ul>
    </div>
    <div class="pk-card">
      <p class="pk-label">2 &middot; The dice being rolled</p>
      <p id="pk-ctx">each row = a letter the model considered</p>
      <div id="pk-bars"></div>
    </div>
  </div>
<script>
(function(){
  const MODELS = /*MODELS*/;
  const REAL   = new Set(/*REAL*/);
  const REAL_ARR = Array.from(REAL);
  const NOTES  = {
    1: "1 letter of memory: goldfish mode. Expect beautiful gibberish.",
    2: "2 letters of memory: the sweet spot. New, yet Pok\u00e9mon-shaped.",
    3: "3 letters of memory: photographic. Watch it plagiarize real Pok\u00e9mon."
  };
  const START="^", END="$", STEP_MS=300, MAX_LEN=14;
  let order=2, temp=1.0, running=false, lastCtx=START.repeat(2);
  const $=id=>document.getElementById(id);
  const nameEl=$("pk-name"), badge=$("pk-badge"), hist=$("pk-history"),
        bars=$("pk-bars"), ctxEl=$("pk-ctx"), note=$("pk-note"),
        bitsEl=$("pk-bits"), fromEl=$("pk-from"),
        btn=$("pk-go"), greedyBtn=$("pk-greedy"),
        tSlider=$("pk-temp"), tLabel=$("pk-tlabel");
  const tc = s => s.charAt(0).toUpperCase() + s.slice(1);
  note.textContent=NOTES[order];

  /* distributions */
  function probs(counts,t){
    const out=[]; let s=0;
    for(const ch in counts){ const w=Math.pow(counts[ch],1/t); out.push([ch,w]); s+=w; }
    out.forEach(p=>p[1]/=s);
    out.sort((a,b)=>b[1]-a[1]);
    return out;
  }
  function pick(p){
    let r=Math.random();
    for(const [ch,w] of p){ r-=w; if(r<=0) return ch; }
    return p[p.length-1][0];
  }

  function surprisal(counts,ch){
    let s=0; for(const k in counts) s+=counts[k];
    return -Math.log2(counts[ch]/s);
  }
  function bitsColor(b){
    const t=Math.min(b/5,1), a=[43,179,163], z=[255,93,115];
    const m=a.map((v,i)=>Math.round(v+(z[i]-v)*t));
    return "rgb("+m[0]+","+m[1]+","+m[2]+")";
  }

  /* near-miss detection */
  function dist(a,b,cap){
    const n=a.length, m=b.length;
    if(Math.abs(n-m)>cap) return cap+1;
    let prev=Array.from({length:m+1},(_,j)=>j);
    for(let i=1;i<=n;i++){
      const cur=[i]; let best=i;
      for(let j=1;j<=m;j++){
        const v=Math.min(prev[j]+1, cur[j-1]+1,
                         prev[j-1]+(a[i-1]===b[j-1]?0:1));
        cur[j]=v; if(v<best) best=v;
      }
      if(best>cap) return cap+1;
      prev=cur;
    }
    return prev[m];
  }

  function nearest(word){
    const cap = word.length>=7 ? 2 : 1;
    let best=null, bd=cap+1;
    for(const r of REAL_ARR){
      const d=dist(word,r,cap);
      if(d<bd){ bd=d; best=r; if(d===1) break; }
    }
    return bd<=cap ? {name:best,d:bd} : null;
  }

  /* provenance: which training names contain the fragments we used */
  function matcher(ng){
    let s=ng, pre=false, suf=false;
    while(s[0]===START){ s=s.slice(1); pre=true; }
    if(s[s.length-1]===END){ s=s.slice(0,-1); suf=true; }
    if(!s) return null;
    if(pre&&suf) return n=>n===s;
    if(pre)      return n=>n.slice(0,s.length)===s;
    if(suf)      return n=>n.slice(-s.length)===s;
    return n=>n.indexOf(s)>=0;
  }
  function provenance(ngrams){
    const score={}, shares={};
    let total=0;
    for(const ng of ngrams){
      const m=matcher(ng);
      if(!m) continue;
      const hits=REAL_ARR.filter(m);
      if(!hits.length) continue;
      total++;
      const w=1/hits.length;
      const frag=ng.split(START).join("").split(END).join("");
      for(const h of hits){
        score[h]=(score[h]||0)+w;
        (shares[h]=shares[h]||[]).push(frag);
      }
    }
    const ranked=Object.keys(score).sort((a,b)=>score[b]-score[a]);
    return {ranked,shares,total};
  }
  function showProvenance(out,prov){
    fromEl.innerHTML="";
    if(!prov.ranked.length) return;
    const lead=document.createElement("span");
    lead.textContent="built from";
    fromEl.appendChild(lead);
    prov.ranked.slice(0,3).forEach(n=>{
      const frags=prov.shares[n];
      const chip=document.createElement("span");
      chip.className="src"+(frags.length===prov.total?" whole":"");
      chip.textContent=tc(n);
      chip.title=frags.length+" of "+prov.total+" fragments: "+frags.join(" \u00b7 ");
      fromEl.appendChild(chip);
    });
    const whole=prov.ranked.find(n=>prov.shares[n].length===prov.total && n!==out);
    if(whole){
      const tail=document.createElement("span");
      tail.textContent="\u2014 every fragment of this name is in "+tc(whole);
      fromEl.appendChild(tail);
    }
  }

  /* bars */
  function pretty(ctx){
    const t=ctx.split(START).join("");
    return t==="" ? "at the very start" : "after \u2039"+t+"\u203A";
  }
  function showBars(p,winner){
    bars.innerHTML="";
    p.slice(0,8).forEach(([ch,w])=>{
      const row=document.createElement("div"); row.className="pk-bar-row";
      if(ch===winner) row.classList.add("win");
      const c=document.createElement("span"); c.className="pk-bar-ch";
      c.textContent = ch===END ? "\u23CE" : ch;
      const tr=document.createElement("div"); tr.className="pk-track";
      const f=document.createElement("div"); f.className="pk-fill";
      tr.appendChild(f);
      const pct=document.createElement("span"); pct.className="pk-pct";
      pct.textContent=(w*100).toFixed(1)+"%";
      row.appendChild(c); row.appendChild(tr); row.appendChild(pct);
      bars.appendChild(row);
      requestAnimationFrame(()=>{ f.style.width=(w*100)+"%"; });
    });
  }
  
  function previewBars(){
    const counts=MODELS[order][lastCtx];
    if(!counts) return;
    ctxEl.innerHTML="context: <b>"+pretty(lastCtx)+"</b>";
    showBars(probs(counts,temp),null);
  }

  /* controls */
  document.querySelectorAll(".pk-toggle button").forEach(b=>{
    b.onclick=()=>{ if(running) return;
      order=+b.dataset.o;
      document.querySelectorAll(".pk-toggle button").forEach(x=>x.classList.toggle("on",x===b));
      note.textContent=NOTES[order];
      lastCtx=START.repeat(order);
      previewBars();
    };
  });
  tSlider.oninput=()=>{
    temp=+tSlider.value; tLabel.textContent="Chaos "+temp.toFixed(1);
    if(!running) previewBars();
  };

  /* generation */
  function generate(mode){
    if(running) return;
    running=true; btn.disabled=true; greedyBtn.disabled=true;
    nameEl.innerHTML=""; badge.textContent=""; badge.className="";
    bitsEl.textContent=""; fromEl.innerHTML="";
    let context=START.repeat(order), out="", bits=0;
    const ngrams=[];

    function step(){
      const counts=MODELS[order][context];
      const p=probs(counts, mode==="greedy" ? 1 : temp);
      const ch = mode==="greedy" ? p[0][0] : pick(p);
      lastCtx=context;
      ctxEl.innerHTML="context: <b>"+pretty(context)+"</b>";
      showBars(probs(counts,temp),ch);
      const s=surprisal(counts,ch);
      bits+=s;
      ngrams.push(context+ch);
      if(ch===END || out.length>=MAX_LEN){ return finish(mode,bits,ngrams); }
      out+=ch;
      const span=document.createElement("span");
      span.textContent = out.length===1 ? ch.toUpperCase() : ch;
      span.style.color = bitsColor(s);
      span.title = s.toFixed(2)+" bits";
      nameEl.appendChild(span);
      context=context.slice(1)+ch;
      setTimeout(step,STEP_MS);
    }

    function finish(mode,bits,ngrams){
      const isReal=REAL.has(out);
      const near = isReal ? null : nearest(out);
      const li=document.createElement("li");
      li.textContent=tc(out);

      if(isReal){
        badge.textContent="\u26A0 already exists \u2014 the model memorized this one";
        badge.className="pk-badge plag";
        li.classList.add("plag");
      } else if(near){
        badge.textContent="\u25D0 "+(near.d===1?"one letter":near.d+" letters")
                        +" from "+tc(near.name);
        badge.className="pk-badge near";
        li.classList.add("near");
        li.title="near-miss: "+tc(near.name);
      } else {
        badge.textContent="\u2713 brand new species";
        badge.className="pk-badge new";
      }

      bitsEl.innerHTML="<b>"+bits.toFixed(1)+" bits</b> to spell this \u00b7 "
        +(bits/(out.length+1)).toFixed(2)+" per letter"
        +(mode==="greedy" ? " \u00b7 greedy, chaos ignored" : "");

      showProvenance(out, provenance(ngrams));

      hist.prepend(li);
      while(hist.children.length>10) hist.removeChild(hist.lastChild);
      running=false; btn.disabled=false; greedyBtn.disabled=false;
    }
    step();
  }

  btn.onclick=()=>generate("sample");
  greedyBtn.onclick=()=>generate("greedy");
  previewBars();
})();
</script>
</div>
"""
HTML = HTML.replace("/*MODELS*/", json.dumps(MODELS))
HTML = HTML.replace("/*REAL*/", json.dumps(names))

try:
    displayHTML(HTML)
except NameError:
    with open("invent_a_pokemon.html", "w", encoding="utf-8") as f:
        f.write("<!doctype html><meta charset='utf-8'>\n" + HTML)
    print("Not in Databricks -> wrote invent_a_pokemon.html (open in any browser).")
