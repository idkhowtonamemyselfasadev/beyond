#!/usr/bin/env python3
"""Assembles the Beyond the End resource pack: 3D item models and the music.

    python3 pack/build_pack.py   -> release/BeyondTheEnd-Pack.zip (+ its sha1 printed)
                                    pack/preview.html (every model, drag to turn)

Models: pack/models.py sculpts one 3D model per item (46). The mod stamps every item with
custom_model_data string `beyond:<id>`; assets/minecraft/items/<base>.json selects on it
and falls back to the vanilla definition (read out of the game jar, so armour trims keep
working). Worn armour keeps the vanilla metal look (a tinted version was tried and hated).

CustomWeapons: that mod's pack overrides the same item files for five base items
(iron/diamond/netherite sword, netherite axe and hoe). A client only keeps one file per
path, so this pack folds the CustomWeapons cases and models in (a snapshot of its built
pack lives in pack/vendor/customweapons-models) and both mods' items show whichever pack
is on top.

Music: the tracks composed by music/compose.py, with the sound events the biomes reference.
"""
import base64
import hashlib
import io
import json
import os
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import models  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC = os.path.join(ROOT, "music")
OUT = os.path.join(ROOT, "pack", "beyond-pack")
ZIP = os.path.join(ROOT, "release", "BeyondTheEnd-Pack.zip")
PREVIEW = os.path.join(ROOT, "pack", "preview.html")
VENDOR = os.path.join(ROOT, "pack", "vendor", "customweapons-models")
JAR = os.path.expanduser("~/.gradle/caches/fabric-loom/minecraftMaven/net/minecraft/minecraft-merged/"
                         "1.21.11-loom.mappings.1_21_11.layered+hash.2198-v2/"
                         "minecraft-merged-1.21.11-loom.mappings.1_21_11.layered+hash.2198-v2.jar")
TRACKS = ["violet", "verdigris", "ember", "bone", "abyssal", "gilded", "roseate", "glacial", "hollow_king"]

# Which vanilla item each Beyond item rides on (mirrors BeyondItems.java / GearItem.java).
TIER_BASE = {"thallasium": "iron", "terminite": "diamond", "aeternium": "netherite"}
BASE = {
    "thallasium_dust": "prismarine_crystals", "thallasium_ingot": "iron_ingot", "terminite_ingot": "copper_ingot",
    "aeternium_ingot": "netherite_ingot", "amber": "honeycomb", "silk_fibre": "string", "gelatine": "slime_ball",
    "shadow_essence": "echo_shard", "end_fish": "cod",
    "chorus_lantern": "soul_lantern", "crystal_focus": "prismarine_shard", "amber_heart": "heart_of_the_sea",
    "veil_of_shadows": "phantom_membrane", "tidal_lens": "nautilus_shell", "starfall_shard": "quartz",
    "eternal_crystal": "amethyst_shard", "gale_rod": "breeze_rod", "void_heart": "nether_star", "tempest_horn": "goat_horn",
}
for tier, metal in TIER_BASE.items():
    for kind in models.GEAR:
        BASE[f"{tier}_{kind}"] = f"{metal}_{kind}"
NAMES = {iid: iid.replace("_", " ").title().replace("Of", "of") for iid in BASE}


def vanilla(path):
    with zipfile.ZipFile(JAR) as z:
        return z.read(path)


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if isinstance(data, bytes) else "w"
    with open(path, mode) as f:
        if isinstance(data, (dict, list)):
            json.dump(data, f, indent=2)
        else:
            f.write(data)


def item_definition(base, cases, fallback):
    return {"model": {"type": "minecraft:select", "property": "minecraft:custom_model_data", "index": 0,
                      "cases": cases, "fallback": fallback}}


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    write(os.path.join(OUT, "pack.mcmeta"), {"pack": {"pack_format": 75, "min_format": [75, 0], "max_format": [75, 99],
                                                     "description": "Beyond the End: 3D items and music"}})

    # ---- models and textures -------------------------------------------------------------------
    built = models.build_all()
    counts = {}
    for iid, (model, tex, n) in built.items():
        write(os.path.join(OUT, "assets", "beyond", "models", "item", iid + ".json"), model)
        buf = io.BytesIO()
        tex.save(buf, "PNG")
        write(os.path.join(OUT, "assets", "beyond", "textures", "item", iid + ".png"), buf.getvalue())
        counts[iid] = n

    # ---- item definitions: ours, then CustomWeapons' cases, then vanilla -------------------------
    by_base = {}
    for iid, base in BASE.items():
        by_base.setdefault(base, []).append(iid)
    vendored = 0
    if os.path.isdir(VENDOR):
        # Everything of theirs except the item definitions, which are merged below.
        for folder, _, files in os.walk(os.path.join(VENDOR, "assets")):
            rel = os.path.relpath(folder, VENDOR)
            if rel.startswith(os.path.join("assets", "minecraft", "items")):
                continue
            for fn in files:
                dst = os.path.join(OUT, rel, fn)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy(os.path.join(folder, fn), dst)
                vendored += 1
        cw_items = os.path.join(VENDOR, "assets", "minecraft", "items")
        for fn in os.listdir(cw_items):
            base = fn[:-5]
            by_base.setdefault(base, [])
    for base, ids in by_base.items():
        cases = [{"when": f"beyond:{iid}", "model": {"type": "minecraft:model", "model": f"beyond:item/{iid}"}} for iid in ids]
        fallback = json.loads(vanilla(f"assets/minecraft/items/{base}.json"))["model"]
        extra = {}
        cw = os.path.join(VENDOR, "assets", "minecraft", "items", base + ".json")
        if os.path.isfile(cw):
            theirs = json.load(open(cw))
            cases += theirs["model"]["cases"]          # their fallback is vanilla too
            extra = {k: v for k, v in theirs.items() if k != "model"}   # hand_animation_on_swap
        definition = item_definition(base, cases, fallback)
        definition.update(extra)
        write(os.path.join(OUT, "assets", "minecraft", "items", base + ".json"), definition)

    # ---- music ---------------------------------------------------------------------------------------------
    events = {}
    missing = []
    for name in TRACKS:
        src = os.path.join(MUSIC, name + ".ogg")
        if not os.path.exists(src):
            missing.append(name)
            continue
        dst = os.path.join(OUT, "assets", "beyond", "sounds", "music", name + ".ogg")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)
        events[f"music.beyond.{name}"] = {"sounds": [{"name": f"beyond:music/{name}", "stream": True}]}
    write(os.path.join(OUT, "assets", "beyond", "sounds.json"), events)

    # ---- zip -----------------------------------------------------------------------------------------------
    os.makedirs(os.path.dirname(ZIP), exist_ok=True)
    # Fixed timestamps: the sha1 (which the server config carries) only changes with content.
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, _, files in sorted(os.walk(OUT)):
            for fn in sorted(files):
                path = os.path.join(folder, fn)
                info = zipfile.ZipInfo(os.path.relpath(path, OUT), date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                with open(path, "rb") as f:
                    z.writestr(info, f.read())
    sha1 = hashlib.sha1(open(ZIP, "rb").read()).hexdigest()

    write_preview(built)
    print(f"{len(built)} models ({sum(counts.values())} elements), {len(by_base)} item definitions, "
          f"{vendored} CustomWeapons files folded in, {len(events)} tracks (missing: {missing or 'none'})")
    print(f"zip: {ZIP} ({os.path.getsize(ZIP) // 1024} KB)")
    print(f"sha1: {sha1}")
    print(f"preview: {PREVIEW}")


HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>Beyond the End models</title>
<style>
  body{margin:0;background:#15121c;color:#ece8f2;font:14px/1.4 system-ui,sans-serif}
  h1{font-size:18px;margin:16px 20px 4px}
  p.hint{margin:0 20px 12px;color:#a9a}
  h2.sec{font-size:16px;margin:18px 20px 6px;color:#c9b6ff}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;padding:0 20px 16px}
  .card{background:#221c2e;border-radius:10px;padding:8px;display:flex;flex-direction:column;gap:6px}
  .card h3{font-size:14px;margin:2px 4px;font-weight:600}
  .card canvas.view{width:100%;height:200px;border-radius:8px;background:radial-gradient(#3a3050,#1a1524);cursor:grab;display:block}
  .row{display:flex;gap:8px;align-items:center}
  .row canvas.tex{width:48px;height:48px;image-rendering:pixelated;background:#111;border-radius:4px}
  .row canvas.gui{width:48px;height:48px;image-rendering:pixelated;background:#8b8b8b;border:2px solid #373737;border-radius:4px}
  .meta{color:#a9a;font-size:12px}
</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head><body>
<h1>Beyond the End – 3D item models</h1>
<p class="hint">Drag to rotate, scroll to zoom. The grey box is the inventory view (the GUI transform), the small texture is the swatch sheet each model paints from.</p>
<div id="root"></div>
<script>
const DATA = __DATA__;
const SECTIONS = __SECTIONS__;
function loadTexture(uri){ const t = new THREE.TextureLoader().load(uri); t.magFilter = t.minFilter = THREE.NearestFilter; t.flipY = false; return t; }
function buildModel(model, texture){
  const group = new THREE.Group();
  const mat = new THREE.MeshLambertMaterial({map: texture, side: THREE.DoubleSide, transparent: true, alphaTest: 0.05});
  for (const el of model.elements){
    const [x0,y0,z0] = el.from, [x1,y1,z1] = el.to;
    const geo = new THREE.BoxGeometry(x1-x0, y1-y0, z1-z0);
    const order = ['east','west','up','down','south','north'];
    const uv = geo.attributes.uv;
    order.forEach((side, i) => { const f = el.faces[side]; if (!f) return; const [u0,v0,u1,v1] = f.uv.map(c => c/16);
      [[u0,v0],[u1,v0],[u0,v1],[u1,v1]].forEach(([u,v], k) => uv.setXY(i*4+k, u, v)); });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set((x0+x1)/2, (y0+y1)/2, (z0+z1)/2);
    if (el.rotation){ const r = el.rotation, o = new THREE.Vector3(...r.origin); const piv = new THREE.Group(); piv.position.copy(o); mesh.position.sub(o); piv.add(mesh);
      const a = THREE.MathUtils.degToRad(r.angle); if (r.axis==='x') piv.rotation.x = a; if (r.axis==='y') piv.rotation.y = a; if (r.axis==='z') piv.rotation.z = a; group.add(piv); }
    else group.add(mesh);
  }
  const root = new THREE.Group(); group.position.set(-8,-8,-8); root.add(group); return root;
}
// One WebGL renderer for the whole page (browsers allow ~16 contexts); each card is a 2D
// canvas that a shared offscreen renderer draws into every frame.
const gl = document.createElement('canvas');
const renderer = new THREE.WebGLRenderer({canvas: gl, antialias: true, alpha: true, preserveDrawingBuffer: true});
const views = [];
function scene(canvas, model, texture, gui){
  const sc = new THREE.Scene(); sc.add(new THREE.AmbientLight(0xffffff, 0.6));
  const sun = new THREE.DirectionalLight(0xffffff, 0.8); sun.position.set(6, 10, 8); sc.add(sun);
  const obj = buildModel(model, texture); sc.add(obj);
  let cam;
  if (gui){ cam = new THREE.OrthographicCamera(-9, 9, 9, -9, -50, 50); cam.position.set(0,0,20); cam.lookAt(0,0,0);
    const d = (model.display && model.display.gui) || {rotation:[0,0,0], scale:[1,1,1]};
    obj.rotation.set(THREE.MathUtils.degToRad(d.rotation[0]), THREE.MathUtils.degToRad(d.rotation[1]), THREE.MathUtils.degToRad(d.rotation[2]));
    obj.scale.set(...d.scale); }
  else { cam = new THREE.PerspectiveCamera(35, 1, 0.1, 200); }
  const v = {canvas, sc, cam, obj, gui, rx: 0.3, ry: -0.6, dist: 30, ctx: canvas.getContext('2d')};
  if (!gui){
    let drag = null;
    canvas.addEventListener('pointerdown', e => { drag = [e.clientX, e.clientY]; canvas.setPointerCapture(e.pointerId); });
    canvas.addEventListener('pointermove', e => { if (!drag) return; v.ry += (e.clientX - drag[0]) * 0.01; v.rx += (e.clientY - drag[1]) * 0.01; drag = [e.clientX, e.clientY]; });
    canvas.addEventListener('pointerup', () => drag = null);
    canvas.addEventListener('wheel', e => { v.dist = Math.max(12, Math.min(60, v.dist + e.deltaY * 0.03)); e.preventDefault(); }, {passive:false});
  }
  views.push(v);
}
function frame(){
  for (const v of views){
    const w = Math.max(1, v.canvas.clientWidth), h = Math.max(1, v.canvas.clientHeight);
    if (v.canvas.width !== w || v.canvas.height !== h){ v.canvas.width = w; v.canvas.height = h; }
    renderer.setSize(w, h, false);
    if (!v.gui){ v.cam.aspect = w / h; v.cam.updateProjectionMatrix(); v.obj.rotation.set(v.rx, v.ry, 0); v.cam.position.set(0, 4, v.dist); v.cam.lookAt(0,0,0); }
    renderer.render(v.sc, v.cam);
    v.ctx.clearRect(0, 0, w, h);
    v.ctx.drawImage(gl, 0, gl.height - h, w, h, 0, 0, w, h);
  }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
const root = document.getElementById('root');
for (const [title, ids] of SECTIONS){
  const h = document.createElement('h2'); h.className = 'sec'; h.textContent = title; root.appendChild(h);
  const grid = document.createElement('div'); grid.className = 'grid'; root.appendChild(grid);
  for (const id of ids){
    const d = DATA[id]; const tex = loadTexture(d.texture);
    const card = document.createElement('div'); card.className = 'card';
    card.innerHTML = `<h3>${d.name}</h3><canvas class="view"></canvas><div class="row"><canvas class="gui" width="64" height="64"></canvas><canvas class="tex" width="64" height="64"></canvas><span class="meta">${d.count} boxes · on ${d.base}</span></div>`;
    grid.appendChild(card);
    scene(card.querySelector('canvas.view'), d.model, tex, false);
    scene(card.querySelector('canvas.gui'), d.model, tex, true);
    const img = new Image(); img.onload = () => card.querySelector('canvas.tex').getContext('2d').drawImage(img, 0, 0); img.src = d.texture;
  }
}
</script></body></html>
"""


def write_preview(built):
    data = {}
    for iid, (model, tex, n) in built.items():
        buf = io.BytesIO()
        tex.save(buf, "PNG")
        data[iid] = {"name": NAMES[iid], "base": BASE[iid], "count": n, "model": model,
                     "texture": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}
    sections = []
    for tier in models.TIERS:
        sections.append([tier.title() + " gear", [f"{tier}_{k}" for k in models.GEAR]])
    sections.append(["Materials", list(models.MATERIALS)])
    sections.append(["Relics", list(models.RELICS)])
    html = HTML.replace("__DATA__", json.dumps(data)).replace("__SECTIONS__", json.dumps(sections))
    with open(PREVIEW, "w") as f:
        f.write(html)


if __name__ == "__main__":
    main()
