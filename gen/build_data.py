#!/usr/bin/env python3
"""Generates every data file for Beyond the End into src/main/resources/data/.

Biomes, the End dimension override, the terrain surface rules, every flora feature, biome
tags, loot tables (including the vanilla tables it has to wrap so the overworld stays vanilla)
and the advancement tab. Editing this file and re-running it is how the world is changed;
nothing under data/ is hand-written.

All numbers and ids are for 1.21.11: biome colours, particles, sounds and music live in the
biome's `attributes` map (not `effects`), colours are hex strings, folders are singular.
"""
import json
import os
import shutil
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'src', 'main', 'resources', 'data')
NS = 'beyond'
SERVER_JAR = '/home/tim/claude/customweapons/run/versions/1.21.11/server-1.21.11.jar'

jar = zipfile.ZipFile(SERVER_JAR)

# Every file under data/ is written by this script, so start from nothing. Without this a
# renamed biome or recipe leaves its old file behind and the server happily loads both.
shutil.rmtree(DATA, ignore_errors=True)


def vanilla(path):
    return json.loads(jar.read('data/minecraft/' + path))


def write(path, data):
    full = os.path.join(DATA, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')


def state(name, **props):
    s = {"Name": "minecraft:" + name}
    if props:
        s["Properties"] = {k: str(v).lower() for k, v in props.items()}
    return s


def simple(name, **props):
    return {"type": "minecraft:simple_state_provider", "state": state(name, **props)}


def weighted(entries):
    """entries: list of (name, weight) or (state-dict, weight)."""
    out = []
    for item, w in entries:
        out.append({"data": item if isinstance(item, dict) else state(item), "weight": w})
    return {"type": "minecraft:weighted_state_provider", "entries": out}


# ============================================================================ features
configured = {}
placed = {}


def cf(name, data):
    configured[name] = data
    return f"{NS}:{name}"


def pf(name, feature, placement):
    placed[name] = {"feature": feature, "placement": placement}
    return f"{NS}:{name}"


AIR_HERE = {"type": "minecraft:block_predicate_filter",
            "predicate": {"type": "minecraft:matching_blocks", "blocks": "minecraft:air"}}


def on(blocks):
    """Only where the block underneath is one of these - trees on their own ground."""
    return {"type": "minecraft:block_predicate_filter",
            "predicate": {"type": "minecraft:matching_blocks", "offset": [0, -1, 0], "blocks": blocks}}


def surface(count, extra=None, rarity=None):
    p = []
    if rarity:
        p.append({"type": "minecraft:rarity_filter", "chance": rarity})
    if count:
        p.append({"type": "minecraft:count", "count": count})
    p += [{"type": "minecraft:in_square"},
          {"type": "minecraft:heightmap", "heightmap": "MOTION_BLOCKING"}]
    if extra:
        p += extra
    p.append({"type": "minecraft:biome"})
    return p


def underground(count, y_min, y_max, rarity=None):
    p = []
    if rarity:
        p.append({"type": "minecraft:rarity_filter", "chance": rarity})
    p += [{"type": "minecraft:count", "count": count},
          {"type": "minecraft:in_square"},
          {"type": "minecraft:height_range", "height": {"type": "minecraft:uniform",
                                                         "min_inclusive": {"absolute": y_min},
                                                         "max_inclusive": {"absolute": y_max}}},
          {"type": "minecraft:biome"}]
    return p


def patch(name, provider, tries=32, xz=7, y=3):
    return cf(name, {"type": "minecraft:random_patch", "config": {
        "tries": tries, "xz_spread": xz, "y_spread": y,
        "feature": {"feature": {"type": "minecraft:simple_block", "config": {"to_place": provider}},
                    "placement": [AIR_HERE]}}})


def tree(name, log, leaves, ground, base=5, rand=3, radius=2, foliage_h=3, trunk="straight",
         decorators=None, leaf_props=None):
    lp = {"distance": "7", "persistent": "false", "waterlogged": "false"}
    if leaf_props is not None:
        lp = leaf_props
    leaf_state = {"Name": "minecraft:" + leaves}
    if lp:
        leaf_state["Properties"] = lp
    if trunk == "straight":
        trunk_placer = {"type": "minecraft:straight_trunk_placer", "base_height": base,
                        "height_rand_a": rand, "height_rand_b": 0}
    elif trunk == "forking":
        trunk_placer = {"type": "minecraft:forking_trunk_placer", "base_height": base,
                        "height_rand_a": rand, "height_rand_b": 1}
    else:
        trunk_placer = {"type": "minecraft:bending_trunk_placer", "base_height": base,
                        "height_rand_a": rand, "height_rand_b": 0, "min_height_for_leaves": 3,
                        "bend_length": {"type": "minecraft:uniform", "min_inclusive": 1, "max_inclusive": 2}}
    return cf(name, {"type": "minecraft:tree", "config": {
        "decorators": decorators or [],
        "dirt_provider": simple(ground), "force_dirt": True, "ignore_vines": True,
        "foliage_placer": {"type": "minecraft:blob_foliage_placer", "height": foliage_h,
                           "offset": 0, "radius": radius},
        "foliage_provider": {"type": "minecraft:simple_state_provider", "state": leaf_state},
        "minimum_size": {"type": "minecraft:two_layers_feature_size", "limit": 1,
                         "lower_size": 0, "upper_size": 1},
        "trunk_placer": trunk_placer,
        "trunk_provider": simple(log, axis="y")}})


def fungus(name, base_block, stem, hat, decor):
    v = vanilla('worldgen/configured_feature/warped_fungus.json')['config']
    return cf(name, {"type": "minecraft:huge_fungus", "config": {
        "valid_base_block": state(base_block), "stem_state": state(stem, axis="y"),
        "hat_state": state(hat), "decor_state": state(decor), "planted": False,
        "replaceable_blocks": v["replaceable_blocks"]}})


def geode(name, outer, middle, inner, alt_inner, inner_placements, filling="air", crack=0.95):
    v = vanilla('worldgen/configured_feature/amethyst_geode.json')['config']
    c = json.loads(json.dumps(v))
    c["blocks"]["outer_layer_provider"] = simple(outer)
    c["blocks"]["middle_layer_provider"] = simple(middle)
    c["blocks"]["inner_layer_provider"] = simple(inner)
    c["blocks"]["alternate_inner_layer_provider"] = simple(alt_inner)
    c["blocks"]["filling_provider"] = simple(filling)
    c["blocks"]["inner_placements"] = inner_placements
    c["crack"]["generate_crack_chance"] = crack
    return cf(name, {"type": "minecraft:geode", "config": c})


def ore(name, block, size, target="end_stone", discard=0.0):
    return cf(name, {"type": "minecraft:ore", "config": {
        "size": size, "discard_chance_on_air_exposure": discard,
        "targets": [{"state": state(block),
                     "target": {"predicate_type": "minecraft:block_match", "block": "minecraft:" + target}}]}})


def lake(name, fluid, barrier, targets=("moss_block", "dirt", "end_stone", "mycelium", "terracotta",
                                        "packed_mud", "yellow_terracotta", "tuff", "rooted_dirt"),
         radius_min=4, radius_max=8, depth=2):
    """A pond: a disk of water sunk into the ground. Not minecraft:lake - that feature reads the
    biome around its spread and, at a chunk edge, asks for a chunk the generating region does
    not have, which is a hard crash during world generation."""
    return cf(name, {"type": "minecraft:disk", "config": {
        "half_height": depth,
        "radius": {"type": "minecraft:uniform", "min_inclusive": radius_min, "max_inclusive": radius_max},
        "state_provider": {"fallback": simple(fluid, level=0) if fluid == "water" else simple(fluid), "rules": []},
        "target": {"type": "minecraft:matching_blocks", "blocks": ["minecraft:" + t for t in targets]}}})


def column(name, provider, min_h, max_h, direction="up"):
    return cf(name, {"type": "minecraft:block_column", "config": {
        "direction": direction, "prioritize_tip": True,
        "allowed_placement": {"type": "minecraft:matching_blocks", "blocks": "minecraft:air"},
        "layers": [{"height": {"type": "minecraft:uniform", "min_inclusive": min_h, "max_inclusive": max_h},
                    "provider": provider}]}})


def disk(name, block, radius_min, radius_max, targets):
    return cf(name, {"type": "minecraft:disk", "config": {
        "half_height": 1,
        "radius": {"type": "minecraft:uniform", "min_inclusive": radius_min, "max_inclusive": radius_max},
        "state_provider": {"fallback": simple(block), "rules": []},
        "target": {"type": "minecraft:matching_blocks", "blocks": ["minecraft:" + t for t in targets]}}})


def lichen(name, block, can_place_on):
    return cf(name, {"type": "minecraft:multiface_growth", "config": {
        "block": "minecraft:" + block, "can_be_placed_on": ["minecraft:" + b for b in can_place_on],
        "can_place_on_ceiling": True, "can_place_on_floor": True, "can_place_on_wall": True,
        "chance_of_spreading": 0.5, "search_range": 12}})


def pile(name, provider):
    return cf(name, {"type": "minecraft:block_pile", "config": {"state_provider": provider}})


def hanging(block, probability, props=None):
    """A tree decorator that hangs a block under the leaves - lanterns, moss, petals."""
    s = {"Name": "minecraft:" + block}
    if props:
        s["Properties"] = props
    return {"type": "minecraft:attached_to_leaves", "probability": probability,
            "exclusion_radius_xz": 1, "exclusion_radius_y": 0, "required_empty_blocks": 1,
            "directions": ["down"],
            "block_provider": {"type": "minecraft:simple_state_provider", "state": s}}


# ============================================================================== biomes
#
# Each biome: BetterEnd counterpart, colours, palette, flora, ambience, mobs. The features
# list is built up per biome and referenced by id in the biome JSON's decoration steps.

BIOMES = {}
STEP_VEGETATION = 9
STEP_ORES = 6
STEP_LAKES = 1
STEP_LOCAL = 2
STEP_SURFACE_STRUCTURES = 4


def biome(name, *, counterpart, fog, water, water_fog, sky="#000000", top, sub, deep="end_stone",
          particle=None, loop=None, mood=None, additions=None, music=None,
          monsters=None, creatures=None, water_creatures=None, ambient=None,
          features=None, temperature=0.5, downfall=0.5, grass=None, foliage=None):
    steps = [[] for _ in range(11)]
    # Every biome carries the dragon's furniture: the spike feature only does anything in
    # the handful of chunks around the origin, so it is harmless everywhere else, and
    # whichever biome lands on the centre island still gets its obsidian pillars.
    steps[STEP_SURFACE_STRUCTURES] += ["minecraft:end_spike", "minecraft:end_gateway_return"]
    steps[10] += ["minecraft:end_platform"]
    for step, ids in (features or {}).items():
        steps[step] += ids
    attributes = {"minecraft:visual/fog_color": fog, "minecraft:visual/sky_color": sky,
                  "minecraft:visual/water_fog_color": water_fog}
    if particle:
        p, prob = particle
        attributes["minecraft:visual/ambient_particles"] = [{"particle": {"type": "minecraft:" + p},
                                                             "probability": prob}]
    sounds = {}
    if loop:
        sounds["loop"] = "minecraft:" + loop
    if mood:
        sounds["mood"] = {"sound": "minecraft:" + mood, "tick_delay": 6000,
                          "block_search_extent": 8, "offset": 2.0}
    if additions:
        sounds["additions"] = {"sound": "minecraft:" + additions, "tick_chance": 0.0111}
    if sounds:
        attributes["minecraft:audio/ambient_sounds"] = sounds
    if music:
        attributes["minecraft:audio/background_music"] = {"default": {
            "sound": "minecraft:" + music, "min_delay": 12000, "max_delay": 24000,
            "replace_current_music": False}}

    def spawner(entries):
        return [{"type": "minecraft:" + t, "weight": w, "minCount": lo, "maxCount": hi}
                for (t, w, lo, hi) in (entries or [])]

    effects = {"water_color": water}
    if grass:
        effects["grass_color"] = grass
    if foliage:
        effects["foliage_color"] = foliage
    BIOMES[name] = {
        "_counterpart": counterpart,
        "attributes": attributes,
        "carvers": [],
        "downfall": downfall,
        "effects": effects,
        "features": steps,
        "has_precipitation": False,
        "spawn_costs": {},
        "spawners": {
            "ambient": spawner(ambient), "axolotls": [],
            "creature": spawner(creatures), "misc": [],
            "monster": spawner(monsters or [("enderman", 10, 4, 4)]),
            "underground_water_creature": [],
            "water_ambient": [], "water_creature": spawner(water_creatures)},
        "temperature": temperature,
        "_palette": {"top": top, "sub": sub, "deep": deep},
    }


ENDERMEN = [("enderman", 10, 4, 4)]

# ---------------------------------------------------------------- Amber Land
f_helix = tree("helix_tree", "stripped_mangrove_log", "orange_stained_glass", "orange_terracotta",
               base=6, rand=4, radius=2, trunk="forking",
               decorators=[hanging("shroomlight", 0.08)], leaf_props={})
f_amber_ore = ore("amber_ore", "honeycomb_block", 6)
f_amber_grass = patch("amber_grass", weighted([("short_dry_grass", 3), ("tall_dry_grass", 1),
                                               (state("orange_tulip"), 1)]), tries=48)
biome("amber_land", counterpart="Amber Land",
      fog="#d0902c", water="#c77b1a", water_fog="#8a4d0a",
      top="orange_terracotta", sub="terracotta",
      particle=("falling_honey", 0.006), mood="ambient.cave", music="music.end",
      monsters=ENDERMEN + [("slime", 6, 1, 2)],
      features={STEP_ORES: [pf("amber_ore", f_amber_ore, underground(8, 20, 90))],
                STEP_VEGETATION: [pf("helix_trees", f_helix, surface(3, [AIR_HERE, on(["minecraft:orange_terracotta"])])),
                                  pf("amber_grass", f_amber_grass, surface(4))]})

# ---------------------------------------------------------- Blossoming Spires
f_tenanea = tree("tenanea_tree", "cherry_log", "cherry_leaves", "moss_block", base=7, rand=4,
                 radius=3, foliage_h=3, trunk="bending",
                 decorators=[hanging("pink_petals", 0.0, {"flower_amount": "1", "facing": "north", "segment_amount": "2"})])
f_petals = patch("petal_carpet", weighted([(state("pink_petals", flower_amount=3, segment_amount=3, facing="north"), 4),
                                           (state("pink_petals", flower_amount=1, segment_amount=1, facing="north"), 2),
                                           ("pink_tulip", 1), ("allium", 1)]), tries=64)
f_hanging_cherry = column("hanging_blossom", weighted([("cherry_leaves", 1)]), 1, 3, direction="down")
biome("blossoming_spires", counterpart="Blossoming Spires",
      fog="#f2a9d6", water="#e587c4", water_fog="#a0447e",
      top="moss_block", sub="rooted_dirt",
      particle=("cherry_leaves", 0.02), mood="ambient.cave", additions="ambient.cave", music="music.overworld.cherry_grove",
      monsters=ENDERMEN, creatures=[("bee", 8, 1, 3)],
      features={STEP_VEGETATION: [pf("tenanea_trees", f_tenanea, surface(4, [AIR_HERE, on(["minecraft:moss_block"])])),
                                  pf("petal_carpet", f_petals, surface(6))]})

# --------------------------------------------------------------- Chorus Forest
f_pythadendron = tree("pythadendron_tree", "stripped_crimson_stem", "purple_stained_glass", "purple_terracotta",
                      base=5, rand=3, radius=2, trunk="forking", leaf_props={},
                      decorators=[hanging("end_rod", 0.04, {"facing": "down"})])
f_chorus_dense = pf("chorus_dense", "minecraft:chorus_plant",
                    [{"type": "minecraft:count", "count": {"type": "minecraft:uniform", "min_inclusive": 2, "max_inclusive": 6}},
                     {"type": "minecraft:in_square"}, {"type": "minecraft:heightmap", "heightmap": "MOTION_BLOCKING"},
                     {"type": "minecraft:biome"}])
f_violet_grass = patch("violet_undergrowth", weighted([(state("large_fern", half="lower"), 1), ("fern", 3)]), tries=32)
biome("chorus_forest", counterpart="Chorus Forest",
      fog="#8b4fbf", water="#7a3fb0", water_fog="#3d1a5c",
      top="purple_terracotta", sub="end_stone",
      particle=("portal", 0.004), mood="ambient.cave", music="music.end",
      monsters=ENDERMEN + [("slime", 4, 1, 2)],
      features={STEP_VEGETATION: [pf("pythadendron_trees", f_pythadendron, surface(2, [AIR_HERE, on(["minecraft:purple_terracotta"])])),
                                  f_chorus_dense]})

# ------------------------------------------------------------ Crystal Mountains
f_crystal_geode = geode("crystal_geode", "smooth_basalt", "calcite", "amethyst_block", "budding_amethyst",
                        [state("small_amethyst_bud", facing="up", waterlogged=False),
                         state("medium_amethyst_bud", facing="up", waterlogged=False),
                         state("large_amethyst_bud", facing="up", waterlogged=False),
                         state("amethyst_cluster", facing="up", waterlogged=False)])
f_crystal_spires = column("crystal_spire", weighted([("amethyst_block", 5), ("calcite", 2), ("budding_amethyst", 1)]), 3, 9)
f_crystal_tips = patch("crystal_tips", weighted([(state("amethyst_cluster", facing="up", waterlogged=False), 3),
                                                 (state("large_amethyst_bud", facing="up", waterlogged=False), 2)]), tries=24, xz=6)
f_thallasium_rich = ore("thallasium_ore_rich", "lapis_ore", 9)
biome("crystal_mountains", counterpart="Crystal Mountains",
      fog="#c9b6ff", water="#a892ff", water_fog="#4b3a99",
      top="calcite", sub="smooth_basalt",
      particle=("electric_spark", 0.004), mood="ambient.cave", additions="block.amethyst_block.chime", music="music.end",
      monsters=ENDERMEN,
      features={STEP_ORES: [pf("crystal_geodes", f_crystal_geode, underground(1, 20, 80, rarity=6)),
                            pf("thallasium_rich", f_thallasium_rich, underground(10, 10, 100))],
                STEP_VEGETATION: [pf("crystal_spires", f_crystal_spires, surface(4)),
                                  pf("crystal_tips", f_crystal_tips, surface(3))]})

# ------------------------------------------------------------ Dragon Graveyards
f_grave_fungus = fungus("grave_fungus", "crimson_nylium", "crimson_stem", "nether_wart_block", "shroomlight")
f_bone_pillars = column("bone_pillar", weighted([("obsidian", 4), ("crying_obsidian", 1)]), 3, 8)
f_grave_bones = patch("grave_bones", weighted([(state("bone_block", axis="x"), 1), (state("bone_block", axis="z"), 1)]), tries=6, xz=5, y=1)
f_fireflies = patch("grave_fireflies", weighted([("firefly_bush", 1)]), tries=12)
biome("dragon_graveyards", counterpart="Dragon Graveyards",
      fog="#5c1a2c", water="#7a2a3a", water_fog="#3a0f1a",
      top="crimson_nylium", sub="blackstone",
      particle=("soul", 0.003), mood="ambient.soul_sand_valley.mood", loop="ambient.soul_sand_valley.loop", music="music.nether.soul_sand_valley",
      monsters=ENDERMEN,
      features={STEP_VEGETATION: [pf("grave_fungi", f_grave_fungus, [{"type": "minecraft:count_on_every_layer", "count": 3}, {"type": "minecraft:biome"}]),
                                  pf("bone_pillars", f_bone_pillars, surface(2)),
                                  pf("grave_bones", f_grave_bones, surface(2)),
                                  pf("grave_fireflies", f_fireflies, surface(2))]})

# ---------------------------------------------------------------- Dry Shrubland
f_shrubs = patch("rust_shrubs", weighted([("dead_bush", 3), ("short_dry_grass", 3), ("tall_dry_grass", 2),
                                          (state("mangrove_roots"), 1)]), tries=64)
f_lucernia_bush = tree("lucernia_bush", "stripped_dark_oak_log", "flowering_azalea_leaves", "terracotta",
                       base=2, rand=1, radius=2, foliage_h=2)
biome("dry_shrubland", counterpart="Dry Shrubland",
      fog="#b25a1e", water="#9a4a12", water_fog="#5a2a08",
      top="terracotta", sub="red_terracotta",
      mood="ambient.cave", music="music.overworld.badlands",
      monsters=ENDERMEN,
      features={STEP_VEGETATION: [pf("rust_shrubs", f_shrubs, surface(6)),
                                  pf("lucernia_bushes", f_lucernia_bush, surface(3, [AIR_HERE, on(["minecraft:terracotta"])]))]})

# --------------------------------------------------------------- Dust Wastelands
f_dust_gravel = disk("dust_gravel", "gravel", 3, 7, ["end_stone", "sandstone"])
f_dust_bones = patch("dust_bones", weighted([(state("bone_block", axis="y"), 1)]), tries=4, xz=6, y=1)
f_thallasium_dust = ore("thallasium_ore", "lapis_ore", 7)
biome("dust_wastelands", counterpart="Dust Wastelands",
      fog="#c9c26a", water="#b8b060", water_fog="#6b6630",
      top="sandstone", sub="end_stone",
      particle=("white_ash", 0.02), mood="ambient.cave", music="music.end",
      monsters=ENDERMEN,
      features={STEP_LOCAL: [pf("dust_gravel", f_dust_gravel, surface(2))],
                STEP_ORES: [pf("thallasium_ore", f_thallasium_dust, underground(12, 10, 100))],
                STEP_VEGETATION: [pf("dust_bones", f_dust_bones, surface(1, rarity=3))]})

# ------------------------------------------------------------ Foggy Mushroomland
f_glowshroom = fungus("mossy_glowshroom", "mycelium", "mushroom_stem", "brown_mushroom_block", "shroomlight")
f_fog_lake = lake("fog_lake", "water", "mossy_cobblestone")
f_small_shrooms = patch("small_shrooms", weighted([("brown_mushroom", 3), ("red_mushroom", 1)]), tries=32)
f_mushroom_lichen = lichen("mycelium_lichen", "glow_lichen", ["mushroom_stem", "brown_mushroom_block", "end_stone", "mycelium"])
biome("foggy_mushroomland", counterpart="Foggy Mushroomland",
      fog="#3b6fa3", water="#3f8fd6", water_fog="#1e4a7a",
      top="mycelium", sub="dirt",
      particle=("mycelium", 0.02), mood="ambient.cave", music="music.overworld.swamp",
      monsters=ENDERMEN + [("slime", 6, 1, 2)], ambient=[("bat", 10, 2, 4)],
      water_creatures=[("glow_squid", 10, 1, 2), ("cod", 8, 2, 4)],
      features={STEP_LAKES: [pf("fog_lakes", f_fog_lake, surface(None, rarity=4))],
                STEP_VEGETATION: [pf("mossy_glowshrooms", f_glowshroom, [{"type": "minecraft:count_on_every_layer", "count": 4}, {"type": "minecraft:biome"}]),
                                  pf("small_shrooms", f_small_shrooms, surface(4)),
                                  pf("mycelium_lichen", f_mushroom_lichen, surface(3))]})

# ------------------------------------------------------------- Glowing Grasslands
f_glow_grass = patch("glow_grass", weighted([("short_grass", 6), (state("tall_grass", half="lower"), 2), ("fern", 1)]), tries=64)
f_lantern_flowers = patch("lantern_flowers", weighted([("torchflower", 3), (state("end_rod", facing="up"), 2),
                                                       (state("pitcher_plant", half="lower"), 1)]), tries=24, xz=6)
f_grass_fireflies = patch("grass_fireflies", weighted([("firefly_bush", 1)]), tries=16)
f_moss_carpet = patch("moss_carpet", weighted([("moss_carpet", 1)]), tries=48)
biome("glowing_grasslands", counterpart="Glowing Grasslands",
      fog="#4fd4c4", water="#41c9c9", water_fog="#1f6b6b",
      top="moss_block", sub="dirt", grass="#7fe3c8", foliage="#7fe3c8",
      particle=("glow", 0.006), mood="ambient.cave", music="music.overworld.meadow",
      monsters=ENDERMEN,
      features={STEP_VEGETATION: [pf("glow_grass", f_glow_grass, surface(8)),
                                  pf("lantern_flowers", f_lantern_flowers, surface(3)),
                                  pf("grass_fireflies", f_grass_fireflies, surface(2)),
                                  pf("moss_carpet", f_moss_carpet, surface(2))]})

# ---------------------------------------------------------------- Lantern Woods
f_lucernia = tree("lucernia_tree", "mangrove_log", "flowering_azalea_leaves", "terracotta",
                  base=6, rand=3, radius=3, foliage_h=3, trunk="forking",
                  decorators=[hanging("lantern", 0.12, {"hanging": "true", "waterlogged": "false"})])
f_lantern_pond = lake("lantern_pond", "water", "mossy_cobblestone")
f_lilypads = patch("lilypads", weighted([("lily_pad", 1)]), tries=10)
biome("lantern_woods", counterpart="Lantern Woods",
      fog="#e08a2a", water="#d97a26", water_fog="#7a4212",
      top="terracotta", sub="packed_mud",
      particle=("falling_spore_blossom", 0.004), mood="ambient.cave", music="music.overworld.forest",
      monsters=ENDERMEN,
      features={STEP_LAKES: [pf("lantern_ponds", f_lantern_pond, surface(None, rarity=6))],
                STEP_VEGETATION: [pf("lucernia_trees", f_lucernia, surface(5, [AIR_HERE, on(["minecraft:terracotta"])])),
                                  pf("lilypads", f_lilypads, surface(1))]})

# --------------------------------------------------------------------- Megalake
f_megalake = lake("megalake", "water", "prismarine", radius_min=6, radius_max=8, depth=3)
f_lake_floor = disk("lake_floor", "prismarine", 3, 6, ["moss_block", "dirt", "end_stone"])
f_sea_lanterns = patch("lake_lanterns", weighted([("sea_lantern", 1)]), tries=4, xz=6, y=2)
f_pickles = patch("lake_pickles", weighted([(state("sea_pickle", pickles=3, waterlogged=True), 1)]), tries=8)
f_lacugrove = tree("lacugrove_tree", "mangrove_log", "azalea_leaves", "moss_block", base=8, rand=4,
                   radius=3, trunk="forking", decorators=[hanging("pale_hanging_moss", 0.1, {"tip": "true"})])
biome("megalake", counterpart="Megalake",
      fog="#6ab0d8", water="#2f9fd6", water_fog="#0b4a6b",
      top="moss_block", sub="dirt",
      particle=("bubble_column_up", 0.0), mood="ambient.underwater.loop.additions", loop="ambient.underwater.loop", music="music.overworld.swamp",
      monsters=ENDERMEN + [("slime", 5, 1, 2)], ambient=[("bat", 8, 1, 3)],
      water_creatures=[("glow_squid", 10, 1, 3), ("cod", 10, 2, 5)],
      features={STEP_LAKES: [pf("megalakes", f_megalake, surface(2, rarity=2))],
                STEP_LOCAL: [pf("lake_floor", f_lake_floor, surface(2))],
                STEP_VEGETATION: [pf("lacugrove_trees", f_lacugrove, surface(2, [AIR_HERE, on(["minecraft:moss_block"])])),
                                  pf("lake_lanterns", f_sea_lanterns, surface(2)),
                                  pf("lake_pickles", f_pickles, surface(2))]})

# ---------------------------------------------------------------- Shadow Forest
f_dragon_tree = tree("dragon_tree", "pale_oak_log", "pale_oak_leaves", "pale_moss_block",
                     base=7, rand=5, radius=3, foliage_h=4, trunk="forking",
                     decorators=[hanging("pale_hanging_moss", 0.2, {"tip": "true"})])
f_shadow_thorns = patch("shadow_thorns", weighted([("dead_bush", 2), (state("sweet_berry_bush", age=3), 1)]), tries=24)
f_shadow_moss = patch("shadow_moss", weighted([("pale_moss_carpet", 1)]), tries=48)
biome("shadow_forest", counterpart="Shadow Forest",
      fog="#0c0a14", water="#1d1a2e", water_fog="#05040a", sky="#000000",
      top="pale_moss_block", sub="rooted_dirt",
      particle=("ash", 0.01), mood="ambient.cave", loop="ambient.cave", music="music.overworld.deep_dark",
      monsters=ENDERMEN + [("wither_skeleton", 12, 1, 2)],
      features={STEP_VEGETATION: [pf("dragon_trees", f_dragon_tree, surface(6, [AIR_HERE, on(["minecraft:pale_moss_block"])])),
                                  pf("shadow_thorns", f_shadow_thorns, surface(3)),
                                  pf("shadow_moss", f_shadow_moss, surface(3))]})

# --------------------------------------------------------------- Sulphur Springs
f_geysers = cf("geyser_columns", {"type": "minecraft:basalt_columns", "config": {
    "height": {"type": "minecraft:uniform", "min_inclusive": 2, "max_inclusive": 6},
    "reach": {"type": "minecraft:uniform", "min_inclusive": 1, "max_inclusive": 3}}})
f_sulphur_pool = lake("sulphur_pool", "water", "magma_block")
f_sulphur_crust = disk("sulphur_crust", "yellow_concrete_powder", 2, 5, ["yellow_terracotta", "tuff"])
f_vents = patch("sulphur_vents", weighted([("magma_block", 1)]), tries=6, xz=5, y=1)
biome("sulphur_springs", counterpart="Sulphur Springs",
      fog="#d9c84a", water="#c9b83a", water_fog="#6b5f10",
      top="yellow_terracotta", sub="tuff",
      particle=("white_smoke", 0.01), mood="ambient.basalt_deltas.mood", loop="ambient.basalt_deltas.loop", music="music.nether.basalt_deltas",
      monsters=ENDERMEN, water_creatures=[("glow_squid", 6, 1, 2), ("cod", 6, 1, 3)],
      features={STEP_LAKES: [pf("sulphur_pools", f_sulphur_pool, surface(None, rarity=3))],
                STEP_LOCAL: [pf("sulphur_crust", f_sulphur_crust, surface(2))],
                STEP_VEGETATION: [pf("geysers", f_geysers, surface(2)),
                                  pf("sulphur_vents", f_vents, surface(2))]})

# ---------------------------------------------------------------- Ice Starfield
f_ice_star = geode("ice_star", "packed_ice", "blue_ice", "ice", "blue_ice",
                   [state("small_amethyst_bud", facing="up", waterlogged=False)],
                   filling="air", crack=0.2)
f_ice_spikes = cf("starfield_spikes", {"type": "minecraft:ice_spike", "config": {}})
f_snow = pile("starfield_snow", simple("snow", layers=2))
biome("ice_starfield", counterpart="Ice Starfield",
      fog="#e8f4ff", water="#9cd2ff", water_fog="#4f8fc4", sky="#000000",
      top="snow_block", sub="packed_ice", deep="packed_ice",
      particle=("snowflake", 0.02), mood="ambient.cave", music="music.overworld.frozen_peaks",
      monsters=ENDERMEN,
      features={STEP_LOCAL: [pf("ice_stars", f_ice_star, [{"type": "minecraft:rarity_filter", "chance": 2},
                                                          {"type": "minecraft:count", "count": 3},
                                                          {"type": "minecraft:in_square"},
                                                          {"type": "minecraft:height_range", "height": {"type": "minecraft:uniform", "min_inclusive": {"absolute": 30}, "max_inclusive": {"absolute": 110}}},
                                                          {"type": "minecraft:biome"}])],
                STEP_VEGETATION: [pf("starfield_spikes", f_ice_spikes, surface(3)),
                                  pf("starfield_snow", f_snow, surface(4))]},
      temperature=0.0)

# Thallasium ore appears in every biome at a modest rate, so the metal is never locked to one
# region; the Crystal Mountains and Dust Wastelands just have far more of it.
f_thallasium_common = ore("thallasium_ore_common", "lapis_ore", 5)
p_thallasium_common = pf("thallasium_common", f_thallasium_common, underground(4, 10, 100))
for b in BIOMES.values():
    b["features"][STEP_ORES].append(p_thallasium_common)

# ====================================================================== the hundred
#
# Fourteen places, each in eight colours. A variant keeps everything that makes its
# parent that kind of place - its flora, its ores, its mobs, its lakes - and changes
# what it is made of and what colour the air is. That is the honest way to get a
# hundred more End biomes out of fourteen: not a hundred new ideas, but every idea
# seen under a different sky, which is what the End is for.
#
# Nothing here needs a client mod. In the End there is no grass or foliage tint to
# lean on, so the colour has to come from the blocks themselves and from the fog,
# which 1.21.11 sends to the client as a biome attribute.

END_MOODS = {
    "violet":    ("Violet",    "#6b3f9c", "#7a4fd0", "#2f1a4a",
                  "purpur_block", "purpur_pillar", ("witch", 0.010)),
    "verdigris": ("Verdigris", "#2f8f7a", "#3fae9c", "#12463c",
                  "oxidized_copper", "weathered_copper", ("mycelium", 0.012)),
    "ember":     ("Ember",     "#a34a1f", "#c4522a", "#4a1c0a",
                  "blackstone", "basalt", ("lava", 0.004)),
    "bone":      ("Bone",      "#c9c4a3", "#b0aa88", "#544f38",
                  "bone_block", "calcite", ("white_ash", 0.020)),
    "abyss":     ("Abyssal",   "#22304a", "#1f3a6a", "#0c1424",
                  "deepslate", "tuff", ("ash", 0.014)),
    "gilded":    ("Gilded",    "#c9a83f", "#d8b84a", "#5a4a12",
                  "smooth_sandstone", "sandstone", ("end_rod", 0.006)),
    "rose":      ("Roseate",   "#c47a9c", "#d88fae", "#5a2f42",
                  "pink_terracotta", "white_terracotta", ("cherry_leaves", 0.014)),
    "glacial":   ("Glacial",   "#8fb4d8", "#7aa8e0", "#2f4a6a",
                  "packed_ice", "blue_ice", ("snowflake", 0.020)),
}

# Which moods each place is seen in, and in what order - the first is the one that
# looks most like the parent, so a cell reads as a gradient rather than a shuffle.
MOOD_ORDER = {
    "dust_wastelands":    ["bone", "gilded", "ember", "abyss", "violet", "rose",
                           "verdigris", "glacial"],
    "crystal_mountains":  ["glacial", "violet", "abyss", "verdigris", "bone", "rose",
                           "gilded", "ember"],
    "megalake":           ["abyss", "verdigris", "glacial", "violet", "rose", "bone",
                           "gilded", "ember"],
    "dry_shrubland":      ["gilded", "bone", "ember", "rose", "violet", "abyss",
                           "verdigris", "glacial"],
    "chorus_forest":      ["violet", "rose", "abyss", "verdigris", "bone", "gilded",
                           "ember", "glacial"],
    "foggy_mushroomland": ["verdigris", "abyss", "violet", "rose", "bone", "glacial",
                           "gilded", "ember"],
    "dragon_graveyards":  ["bone", "abyss", "ember", "violet", "gilded", "glacial",
                           "rose", "verdigris"],
    "glowing_grasslands": ["verdigris", "gilded", "violet", "rose", "glacial", "bone",
                           "abyss", "ember"],
    "blossoming_spires":  ["rose", "violet", "gilded", "verdigris", "bone", "glacial",
                           "abyss", "ember"],
    "sulphur_springs":    ["ember", "gilded", "bone", "abyss", "verdigris", "violet",
                           "rose", "glacial"],
    "amber_land":         ["gilded", "ember", "rose", "bone", "violet", "verdigris",
                           "abyss", "glacial"],
    "lantern_woods":      ["gilded", "violet", "rose", "verdigris", "abyss", "bone",
                           "ember", "glacial"],
    "shadow_forest":      ["abyss", "violet", "ember", "verdigris", "bone", "rose",
                           "gilded", "glacial"],
    "ice_starfield":      ["glacial", "abyss", "violet", "bone", "verdigris", "rose",
                           "gilded", "ember"],
}

# 14 places x 7 variants is 98; two places get an eighth so the total is a round 100.
EXTRA_EIGHTH = {"chorus_forest", "ice_starfield"}

VARIANTS = {}


def make_variants():
    """Clone each biome once per mood, recolouring it and swapping what it is made of."""
    made = 0
    for base in list(BIOMES):
        order = MOOD_ORDER.get(base, list(END_MOODS))
        count = 8 if base in EXTRA_EIGHTH else 7
        family = []
        for mood_key in order[:count]:
            adj, fog, water, water_fog, top, sub, particle = END_MOODS[mood_key]
            src = BIOMES[base]
            clone = json.loads(json.dumps(src))
            name = f"{mood_key}_{base}"

            clone["attributes"]["minecraft:visual/fog_color"] = fog
            clone["attributes"]["minecraft:visual/water_fog_color"] = water_fog
            clone["effects"]["water_color"] = water
            clone["attributes"]["minecraft:visual/ambient_particles"] = [
                {"particle": {"type": "minecraft:" + particle[0]},
                 "probability": particle[1]}]
            # a little of the parent's own ground survives, so the family still reads
            clone["_palette"] = {"top": top, "sub": sub,
                                 "deep": src["_palette"]["deep"]}
            clone["_counterpart"] = f'{adj} {src["_counterpart"]}'
            BIOMES[name] = clone
            family.append(name)
            made += 1
        VARIANTS[base] = family
    return made


NEW_BIOMES = make_variants()

# Music of its own, one track per mood, from the resource pack the mod hands out
# (beyond:music.beyond.<mood>; the base biomes take the Violet track). A client without the
# pack hears nothing in the End, which is why the pack is required.
for _name, _b in BIOMES.items():
    _mood = _name.split("_", 1)[0] if _name.split("_", 1)[0] in END_MOODS else "violet"
    _mood = {"abyss": "abyssal"}.get(_mood, _mood)   # the track is named after the adjective
    _b["attributes"]["minecraft:audio/background_music"] = {"default": {
        "sound": {"sound_id": f"beyond:music.beyond.{_mood}"}, "min_delay": 6000, "max_delay": 12000,
        "replace_current_music": False}}

# ========================================================================= write biomes
LAND = [n for n in BIOMES if n != "ice_starfield"]

for name, b in BIOMES.items():
    out = {k: v for k, v in b.items() if not k.startswith('_')}
    write(f'{NS}/worldgen/biome/{name}.json', out)
for name, data in configured.items():
    write(f'{NS}/worldgen/configured_feature/{name}.json', data)
for name, data in placed.items():
    write(f'{NS}/worldgen/placed_feature/{name}.json', data)

# Tags: the End's own machinery has to accept the new biomes, and end cities should still
# find somewhere to stand.
write('minecraft/tags/worldgen/biome/is_end.json',
      {"replace": False, "values": [f"{NS}:{n}" for n in BIOMES]})
write('minecraft/tags/worldgen/biome/has_structure/end_city.json',
      {"replace": False, "values": [f"{NS}:{n}" for n in LAND if n not in ("megalake", "sulphur_springs")]})

# ====================================================================== the dimension
#
# Fourteen biomes laid out on a temperature x humidity grid. The erosion axis is the vanilla
# End island function - high inside an island, low over the void - which is what puts the
# Ice Starfield everywhere the ground is not.
T = [(-1.0, -0.6), (-0.6, -0.2), (-0.2, 0.2), (0.2, 0.6), (0.6, 1.0)]
H = [(-1.0, -0.33), (-0.33, 0.33), (0.33, 1.0)]
GRID = [
    ["dust_wastelands", "crystal_mountains", "megalake"],
    ["dry_shrubland", "chorus_forest", "foggy_mushroomland"],
    ["dragon_graveyards", "glowing_grasslands", "blossoming_spires"],
    ["sulphur_springs", "amber_land", "lantern_woods"],
    ["shadow_forest", "shadow_forest", "lantern_woods"],
]
LAND_EROSION = [-0.22, 1.0]
VOID_EROSION = [-1.0, -0.22]

# Each (temperature, humidity) cell still belongs to one place, exactly as before; the
# weirdness axis inside it is divided between that place and its moods. So the map has
# the same shape it always had and the variants sit where their parent sits.

def weird_bands(n):
    step = 2.0 / n
    return [[round(-1.0 + i * step, 4), round(-1.0 + (i + 1) * step, 4)]
            for i in range(n)]


entries = []
for ti, row in enumerate(GRID):
    for hi, name in enumerate(row):
        here = [name] + VARIANTS.get(name, [])
        for band, who in zip(weird_bands(len(here)), here):
            entries.append({"biome": f"{NS}:{who}", "parameters": {
                "temperature": list(T[ti]), "humidity": list(H[hi]),
                "continentalness": [-1.0, 1.0], "erosion": LAND_EROSION,
                "weirdness": band, "depth": 0.0, "offset": 0.0}})

void = ["ice_starfield"] + VARIANTS.get("ice_starfield", [])
for band, who in zip(weird_bands(len(void)), void):
    entries.append({"biome": f"{NS}:{who}", "parameters": {
        "temperature": [-1.0, 1.0], "humidity": [-1.0, 1.0],
        "continentalness": [-1.0, 1.0], "erosion": VOID_EROSION,
        "weirdness": band, "depth": 0.0, "offset": 0.0}})

reachable = {e["biome"] for e in entries}
missing = {f"{NS}:{n}" for n in BIOMES} - reachable
if missing:
    raise SystemExit(f"{len(missing)} biomes unreachable: {sorted(missing)[:5]}")

write('minecraft/dimension/the_end.json', {
    "type": "minecraft:the_end",
    "generator": {"type": "minecraft:noise", "settings": f"{NS}:end",
                  "biome_source": {"type": "minecraft:multi_noise", "biomes": entries}}})

# ==================================================================== noise settings
#
# The vanilla End terrain, untouched, plus climate noises so multi-noise has something to
# read, plus a surface rule per biome.
ns = vanilla('worldgen/noise_settings/end.json')


def climate(noise, scale):
    return {"type": "minecraft:shifted_noise", "noise": "minecraft:" + noise,
            "shift_x": "minecraft:shift_x", "shift_y": 0.0, "shift_z": "minecraft:shift_z",
            "xz_scale": scale, "y_scale": 0.0}


ns["noise_router"]["temperature"] = climate("temperature", 0.16)
ns["noise_router"]["vegetation"] = climate("vegetation", 0.16)
ns["noise_router"]["continents"] = climate("continentalness", 0.16)
ns["noise_router"]["ridges"] = climate("ridge", 0.16)
# erosion stays the vanilla end_islands function; depth stays 0


def floor_rule(depth_offset, block):
    return {"type": "minecraft:condition",
            "if_true": {"type": "minecraft:stone_depth", "offset": depth_offset, "surface_type": "floor",
                        "add_surface_depth": False, "secondary_depth_range": 0},
            "then_run": {"type": "minecraft:block", "result_state": state(block)}}


rules = []
for name, b in BIOMES.items():
    pal = b["_palette"]
    seq = [floor_rule(0, pal["top"]), floor_rule(3, pal["sub"])]
    if pal["deep"] != "end_stone":
        seq.append({"type": "minecraft:block", "result_state": state(pal["deep"])})
    rules.append({"type": "minecraft:condition",
                  "if_true": {"type": "minecraft:biome", "biome_is": [f"{NS}:{name}"]},
                  "then_run": {"type": "minecraft:sequence", "sequence": seq}})
rules.append({"type": "minecraft:block", "result_state": state("end_stone")})
ns["surface_rule"] = {"type": "minecraft:sequence", "sequence": rules}
write(f'{NS}/worldgen/noise_settings/end.json', ns)

# ======================================================================= loot tables
IN_END = {"condition": "minecraft:location_check", "predicate": {"dimension": "minecraft:the_end"}}
NOT_END = {"condition": "minecraft:inverted", "term": IN_END}


def item(beyond_id, base, lo=1, hi=1, weight=1):
    """A vanilla item stamped with the mod's identity. The mod fills in name and stats."""
    e = {"type": "minecraft:item", "name": "minecraft:" + base, "weight": weight,
         "functions": [{"function": "minecraft:set_custom_data",
                        "tag": "{beyond_item:'%s'}" % beyond_id}]}
    if (lo, hi) != (1, 1):
        e["functions"].append({"function": "minecraft:set_count", "add": False,
                               "count": {"type": "minecraft:uniform", "min": float(lo), "max": float(hi)}})
    return e


def plain(base, lo=1, hi=1, weight=1):
    e = {"type": "minecraft:item", "name": "minecraft:" + base, "weight": weight}
    if (lo, hi) != (1, 1):
        e["functions"] = [{"function": "minecraft:set_count", "add": False,
                           "count": {"type": "minecraft:uniform", "min": float(lo), "max": float(hi)}}]
    return e


def pool(entries, rolls=1, conditions=None, bonus=0.0):
    p = {"rolls": rolls, "bonus_rolls": bonus, "entries": entries}
    if conditions:
        p["conditions"] = conditions
    return p


def wrap_vanilla(path, end_pools):
    """Keeps the vanilla table verbatim outside the End, and swaps in ours inside it."""
    v = vanilla('loot_table/' + path)
    for p in v.get("pools", []):
        p["conditions"] = p.get("conditions", []) + [NOT_END]
    for p in end_pools:
        p["conditions"] = p.get("conditions", []) + [IN_END]
    v["pools"] = v.get("pools", []) + end_pools
    write('minecraft/loot_table/' + path, v)


# Ores and mob drops only behave differently inside the End.
wrap_vanilla('blocks/lapis_ore.json', [pool([item("thallasium_dust", "prismarine_crystals", 2, 4)])])
wrap_vanilla('blocks/honeycomb_block.json', [pool([item("amber", "honeycomb", 1, 3)])])
wrap_vanilla('entities/cod.json', [pool([item("end_fish", "cod")])])
wrap_vanilla('entities/glow_squid.json', [pool([item("gelatine", "slime_ball", 1, 2)])])
wrap_vanilla('entities/bee.json', [pool([item("silk_fibre", "string", 1, 2)])])
wrap_vanilla('entities/wither_skeleton.json', [pool([item("shadow_essence", "echo_shard", 0, 1)])])

# Structure chests. Every one has an item that exists nowhere else.
CHESTS = {
    "violecite_ruin": [pool([item("chorus_lantern", "soul_lantern")]),
                       pool([plain("chorus_fruit", 3, 8, 10), plain("ender_pearl", 1, 3, 6), plain("purpur_block", 4, 12, 8),
                             item("thallasium_ingot", "iron_ingot", 1, 3, 5), plain("experience_bottle", 1, 3, 3)], rolls=4)],
    "crystal_shrine": [pool([item("crystal_focus", "prismarine_shard")]),
                       pool([plain("amethyst_shard", 4, 12, 10), item("thallasium_dust", "prismarine_crystals", 3, 6, 8),
                             plain("diamond", 1, 2, 3), plain("calcite", 6, 16, 6)], rolls=4)],
    "amber_vault": [pool([item("amber_heart", "heart_of_the_sea")]),
                    pool([item("amber", "honeycomb", 3, 8, 10), plain("gold_ingot", 2, 6, 6), plain("honey_bottle", 1, 2, 4),
                          item("thallasium_ingot", "iron_ingot", 2, 4, 5), plain("golden_apple", 1, 1, 2)], rolls=4)],
    "shadow_nest": [pool([item("veil_of_shadows", "phantom_membrane")]),
                    pool([item("shadow_essence", "echo_shard", 1, 3, 8), plain("wither_skeleton_skull", 1, 1, 2), plain("bone", 4, 10, 8),
                          plain("coal", 6, 14, 6), item("terminite_ingot", "copper_ingot", 1, 1, 2)], rolls=4)],
    "sunken_observatory": [pool([item("tidal_lens", "nautilus_shell")]),
                           pool([plain("prismarine_crystals", 3, 8, 8), plain("sea_lantern", 1, 3, 5), item("gelatine", "slime_ball", 2, 5, 6),
                                 item("end_fish", "cod", 2, 4, 6), plain("heart_of_the_sea", 1, 1, 1)], rolls=4)],
    "starfall_cairn": [pool([item("starfall_shard", "quartz")]),
                       pool([plain("blue_ice", 2, 6, 8), plain("packed_ice", 6, 16, 8), item("thallasium_ingot", "iron_ingot", 1, 2, 4),
                             plain("snowball", 8, 16, 5), plain("diamond", 1, 1, 2)], rolls=3)],
    "eternal_portal": [pool([item("amber", "honeycomb", 2, 4, 6), plain("ender_eye", 1, 2, 5), plain("obsidian", 4, 8, 6),
                             item("thallasium_ingot", "iron_ingot", 2, 5, 5)], rolls=3)],
    # The ten new cities share two tables: the common one you find in every spire, and
    # the one that is only in the places that were hard to reach.
    "end_city": [pool([plain("purpur_block", 4, 12, 10), plain("chorus_fruit", 2, 6, 8),
                       item("thallasium_ingot", "iron_ingot", 1, 3, 6),
                       plain("ender_pearl", 1, 2, 5), plain("iron_ingot", 2, 5, 6),
                       plain("gold_ingot", 1, 4, 5), plain("experience_bottle", 1, 3, 4),
                       plain("magenta_stained_glass", 4, 10, 4)], rolls=4)],
    "monument": [pool([plain("purpur_block", 6, 16, 10), plain("end_stone_bricks", 8, 20, 8),
                       item("thallasium_ingot", "iron_ingot", 2, 5, 6),
                       plain("ender_pearl", 2, 5, 6), plain("obsidian", 3, 8, 5),
                       plain("experience_bottle", 2, 6, 5), plain("chorus_fruit", 4, 10, 5)],
                      rolls=4)],
    "monument_deep": [pool([item("crystal_focus", "prismarine_shard", 1, 1, 2),
                            item("aeternium_ingot", "netherite_ingot", 1, 1, 1),
                            plain("diamond", 2, 5, 6), plain("emerald", 3, 8, 6),
                            plain("enchanted_golden_apple", 1, 1, 2),
                            plain("dragon_breath", 2, 5, 4),
                            plain("experience_bottle", 4, 12, 5)], rolls=4)],
    "end_city_treasure": [pool([item("crystal_focus", "prismarine_shard", 1, 1, 3),
                                plain("diamond", 1, 3, 6), plain("emerald", 2, 6, 6),
                                item("thallasium_ingot", "iron_ingot", 2, 5, 6),
                                plain("enchanted_golden_apple", 1, 1, 2),
                                plain("experience_bottle", 3, 9, 5),
                                plain("diamond_block", 1, 1, 1),
                                plain("dragon_breath", 1, 3, 3)], rolls=4)],
    # The two code-built boss halls: four chests each, worth the climb or the descent.
    "void_crypt": [pool([plain("sculk", 4, 12, 8), plain("echo_shard", 1, 3, 6), plain("soul_lantern", 1, 3, 5),
                         item("shadow_essence", "echo_shard", 1, 2, 5), item("terminite_ingot", "copper_ingot", 1, 2, 4),
                         plain("diamond", 1, 3, 5), plain("experience_bottle", 3, 8, 5),
                         plain("enchanted_golden_apple", 1, 1, 1)], rolls=4)],
    "storm_spire": [pool([plain("breeze_rod", 1, 3, 8), plain("wind_charge", 4, 12, 8), plain("copper_block", 2, 6, 5),
                          item("thallasium_ingot", "iron_ingot", 2, 5, 5), item("terminite_ingot", "copper_ingot", 1, 2, 4),
                          plain("diamond", 1, 3, 5), plain("experience_bottle", 3, 8, 5),
                          plain("heavy_core", 1, 1, 1)], rolls=4)],
}
for name, pools in CHESTS.items():
    write(f'{NS}/loot_table/chests/{name}.json', {"type": "minecraft:chest", "pools": pools})

# ========================================================================== recipes
#
# The Gale Rod is the only relic you can make. The result carries the mod's identity in
# custom_data and nothing else - name, lore and cooldown are stamped on by the item
# sweep, the same as for one pulled out of a chest.
write(f'{NS}/recipe/gale_rod.json', {
    "type": "minecraft:crafting_shaped",
    "category": "equipment",
    "pattern": ["B B",
                " N ",
                " S "],
    "key": {"B": "minecraft:breeze_rod",
            "N": "minecraft:netherite_ingot",
            "S": "minecraft:stick"},
    "result": {"id": "minecraft:breeze_rod", "count": 1,
               "components": {"minecraft:custom_data": {"beyond_item": "gale_rod"}}},
})
# Nothing in the game tells you a recipe exists, and the rod is not a new item a vanilla
# client could show in a creative tab - so holding a breeze rod unlocks it in the recipe
# book, the same way vanilla teaches its own.
write(f'{NS}/advancement/recipes/gale_rod.json', {
    "parent": "minecraft:recipes/root",
    "criteria": {"has_rod": {"trigger": "minecraft:inventory_changed",
                             "conditions": {"items": [{"items": "minecraft:breeze_rod"}]}}},
    "requirements": [["has_rod"]],
    "rewards": {"recipes": [f"{NS}:gale_rod"]},
})

# ===================================================================== enchantment
#
# 1.21 lets a data pack add a real enchantment. The description is a literal text
# component rather than a translation key on purpose: with no resource pack, a
# translation key would show up as "enchantment.beyond.fast_fly" on the item, and a
# literal shows up as the words.
write(f'{NS}/enchantment/fast_fly.json', {
    "description": {"text": "Fast Fly", "color": "light_purple"},
    "supported_items": "minecraft:elytra",
    "weight": 2,
    "max_level": 1,
    "min_cost": {"base": 20, "per_level_above_first": 0},
    "max_cost": {"base": 55, "per_level_above_first": 0},
    "anvil_cost": 6,
    "slots": ["chest"],
    "effects": {},
})
write('minecraft/tags/enchantment/non_treasure.json',
      {"replace": False, "values": [f"{NS}:fast_fly"]})

# ========================================================================== cities
#
# Ten more End cities on their own structure set, and vanilla's own moved from a
# spacing of 20 down to 11 - between the two, roughly four times as many cities.
import cities

CITY_TEMPLATES = cities.emit(write, NS, '#minecraft:has_structure/end_city')

# Twenty monuments: the big things, on their own spread so they stay landmarks.
import monuments

MONUMENT_TEMPLATES = monuments.emit(write, NS, '#minecraft:has_structure/end_city')

# Three castles: the wide things, walled complexes on the rarest spread of all.
import castles

CASTLE_TEMPLATES = castles.emit(write, NS, '#minecraft:has_structure/end_city')

# ====================================================================== advancements


def adv(name, parent, icon, title, desc, criteria, frame="task", background=None, announce=True, icon_data=None):
    ic = {"id": "minecraft:" + icon}
    if icon_data:
        ic["components"] = {"minecraft:custom_data": {"beyond_item": icon_data}}
    display = {"icon": ic, "title": title, "description": desc, "frame": frame,
               "show_toast": True, "announce_to_chat": announce, "hidden": False}
    if background:
        display["background"] = background
    d = {"display": display, "criteria": criteria, "requirements": [[k] for k in criteria]}
    if parent:
        d["parent"] = f"{NS}:{parent}"
    write(f'{NS}/advancement/{name}.json', d)


def in_biome(b):
    return {"trigger": "minecraft:location", "conditions": {"player": [{
        "condition": "minecraft:entity_properties", "entity": "this",
        "predicate": {"location": {"biomes": f"{NS}:{b}"}}}]}}


def granted():
    return {"trigger": "minecraft:impossible"}


adv('root', None, 'end_stone', 'Beyond the End', 'The End, remade',
    {"arrived": {"trigger": "minecraft:changed_dimension", "conditions": {"to": "minecraft:the_end"}}},
    background="minecraft:textures/block/end_stone_bricks.png", announce=False)
adv('amber_light', 'root', 'honeycomb', 'Amber Light', 'Walk under the twisting trees of the Amber Land', {"in": in_biome("amber_land")})
adv('quiet_forest', 'root', 'pale_oak_sapling', 'Something Is Following You', 'Set foot in the Shadow Forest', {"in": in_biome("shadow_forest")})
adv('crystal_clear', 'root', 'amethyst_cluster', 'Crystal Clear', 'Climb the Crystal Mountains', {"in": in_biome("crystal_mountains")})
adv('starfall', 'root', 'blue_ice', 'Starfall', 'Drift among the stars of the Ice Starfield', {"in": in_biome("ice_starfield")}, frame="goal")
adv('deep_water', 'root', 'sea_lantern', 'Deep Water', 'Swim in the Megalake', {"in": in_biome("megalake")})
adv('forge_lit', 'root', 'blast_furnace', 'The Forge Is Lit', 'Assemble an End Stone Smelter and open it', {"granted": granted()})
adv('thallasium', 'forge_lit', 'iron_ingot', 'Thallasium', 'Forge the first ingot of the End\'s own metal', {"granted": granted()}, icon_data="thallasium_ingot")
adv('terminite', 'thallasium', 'copper_ingot', 'Terminite', 'Forge Terminite - an alloy that laughs at diamond', {"granted": granted()}, icon_data="terminite_ingot")
adv('aeternium', 'terminite', 'netherite_ingot', 'Aeternium', 'Forge Aeternium. Nothing is harder.', {"granted": granted()}, frame="challenge", icon_data="aeternium_ingot")
adv('way_home', 'root', 'end_portal_frame', 'The Way Home', 'Light all six pedestals of an Eternal Portal', {"granted": granted()}, frame="goal")
adv('relic', 'root', 'chest', 'Relic Hunter', 'Recover a relic from one of the End\'s ruins', {"granted": granted()})

# The list /beyond tp and /beyond biomes offer. There are 114 of them now, far too many
# to keep by hand in the Java, and the command tree is built before the registries are
# readable - so the generator writes the names out and the command reads them back.
with open(os.path.join(ROOT, 'src', 'main', 'resources', 'beyond-biomes.txt'), 'w') as f:
    for name in sorted(BIOMES):
        f.write(name + '\n')

# The data pack's own metadata. 1.21.11 refuses a pack above format 81 without a range.
with open(os.path.join(ROOT, 'src', 'main', 'resources', 'pack.mcmeta'), 'w') as f:
    json.dump({"pack": {"pack_format": 94, "min_format": [94, 0], "max_format": [94, 99],
                        "description": "Beyond the End - the End, remade"}}, f, indent=2)
    f.write('\n')

print(f"biomes {len(BIOMES)}, configured features {len(configured)}, "
      f"placed features {len(placed)}, chests {len(CHESTS)}, "
      f"city templates {CITY_TEMPLATES}, monuments {MONUMENT_TEMPLATES}, "
      f"castles {CASTLE_TEMPLATES}")
