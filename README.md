# Beyond the End

A new End for **Minecraft 1.21.11 Fabric**: **114 biomes**, **38 kinds of structure** -
eleven kinds of End city, twenty monuments up to a hundred blocks tall, and seven ruins with
their own relics - three bosses worth going looking for, each with a relic only it drops, a
three-tier metal progression past netherite, new creatures, and a way home.

**Players install nothing.** Server-side only and dependency free — one jar in `mods/`, not
even Fabric API. Everyone joins with a completely vanilla client.

Built in the spirit of BetterEnd, and honest about the difference: a vanilla client cannot be
shown a block, item, mob or texture it does not have. So every biome is built from vanilla
blocks, every item is a vanilla item re-dressed, every creature is a vanilla mob in new
clothes. What the client *can* be sent — biomes, terrain, fog and water colours, particles,
sounds, music, structures, loot, chest screens — is all here.

Built and verified against a freshly downloaded 1.21.11 server, loader 0.19.5, empty
`mods/` — see [Testing](#testing).

---

## The biomes

**Fourteen places, in eight moods, 114 biomes.** The fourteen below are the places. Each one
is also generated in seven or eight *moods* - Violet, Verdigris, Ember, Bone, Abyssal,
Gilded, Roseate and Glacial - which keep the place's shape, its trees and its mobs but change
its fog, its water, its ground and the particles on the air. A Glacial Megalake is still a
megalake: packed ice and blue ice under blue-white fog, with the same lakes and the same
Cubozoa in them.

They are laid out on the End's climate so they form regions rather than a patchwork, and the
moods of one place sit next to each other along weirdness, so a long walk in one direction
crosses a family as a gradient rather than a shuffle. Every one of the 114 is reachable - the
generator asserts it, by checking no entry is shadowed out of the parameter list before it
writes anything.

The dragon's island keeps its pillars whichever biome lands on it.

| Biome | After BetterEnd's | What it is |
|---|---|---|
| **Amber Land** | Amber Land | Orange terracotta under twisting stripped-mangrove trees with amber-glass crowns lit by shroomlight. Amber veins in the rock. Amber fog. |
| **Blossoming Spires** | Blossoming Spires | Cherry trees on moss, petals drifting down. Silk Moths. Pink fog. |
| **Chorus Forest** | Chorus Forest | Purple ground, dense chorus, crimson-stemmed trees with violet crowns and end-rod fruit. Violecite ruins. |
| **Crystal Mountains** | Crystal Mountains | Calcite over basalt, amethyst spires and geodes, crystal tips underfoot. Rich in thallasium. |
| **Dragon Graveyards** | Dragon Graveyards | Crimson nylium, huge fungi, obsidian pillars, bone, fireflies. Soul-sand-valley ambience. |
| **Dry Shrubland** | Dry Shrubland | Terracotta, dry grass, dead bushes, low flowering shrubs. Rust fog. |
| **Dust Wastelands** | Dust Wastelands | Sandstone and gravel, bone, white ash on the air. The other thallasium field. |
| **Foggy Mushroomland** | Foggy Mushroomland | Mycelium, huge glowing mushrooms, lakes with Cubozoa and End Fish, Dragonflies. Blue fog. |
| **Glowing Grasslands** | Glowing Grasslands | Cyan-tinted moss and grass, torchflowers and end-rod blooms, fireflies. |
| **Lantern Woods** | Lantern Woods | Mangrove-and-azalea trees hung with lanterns, ponds with lily pads. Orange fog. |
| **Megalake** | Megalake | Great water lakes on moss, prismarine floors, sea lanterns, sea pickles, hanging-moss trees. |
| **Shadow Forest** | Shadow Forest | Pale oak and pale moss in near-black fog. Shadow Walkers. |
| **Sulphur Springs** | Sulphur Springs | Yellow terracotta and tuff, basalt geysers, magma vents, hot pools. Yellow fog, smoke. |
| **Ice Starfield** | Ice Starfield | The void between islands: stars of blue ice drifting at random heights, ice spikes and snow where there is ground. White fog. |

## The structures

Built block by block from vanilla blocks, placed on a seed-deterministic grid so the same
seed gives the same map.

### The seven ruins

One chest each, with **an item found nowhere else**.

| Structure | Where | The relic |
|---|---|---|
| **Violecite Ruin** | Chorus Forest, Dust Wastelands | **Chorus Lantern** — blink 8 blocks, no pearl, no damage |
| **Crystal Shrine** | Crystal Mountains | **Crystal Focus** — every monster within 20 blocks glows for 10 s |
| **Amber Vault** | Amber Land | **Amber Heart** — Regeneration II and Absorption |
| **Shadow Nest** | Shadow Forest | **Veil of Shadows** — 20 s of Invisibility |
| **Sunken Observatory** | Megalake, Foggy Mushroomland | **Tidal Lens** — Water Breathing and Conduit Power |
| **Starfall Cairn** | adrift in the Ice Starfield | **Starfall Shard** — Slow Falling and Speed |
| **Eternal Portal** | anywhere | the way home (below) |

### Eleven kinds of End city

Vanilla's End cities are rare and all the same. These are eleven different cities on a 14/6
grid, and **vanilla's own cities are pulled in to 11/5**, so the outer islands are worth
flying over at all.

| | What it is |
|---|---|
| **Spire City** | Purpur towers around one tall central spire |
| **Bridge City** | Towers joined across the gaps by bridges you can walk |
| **Hanging City** | Built downward from an overhang, on chains |
| **Wreck City** | A city that has already fallen, half of it into the void |
| **Crystal City** | Purpur and amethyst, lit from inside |
| **Library City** | Bookshelves, lecterns and chiseled bookshelves, floor on floor |
| **Drowned City** | Prismarine and water, sunk into its own island |
| **Beacon City** | A working beacon under a glass column |
| **Sail City** | Masts and banners, like something moored |
| **Gate City** | Built around an obsidian arch |
| **Throne City** | The King's hall, and a dragon egg on the dais |

Every one has loot, and each kind is built in three variants, so two cities of the same kind
are not the same building.

### Twenty monuments

Landmarks rather than loot - things you see from a long way off and fly towards. The tallest
run to about a hundred blocks, and each comes in two variants.

**Void Spire** (the tallest), **Watchspire**, **Obsidian Gate**, **Crystal Cathedral**,
**Starforge**, **Shulker Hive**, **Chorus Titan**, **Mausoleum of Wings**, **Shadow Keep**,
**Frozen Beacon**, **Amber Hall**, **Dragon Shrine**, **Dust Throne**, **Sunken Vault**,
**Enderman's Folly**, **Ring Monument**, **Bridgeway**, **Void Well**, **Pillar Field**,
**Shattered Hull**.

### Rivers

Rivers cross the bigger islands: a winding channel two deep, source water over a bed of
prismarine (packed ice in the cold moods) lit by sea lanterns, banks dressed in end stone
bricks with end rods, an arched footbridge at the halfway point, and where the island gives
out, the water simply **pours off the edge into the void**. They are carved by the mod
around players rather than generated, about one candidate in three on a 10-chunk grid
(`river_spacing_chunks`, `rivers_enabled`); `/beyond tp river` goes to the nearest.

### Three castles

The monuments are tall; these are wide - 75 to 90 blocks across, 40 to 45 high, on the
rarest spread of all (44/20 chunks), and every one is a complex you can walk end to end,
checked by `gen/walkcheck.py`, which floods a two-block-tall player through each template
from outside the gate and insists on reaching every chest, walkway, roof and tower top.
Three variants each.

| | What it is |
|---|---|
| **Obsidian Fortress** | Curtain walls of obsidian and blackstone behind a deepslate-lined moat, a twelve-block bridge to a gatehouse with a raised portcullis, four crying-obsidian corner towers on a walkway that runs the whole way round, and a three-floor keep - great hall, treasury with three chests, lord's chamber - with a tower on its roof. Barracks, a well and a market under wool awnings in the courtyard |
| **Purpur Citadel** | A stepped hill-fort: three terraces inside three rings of wall, each with a gatehouse and a ramp on a different side, gardens of chorus and amethyst on the terraces, corner towers joined by diagonal bridges in the air, and a domed palace of purpur stairs on top with a council chamber under the dome |
| **Bastion of Tides** | Prismarine walls that are an arcade of arches at their foot, built round a pool with a lighthouse on an islet in the middle, timber docks, four warehouses of barrels, and flooded halls under the whole courtyard - two blocks of water, sea lanterns in the floor, chests on plinths - reached by stairs down from the paving |

All three are sunk six rows into the ground so their foundations
never hang over a slope; the courtyard sits exactly on the surface.

**Every castle is garrisoned.** Ten named, persistent guards are placed on the walls and in
the courtyard the moment a castle is built (`castle_garrison`, `castle_garrison_enabled`):
the Obsidian Fortress has **Fortress Sentinels** (wither skeletons with stone swords) and
**Moat Wraiths** (phantoms over the towers); the Purpur Citadel **Citadel Knights**
(endermen) and **Citadel Sentries** (shulkers); the Bastion of Tides **Tide Guards**
(drowned with tridents) and **Bastion Wraiths**. They never despawn, so a castle is still
held when you come back for the chests you left.

## The Hollow King

**The boss halls cannot be broken.** Every block of the Throne City is protected: a survival player
cannot mine it, no explosion (TNT, creeper, wither skull, crystal, bed) takes a block out of it,
and a block-breaking mob - the boss itself included - leaves it standing. So the arena stays an
arena: no digging through the floor, no blowing a wall out to skip the fight. Creative mode is
exempt, so an operator can still edit one, and heads and skulls are always breakable - a dragon
head or a wither skeleton skull set into a hall is loot, and you can take it. Config:
`protect_boss_halls` (default true).


The End's own boss. Find a **Throne City**: there is a dragon egg on the dais, and using it
wakes him.

**Finding it.** Every player in the End has a **purple mark on their locator bar** pointing
at the nearest Throne City, the moment they arrive, with one line in chat saying how far and
which way. Turn until the mark is centred and go. `/throne` repeats the coordinates. It is
vanilla's own locator bar being told about a place instead of a player, so there is nothing
to install; `boss_marker` in the config turns it off. When the fight starts his own theme
plays for everyone within 128 blocks and stops when he falls.

He is a wither the client already knows how to draw, wearing a different name - which also
renames the boss bar, because the bar takes the entity's display name. Nine hundred health,
armour, and:

- **Under two thirds** he calls Throne Guards, shulkers and endermites, so the air above you
  stops being safe.
- **Under a third** he pulls you off the ground with Levitation and blinds you, so duelling
  him with a bow from a ledge stops working, and he starts mending himself unless you keep
  hitting him.

His guard dies with him, so the hall is not left full of shulkers.

He drops the **Wings of the Hollow King**: an elytra you can dash with. **Sneak while
gliding** and it throws you forward along your look - a vanilla client cannot be shown a new
control, so the input has to be one you already have. Ten seconds between dashes, or
**seven with Fast Fly**: a real data-driven enchantment for the chest slot, off an
enchanting table or an anvil like any other, whose name is a literal text component so a
client with no resource pack reads "Fast Fly" and not an enchantment id. (A config file
written by an older build is retuned from the old thirty seconds on first load, unless the
number was changed by hand.)

## The Void Warden

Sleeps under a **Void Crypt**: a low shrine of deepslate tiles on the surface, a spiral
shaft, and a chamber twelve blocks down floored in sculk, eight pillars, soul fire in the
corners, four alcoves with chests. The **sculk shrieker** on the dais is the alarm clock;
right-click it. The Warden is a warden with six hundred health and a boss bar the server
puts up for whoever is within sixty-four blocks (a warden has none of its own), and it is
made angrier at whoever is nearest every second so it never digs away from the fight.

- **Under two thirds** every eight seconds it pulls everyone near it in and darkens their
  sight, so keeping your distance stops being a plan.
- **Under a third** it calls **Void Mites**, steps through the void to whoever is farthest
  away, and mends itself unless you keep hitting it.

It drops the **Void Heart**: right-click to step up to sixteen blocks through the void along
your look, to solid footing, and land softly. Ten seconds between steps.

## The Gale Sovereign

Rides the wind above a **Storm Spire**: a tower of end stone bricks and purpur thirty-six
blocks tall with a spiral stair inside, and an open platform on top with a low rail, four
copper pylons with lanterns, four chests, and the **lightning rod** on the dais. Right-click
the rod. The Sovereign is a breeze with four hundred and fifty health and a boss bar, and it
fights the way a breeze does - leaping, shooting wind - and then some.

- **Under two thirds** every six seconds a gust throws everyone near it outward and upward.
  On a spire top, that is the point.
- **Under a third** it calls **Gale Wisps**, quickens, and mends itself unless you keep
  hitting it.

It drops the **Tempest Horn**: right-click for a blast of wind that throws everything within
eight blocks away from you, and slow falling for fifteen seconds so you can follow it off the
edge. Twenty seconds between blasts.

**Both halls are protected** like the Throne City (`protect_boss_halls`): no survival
mining, no explosion, no block-breaking mob. They grow on the islands the way the castles do,
one candidate per region of `hall_spacing_chunks` (48), the crypt or the spire by the
region's own roll; `/beyond build void_crypt` or `storm_spire` puts one down where you stand,
`/beyond locate` finds the nearest, and `/beyond boss <which>` wakes any of the three bosses
in front of you without the walk.

## The Gale Rod

The one relic you can make rather than find:

```
B _ B      B  breeze rod
_ N _      N  netherite ingot
_ S _      S  stick
```

Right-click and it throws you about twelve blocks straight up. It *replaces* your downward
motion rather than adding to it, so using it on the way down is a rescue and not a slightly
slower fall - though the fall it saves you from is still your own problem. Twenty seconds
between uses, shown on the item as the vanilla cooldown sweep. Holding a breeze rod unlocks
the recipe in the recipe book, because nothing else in the game would ever tell you it exists.

## The progression

Three metals, forged at the **End Stone Smelter**.

| Tier | Base | How |
|---|---|---|
| **Thallasium** | iron | three **Thallasium Dust**, mined from lapis-looking ore in End stone |
| **Terminite** | diamond | three Thallasium, an eye of ender, obsidian |
| **Aeternium** | netherite | Terminite + netherite + **Shadow Essence** from a Shadow Walker |

Every tier has the full tool set and armour set. Weapons hit softly on purpose — swords do
4 / 5 / 6, axes 5.5 / 6 / 7 (an iron sword does 6); what the tiers give you is armour,
mining speed and, for Aeternium, not burning. The **Aeternium Pickaxe mines 3×3** in the plane you face (sneak for one block);
the extra blocks go through the normal break path, so fortune, silk touch and durability
all apply, and it never takes anything harder than the block you hit or that it is the
wrong tool for. Stats are tooltip totals in `config/beyond.json`, and `/beyond reload` re-stats gear
already in inventories.

**The smelter is a shape, not a block**: a blast furnace on crying obsidian, with end stone
bricks on the four sides of the obsidian. Right-click the furnace and the mod's screen opens
instead of vanilla's — a six-row book of recipes, one per slot, price in the lore, green or
red for whether you can pay, click to forge. **A plain iron ingot does not pass for
Thallasium**: vanilla recipes match by item type, so every recipe involving End materials
lives here, where identity is checked properly.

## The way home

An Eternal Portal: an obsidian ring and six purpur pedestals, each topped with an end rod.
Forge an **Eternal Crystal** (Terminite, two Amber, an eye of ender), right-click a pedestal
with it, and the rod becomes a sea lantern. The sixth fills the ring with end portal blocks —
and an end portal in the End is vanilla's own way out.

## The creatures

| | Built on | Where | Drops |
|---|---|---|---|
| **Shadow Walker** | wither skeleton, unarmed, faster, tougher | Shadow Forest | Shadow Essence — and its touch **blinds** |

(The mod also carries the wither skeleton's loot table, so the Nether's wither skeletons drop
their **skull 40 % of the time** — 50/60/70 % with Looting I/II/III — instead of vanilla's 2.5 %.)
| **End Slime** | slime | Amber Land, Chorus Forest, Foggy Mushroomland, Megalake | |
| **Cubozoa** | glow squid | the lakes | Gelatine |
| **End Fish** | cod | the lakes | End Fish, a proper meal |
| **Silk Moth** | bee | Blossoming Spires | Silk Fibre |
| **Dragonfly** | bat | Foggy Mushroomland, Megalake | |

Drops are loot-table overrides that only apply **inside the End** — the same mobs in the
Overworld drop what they always did.

## Advancements

A tab of twelve: arriving, five biomes worth finding, lighting the forge, each metal, a relic,
and the way home.

---

## Install

1. Stop the server
2. `mods/` → `beyond-1.1.0.jar`. **That is the whole install.** No Fabric API.
3. Start it. The console prints:

```
Installed data pack: 384 files into <world>/datapacks/beyond
Beyond the End ready: 114 biomes in data, 44 items, 31 forge recipes, 7 structures
Registered /beyond
```

(The seven structures there are the seven ruins the Java half builds and locates. The cities
and the monuments are jigsaw structures in the data pack, and the world places those itself.)

**The End must be new.** Biomes only exist in chunks generated after the mod is installed. A
world whose End is already explored keeps its old End where it has been; new land beyond it
is the new End.

### Why it installs a data pack into the world

The biomes, terrain, flora, loot and advancements are data. Fabric Loader on its own does not
load the `data/` folder inside a mod jar — that is Fabric API's resource loader — and this
mod depends on nothing but the loader. So on every start, before the world opens, it copies
its data out of the jar into `<world>/datapacks/beyond/`, which the server enables on its
own. That is also how Nullscape and Terralith work, and the only place a dimension override
counts for a new world. Copied fresh each start, so an update never leaves stale data. Remove
the mod and the folder stays, and the world keeps its biomes.

## Commands

All level 2.

| | |
|---|---|
| `/beyond give <players> <item>` | any of the 46 items |
| `/beyond tp <biome>` | any of the 114, to the nearest one: on ground if there is any within 160 blocks, else on a small landing shard |
| `/beyond dash <players>` | fire the wings' dash without gliding - how the dash is tested |
| `/beyond locate <structure>` / `build <structure>` | nearest placed one / build one here - includes `void_crypt` and `storm_spire` |
| `/beyond seed [radius]` | a world generated before the mod gets everything it never grew within the radius (1,500 by default): ruins, portals, rivers, castles, boss halls through their own placement, and the jigsaw cities, monuments and Throne City at the cells their structure sets would have chosen. Loads chunks; idempotent |
| `/beyond boss hollow_king` / `void_warden` / `gale_sovereign` | wakes that boss four blocks in front of you |
| `/beyond forge` | open the smelter without the shape (staff); **`/forge`** does the same for everyone |
| `/beyond tp structure <id>` | the nearest jigsaw structure: any castle, city or monument, e.g. `obsidian_fortress`, `throne_city` |
| `/beyond tp river` | the nearest carved river |
| `/beyond sites`, `biomes`, `reload` | |

For everyone: `/throne` says where the Hollow King's throne is, and `/endmusic install`
sends the music pack.

## The resource pack: 3D items and music

`release/BeyondTheEnd-Pack.zip` (built by `pack/build_pack.py`) carries two things:

- **A 3D model for every item** — all 46: the three tiers of tools and armour, the
  materials and the relics — sculpted in `pack/models.py` as voxel models the way vanilla's
  trident is, one texture swatch sheet each. The mod stamps each item with
  `custom_model_data` `beyond:<id>` and the pack's item definitions pick the model by it;
  a client without the pack sees the plain base item as before. `pack/preview.html` shows
  them all (drag to turn).
- **The music** — see below.

It also folds in the **CustomWeapons** models (a snapshot in `pack/vendor/`): both mods
override the same five vanilla item files (iron/diamond/netherite sword, netherite axe and
hoe), a client keeps only one file per path, and this pack carries both sets of cases.
Point CustomWeapons' `pack_url` at this zip too if both mods run on the server.

**One pack for the whole server:** the CustomWeapons release zip carries these models and
the music as well, so `pack_url`/`pack_sha1` default to
`https://github.com/idkhowtonamemyselfasadev/customweapons/releases/download/v1.6.1/CustomWeapons-Models.zip`,
and when CustomWeapons is on the server this mod leaves the sending to it — players get one
download. Alone, this mod sends that same zip the way vanilla's `resource-pack` property would:
`pack_required` (on) kicks whoever declines with `pack_kick_message`, off it asks in chat
instead. Every rebuild of the pack changes the sha1 (printed by `build_pack.py`), so a new
pack means a new release asset and the new sha1 in the config.

## Music

The End has music of its own: nine tracks, one per mood (Violet, Verdigris, Ember, Bone,
Abyssal, Gilded, Roseate, Glacial) and the Hollow King's theme, composed in `music/` by
`compose.py` from nothing but a synthesiser, so there is nothing anyone can claim. They ship
in the pack above; with `pack_url` empty nothing is sent and the End is silent, because
every biome's music names a track from the pack.

## Config

`config/beyond.json`: every tier's damage, speed, armour, toughness, knockback resistance and
mining bonus; every relic's numbers and cooldown; structure and portal spacing; the Shadow
Walker's health, speed and damage; the Hollow King's health, armour, speed, mending and how
many guards he calls; the dash's strength and its two cooldowns; the Gale Rod's lift and
cooldown; the Void Warden's and Gale Sovereign's health, armour, mending and adds, the
Void Heart's range and the Tempest Horn's radius and force, `boss_halls_enabled` and
`hall_spacing_chunks`; `log_events`.

## Build

```bash
python3 gen/build_data.py        # wipes and rewrites everything under src/main/resources/data
JAVA_HOME=/home/tim/.gradle/jdks/eclipse_adoptium-21-amd64-linux.2 ./gradlew build
```

`gen/build_data.py` is the world. Biomes, features, surface rules, the dimension, tags, loot,
recipes and advancements are all generated from it, the cities, monuments and castles are built into
`.nbt` templates by `gen/cities.py`, `gen/monuments.py` and `gen/castles.py`, and nothing under `data/` is
hand-written - it is wiped and rebuilt every run, so a renamed file cannot linger. It reads
the vanilla 1.21.11 files out of the server jar for the shapes it copies, and it writes
`beyond-biomes.txt` beside them, which is the list `/beyond tp` and the test suite both read
so the 114 names live in exactly one place.

## Testing

```bash
bash run/test.sh
```

Downloads nothing it does not have: a stock 1.21.11 Fabric server launcher (loader 0.19.5),
a fresh world, **only this jar in `mods/`**, and one vanilla mineflayer client that:

- enters the End and confirms the dimension override took
- teleports to all **114 biomes** and has the *server* confirm it is standing in each
- finds structures that placed themselves while it explored (46 in the run)
- builds all **7 structures** and finds each one's chest
- assembles the smelter shape, opens it by right-clicking the furnace, forges an ingot from
  three dust, and confirms plain iron is refused
- uses a relic and moves 8 blocks
- crafts a **Gale Rod** in a real crafting table, right-clicks it, catches the 1.5
  blocks/tick upward velocity packet the server sends and the twenty-second refusal after it
  (`node test/galerod.js`)
- wakes the **Hollow King** from a dragon egg, checks that what woke is a King and not a
  plain wither, kills him and finds the wings in what drops (`node test/king.js`)
- builds an Eternal Portal, sets six crystals, and finds nine end portal blocks
- summons a wither skeleton in the Shadow Forest and finds a Shadow Walker
- builds a **Void Crypt** and a **Storm Spire**, confirms the dais block of each server-side,
  fails to mine a hall block in survival, wakes the **Void Warden** and the **Gale
  Sovereign** by using the dais block, reads their boss health off the server, kills each and
  finds the **Void Heart** and **Tempest Horn** in the drops, and fires both relics
- runs `/beyond seed 300` over the land already made and gets a reply with the server still up
- mines lapis ore in the End and gets Thallasium Dust, not lapis
- ends with **no exceptions** in the server log

### What building this taught

- **Without Fabric API, a mod's `data/` is not loaded.** The Java half worked and every
  data-driven half silently did nothing — no error, no "found data pack" line. The world
  data pack installer is the answer.
- **1.21.11 biome JSON moved colours, particles, sounds and music into an `attributes` map**
  (`minecraft:visual/fog_color`, `minecraft:visual/ambient_particles`,
  `minecraft:audio/ambient_sounds`, `minecraft:audio/background_music`), with colours as hex
  strings. The old `effects.fog_color` form is silently ignored.
- **The End's vanilla `erosion` router value is the island function**, so `erosion` in a
  multi-noise entry is "inside an island" versus "over the void". That is what makes the Ice
  Starfield the void between everything else.
- **A void biome's structure will be most of what generates** unless thinned: the first run
  placed 72 cairns against 25 of everything else.
- **mineflayer's 1.21.11 tables mis-read attribute modifiers**, and a screen of 31 items
  carrying them drifted into a crash. Icons carry no stats now; the real item does.
- **The biome finder samples every 32 blocks and block-level lookup jitters the edges**, so a
  point "in" a biome can read as its neighbour. Landing spots are checked at block level.
- **`minecraft:lake` crashes world generation at chunk edges** — it reads the biome around
  its 16-block spread and asks for a chunk the generating region does not have
  ("Requested chunk unavailable during world generation"). Every pond and lake here is a
  `minecraft:disk` of water sunk into the ground instead, which never looks outside its
  radius. A disk's radius is capped at 8.
- `/beyond build` places the structure eight blocks ahead of the player. Building it around
  them entombs them in it — the Crystal Shrine's spire suffocated the test bot.
- Entity classes moved: `animal.bee.Bee`, `animal.fish.Cod`, `animal.squid.GlowSquid`,
  `monster.skeleton.WitherSkeleton`. `ResourceKey.location()` is `identifier()`. There is no
  chiseled purpur. `MobSpawnType` is `EntitySpawnReason`, `moveTo` is `snapTo`, and the
  breeze's launch sound is `SoundEvents.BREEZE_JUMP`.
- **Python's `hash()` is salted per process**, so seeding a generator with it built a
  different set of cities and monuments on every run - a jar that changed size with no edit
  behind it. `zlib.crc32` is stable.
- **Nothing under `data/` was ever deleted**, only overwritten, so a file that moved
  namespace stayed behind and the server loaded both copies. The generator wipes `data/`
  before it writes now.
- **"Never used" has to be absence, not a sentinel.** The dash stored `Long.MIN_VALUE` for a
  player who had never dashed, and `tick - Long.MIN_VALUE` overflows negative, which reads as
  "still on cooldown" - so the very first dash was refused forever.
- **mineflayer drops an `entity_velocity` aimed at its own player**, so a headless bot never
  rises when the server launches it. The launch is checked as the packet the server sends,
  which is the whole of what the server does; a real client rises.
