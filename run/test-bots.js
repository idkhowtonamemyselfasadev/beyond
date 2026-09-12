// One vanilla client walks the new End: every biome, every structure, the forge, a relic, the
// portal, a creature, and a loot override. Assertions come from the server ("say" lines the
// bot hears, blocks the bot can see, items in its inventory), never from the harness's idea
// of what should have happened.
const mineflayer = require('/home/tim/claude/anticheat/test/node_modules/mineflayer');
const { Vec3 } = require('/home/tim/claude/anticheat/test/node_modules/vec3');
const fs = require('fs');

const RUN = __dirname;
const PORT = parseInt(process.env.PORT || '25609', 10);
const fifo = fs.createWriteStream(RUN + '/console.fifo', { flags: 'a' });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failures = 0;
const cmd = (c) => fifo.write(c + '\n');
const ok = (n, e = '') => console.log(`   PASS  ${n}${e ? '  ' + e : ''}`);
const fail = (n, e = '') => { failures++; console.log(`!! FAIL  ${n}${e ? '  ' + e : ''}`); };
const check = (c, n, e = '') => { c ? ok(n, e) : fail(n, e); return c; };

// The same list the mod reads, from the same file the generator writes - so a biome added
// to the generator is a biome this run has to visit, with nothing to keep in step by hand.
const BIOMES = require('fs')
  .readFileSync(require('path').join(__dirname, '..', 'src', 'main', 'resources', 'beyond-biomes.txt'), 'utf8')
  .split('\n').map((line) => line.trim()).filter(Boolean);
const STRUCTURES = ['violecite_ruin', 'crystal_shrine', 'amber_vault', 'shadow_nest', 'sunken_observatory',
  'starfall_cairn', 'eternal_portal'];

function connect(username) {
  return new Promise((resolve, reject) => {
    const bot = mineflayer.createBot({ host: '127.0.0.1', port: PORT, username, version: '1.21.11', auth: 'offline',
      checkTimeoutInterval: 180000 });   // the tour stalls the server while it places castles; do not give up at 30 s
    bot.chats = [];
    bot.log = [];          // never cleared: everything the bot was ever told
    bot.waypoints = [];    // clientbound tracked_waypoint packets (the locator bar mark)
    bot.packPushes = [];   // clientbound add_resource_pack packets, play or configuration phase
    bot.kicks = [];
    bot.on('message', (m, pos) => { const t = m.toString(); bot.chats.push(t); bot.log.push(t); });
    bot._client.on('tracked_waypoint', (p) => bot.waypoints.push(p));
    bot._client.on('add_resource_pack', (p) => bot.packPushes.push(p));
    bot.once('spawn', () => resolve(bot));
    bot.on('error', reject);
    bot.on('kicked', (r) => { bot.kicks.push(JSON.stringify(r)); reject(new Error('kicked: ' + JSON.stringify(r))); });
  });
}
const said = (bot, re) => bot.chats.some((m) => re.test(m));
const last = (bot, re) => bot.chats.filter((m) => re.test(m)).slice(-1)[0] || '';
const named = (item) => JSON.stringify(item && item.customName ? item.customName : '');
const itemsNamed = (bot, re) => bot.inventory.items().filter((i) => re.test(named(i)));

async function main() {
  console.log('== connecting ==');
  const bot = await connect('Explorer');
  await sleep(1500);
  cmd('op Explorer');
  cmd('gamerule keep_inventory true');
  await sleep(1500);

  // ------------------------------------------------------------- 1. into the End
  console.log('\n== 1. entering the End ==');
  bot.chats.length = 0;
  cmd('execute in minecraft:the_end run tp Explorer 100 80 0');
  // A cold End takes the server a while to generate; ask until it answers (up to 30 s).
  for (let i = 0; i < 10 && !said(bot, /IN_END/); i++) {
    await sleep(3000);
    cmd('execute as Explorer at @s if dimension minecraft:the_end run say IN_END');
    await sleep(1000);
  }
  check(said(bot, /IN_END/), 'the End loaded with the mod\'s dimension override');

  // ----------------------------------------------------- 1b. the throne locator
  console.log('\n== 1b. the locator bar points at the Hollow King\'s throne ==');
  // An enderman once slew the bot during this wait; it respawned in the Overworld and /throne
  // rightly said the King waits in the End. The check is about the locator, not survival.
  cmd('effect give Explorer minecraft:resistance 120 4 true');
  await sleep(10000);   // BossLocator looks every 40 ticks, and the structure search is not instant
  const wp = bot.waypoints[0];
  check(!!wp, 'a tracked_waypoint packet arrived after entering the End', wp ? JSON.stringify(wp).slice(0, 200) : '');
  if (wp) {
    check(wp.operation === 'track' && wp.waypoint && wp.waypoint.type === 'vec3i',
        'the waypoint is a tracked block position', `operation=${wp.operation} type=${wp.waypoint && wp.waypoint.type}`
        + ` icon=${wp.waypoint && wp.waypoint.icon && wp.waypoint.icon.style} data=${JSON.stringify(wp.waypoint && wp.waypoint.data)}`);
  }
  check(bot.log.some((m) => /Hollow King's throne lies/.test(m)), 'and chat told the player once where the throne lies',
      bot.log.filter((m) => /Hollow King's throne/.test(m)).slice(-1)[0] || '');
  bot.chats.length = 0;
  cmd('execute as Explorer at @s if dimension minecraft:the_end run say STILL_IN_END');
  await sleep(1500);
  if (!said(bot, /STILL_IN_END/)) {
    console.log('   (the bot left the End - ' + (last(bot, /Explorer/) || 'died?') + ' - sending it back before /throne)');
    cmd('execute in minecraft:the_end run tp Explorer 100 80 0');
    await sleep(4000);
  }
  bot.chats.length = 0;
  bot.chat('/throne');
  await sleep(3000);
  check(said(bot, /The Hollow King's throne:/), '/throne answers with the throne\'s position',
      last(bot, /Hollow King|Throne City|waits in the End/).slice(0, 100));

  // -------------------------------------------------------------- 2. every biome
  console.log('\n== 2. every biome generates and can be reached ==');
  // Creative for the tour: a landing on a shard while the server stalls placing a castle
  // otherwise reads as flying and gets a survival client kicked mid-way. Back to survival
  // for everything after, which is what the later checks assume.
  cmd('gamemode creative Explorer');
  const found = [];
  const where = [];   // [x, z] of every biome reached, to search again from somewhere else
  const tpTo = async (biome) => {
    bot.chats.length = 0;
    bot.chat('/beyond tp ' + biome);
    // Wait until the client has actually arrived where the server says it sent us.
    let tpLine = '';
    for (let i = 0; i < 12; i++) {
      await sleep(1000);
      tpLine = last(bot, /Teleported to beyond:|No .* within/);
      const m = /at (-?\d+) (-?\d+) (-?\d+)/.exec(tpLine);
      if (m && Math.abs(bot.entity.position.x - (+m[1])) < 4 && Math.abs(bot.entity.position.z - (+m[3])) < 4) break;
    }
    return tpLine;
  };
  for (const biome of BIOMES) {
    let tpLine = await tpTo(biome);
    // The search is 6400 blocks from where the bot stands; a rare biome can be just outside
    // that, so look again from the biome reached farthest from here before giving up.
    if (/No .* within/.test(tpLine) && where.length) {
      const here = bot.entity.position;
      const far = where.slice().sort((a, b) => Math.hypot(b[0] - here.x, b[1] - here.z) - Math.hypot(a[0] - here.x, a[1] - here.z))[0];
      cmd(`execute in minecraft:the_end run tp Explorer ${far[0]} 80 ${far[1]}`);
      await sleep(3000);
      tpLine = await tpTo(biome);
    }
    await sleep(1500);
    let here = false;
    // Up to 12 s: a code-placed castle or portal next to the landing can stall the server
    // for ten seconds (the chunks it needs are generated synchronously), and a biome the bot
    // is standing in must not read as unreachable because the answer came late.
    for (let attempt = 0; attempt < 8 && !here; attempt++) {
      cmd(`execute as Explorer at @s if biome ~ ~ ~ beyond:${biome} run say BIOME_OK ${biome}`);
      await sleep(1500);
      here = said(bot, new RegExp('BIOME_OK ' + biome));
    }
    console.log(`   ${biome.padEnd(26)} ${tpLine.slice(0, 70)} ${here ? '  standing in it' : ''}`);
    if (here) { found.push(biome); where.push([Math.round(bot.entity.position.x), Math.round(bot.entity.position.z)]); }
    await sleep(2500);   // let the structure scan see this region
  }
  check(found.length === BIOMES.length, `all ${BIOMES.length} biomes reachable and confirmed server-side`,
      `${found.length}/${BIOMES.length}`);

  // ------------------------------------------------------ 3. structures generated
  cmd('gamemode survival Explorer');
  await sleep(500);
  console.log('\n== 3. structures generated on their own while exploring ==');
  bot.chats.length = 0;
  bot.chat('/beyond sites');
  await sleep(2000);
  const sitesLine = last(bot, /structure\(s\) placed/);
  console.log('   ' + sitesLine);
  console.log('   ' + bot.chats.filter((m) => / - /.test(m)).slice(0, 12).join(' | '));
  check(/[1-9]\d* structure/.test(sitesLine), 'at least one structure placed itself near a visited biome', sitesLine);

  // ---------------------------------------------------- 4. build every structure
  console.log('\n== 4. every structure builds, with its chest ==');
  // A platform is made under each spot while standing nearby, so the chunks are loaded and
  // the bot never has void under it.
  const pad = async (x, z, r) => {
    cmd(`execute in minecraft:the_end run forceload add ${x - r} ${z - r} ${x + r} ${z + r}`);
    await sleep(1500);
    cmd(`execute in minecraft:the_end run fill ${x - r} 70 ${z - r} ${x + r} 70 ${z + r} minecraft:end_stone`);
    cmd(`execute in minecraft:the_end run fill ${x - r} 71 ${z - r} ${x + r} 84 ${z + r} minecraft:air`);
    await sleep(1500);
    cmd(`execute in minecraft:the_end run tp Explorer ${x} 72 ${z}`);
    await sleep(2500);
  };
  const markers = { violecite_ruin: 'purpur_pillar', crystal_shrine: 'amethyst_block', amber_vault: 'honeycomb_block',
    shadow_nest: 'pale_oak_log', sunken_observatory: 'prismarine_bricks', starfall_cairn: 'blue_ice', eternal_portal: 'crying_obsidian' };
  for (const type of STRUCTURES) {
    await pad(300 + STRUCTURES.indexOf(type) * 40, 300, 14);
    bot.chats.length = 0;
    bot.chat('/beyond build ' + type);
    await sleep(3500);
    const marker = bot.findBlock({ matching: (b) => b.name === markers[type], maxDistance: 14 });
    const chest = bot.findBlock({ matching: (b) => b.name === 'chest', maxDistance: 14 });
    check(!!marker && !!chest, `${type} built with its chest`,
        `${marker ? markers[type] : 'no ' + markers[type]}, ${chest ? 'chest' : 'no chest'}  ${last(bot, /Built/)}`);
  }

  // ---------------------------------------------------------------- 5. the forge
  console.log('\n== 5. the End Stone Smelter ==');
  await pad(500, 500, 10);
  cmd('execute in minecraft:the_end run setblock 503 71 500 minecraft:crying_obsidian');
  for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
    cmd(`execute in minecraft:the_end run setblock ${503 + dx} 71 ${500 + dz} minecraft:end_stone_bricks`);
  }
  cmd('execute in minecraft:the_end run setblock 503 72 500 minecraft:blast_furnace');
  cmd('clear Explorer');
  for (let i = 0; i < 3; i++) cmd('beyond give Explorer thallasium_dust');
  await sleep(3000);
  const furnace = bot.findBlock({ matching: (b) => b.name === 'blast_furnace', maxDistance: 8 });
  check(!!furnace, 'the forge shape is in place');
  if (furnace) {
    await bot.activateBlock(furnace);
    await sleep(2500);
    const title = bot.currentWindow ? JSON.stringify(bot.currentWindow.title) : '';
    check(/End Stone Smelter/.test(title), 'right-clicking the furnace opens the forge, not vanilla\'s', title.slice(0, 80));
    if (bot.currentWindow) {
      const slot0 = bot.currentWindow.slots[0];
      console.log('   slot 0: ' + named(slot0) + ' lore lines: ' + ((slot0 && slot0.components || []).length));
      await bot.clickWindow(0, 0, 0);
      await sleep(2000);
      bot.closeWindow(bot.currentWindow);
      await sleep(1500);
    }
  }
  const ingots = itemsNamed(bot, /Thallasium Ingot/);
  const dust = itemsNamed(bot, /Thallasium Dust/);
  check(ingots.length === 1, 'three dust became one Thallasium Ingot', `${ingots.length} ingot(s), ${dust.length} dust left`);
  check(dust.length === 0, 'and the dust was taken');
  cmd('execute if entity @a[name=Explorer,advancements={beyond:thallasium=true}] run say ADV_THALLASIUM');
  cmd('execute if entity @a[name=Explorer,advancements={beyond:forge_lit=true}] run say ADV_FORGE');
  await sleep(1500);
  check(said(bot, /ADV_FORGE/) && said(bot, /ADV_THALLASIUM/), 'the forge advancements were granted');

  // The Aeternium Pickaxe mines 3x3: a fresh pad, a 3x3 stone wall two blocks east of the
  // bot, break the centre, all nine must go; sneaking breaks one. Obsidian in the wall stays
  // (harder than the block hit). Console commands run in the overworld unless told otherwise.
  {
    await pad(560, 500, 10);
    const E = 'execute in minecraft:the_end run ';
    const wx = 562, wy = 71, wz = 500;   // wall column x, bottom row y, centre z; the bot stands at 560, feet on 71
    const wallCmd = () => cmd(`${E}fill ${wx} ${wy} ${wz - 1} ${wx} ${wy + 2} ${wz + 1} minecraft:stone`);
    wallCmd();
    cmd(`${E}setblock ${wx} ${wy + 2} ${wz + 1} minecraft:obsidian`);
    cmd('clear Explorer'); cmd('beyond give Explorer aeternium_pickaxe'); cmd('gamemode survival Explorer');
    await sleep(1500);
    await bot.look(-Math.PI / 2, 0, true);   // mineflayer yaw -PI/2 faces +x
    await sleep(300);
    const dig = async (b) => { try { await Promise.race([bot.dig(b), sleep(8000)]); } catch (e) { console.log('   dig: ' + e.message); } };
    const centre = () => bot.blockAt(new Vec3(wx, wy + 1, wz));
    console.log('   wall centre reads as ' + ((centre() || {}).name));
    if (centre() && centre().name === 'stone') await dig(centre());
    await sleep(1500);
    cmd(`${E}execute if block ${wx} ${wy + 1} ${wz} minecraft:air if block ${wx} ${wy} ${wz - 1} minecraft:air if block ${wx} ${wy + 2} ${wz - 1} minecraft:air if block ${wx} ${wy} ${wz + 1} minecraft:air if block ${wx} ${wy + 1} ${wz + 1} minecraft:air run say AREA_OK`);
    cmd(`${E}execute if block ${wx} ${wy + 2} ${wz + 1} minecraft:obsidian run say OBS_STAYS`);
    await sleep(1200);
    check(said(bot, /AREA_OK/), 'the Aeternium Pickaxe mines 3x3 (stone wall gone)');
    check(said(bot, /OBS_STAYS/), 'but leaves the obsidian, harder than the block hit');
    wallCmd();
    await sleep(1000);
    bot.setControlState('sneak', true);
    await sleep(300);
    if (centre() && centre().name === 'stone') await dig(centre());
    bot.setControlState('sneak', false);
    await sleep(1200);
    cmd(`${E}execute if block ${wx} ${wy + 1} ${wz} minecraft:air if block ${wx} ${wy + 2} ${wz} minecraft:stone if block ${wx} ${wy + 1} ${wz + 1} minecraft:stone run say SNEAK_OK`);
    await sleep(1200);
    check(said(bot, /SNEAK_OK/), 'sneaking mines a single block');
    cmd(`${E}fill ${wx} ${wy} ${wz - 1} ${wx} ${wy + 2} ${wz + 1} minecraft:air`);
    cmd('clear Explorer');   // the bot stays in survival, as the rest of the walk expects
    await sleep(800);
    await pad(500, 500, 10);   // back beside the forge for the /forge check
  }

  // /forge opens the same screen for a plain player, no shape and no op needed.
  cmd('deop Explorer');
  await sleep(800);
  bot.chat('/forge');
  await sleep(2500);
  const forgeTitle = bot.currentWindow ? JSON.stringify(bot.currentWindow.title) : '';
  check(/End Stone Smelter/.test(forgeTitle), '/forge opens the smelter for a non-op player', forgeTitle.slice(0, 80));
  if (bot.currentWindow) { bot.closeWindow(bot.currentWindow); await sleep(800); }
  cmd('op Explorer');
  await sleep(800);

  // A plain iron ingot must not pass for Thallasium.
  cmd('clear Explorer');
  cmd('give Explorer minecraft:iron_ingot 3');
  cmd('give Explorer minecraft:stick 1');
  await sleep(2000);
  if (furnace) {
    await bot.activateBlock(furnace);
    await sleep(2000);
    if (bot.currentWindow) {
      await bot.clickWindow(9, 0, 0);   // first Thallasium gear slot: the sword (2 ingots + stick)
      await sleep(1500);
      bot.closeWindow(bot.currentWindow);
      await sleep(1000);
    }
  }
  check(itemsNamed(bot, /Thallasium Sword/).length === 0, 'plain iron ingots do not forge Thallasium gear');

  // ------------------------------------------------------------------- 6. relic
  console.log('\n== 6. a relic ability ==');
  cmd('clear Explorer');
  cmd('beyond give Explorer chorus_lantern');
  await sleep(2000);
  const lantern = itemsNamed(bot, /Chorus Lantern/)[0];
  check(!!lantern, 'the relic arrives named');
  if (lantern) {
    await bot.equip(lantern, 'hand');
    await bot.look(0, 0, true);
    const before = bot.entity.position.clone();
    bot.chats.length = 0;
    bot.activateItem();
    await sleep(2500);
    const moved = bot.entity.position.distanceTo(before);
    check(said(bot, /Chorus Lantern/), 'the ability reports on the action bar', last(bot, /Chorus/));
    check(moved > 2, 'the blink actually moved the player', `${moved.toFixed(1)} blocks`);
  }
  cmd('execute if entity @a[name=Explorer,advancements={beyond:relic=true}] run say ADV_RELIC');
  await sleep(1500);
  check(said(bot, /ADV_RELIC/), 'holding a relic granted Relic Hunter');

  // ------------------------------------------------------------------ 7. portal
  console.log('\n== 7. the Eternal Portal ==');
  await pad(700, 700, 20);
  bot.chat('/beyond build eternal_portal');
  await sleep(3500);
  cmd('clear Explorer');
  for (let i = 0; i < 6; i++) cmd('beyond give Explorer eternal_crystal');
  await sleep(2500);
  const crystals = itemsNamed(bot, /Eternal Crystal/);
  check(crystals.length >= 1, 'six Eternal Crystals in hand', `${crystals.reduce((n, i) => n + i.count, 0)}`);
  const rods = bot.findBlocks({ matching: (b) => b.name === 'end_rod', maxDistance: 16, count: 20 });
  check(rods.length >= 6, 'six pedestals stand around the ring', `${rods.length} end rods`);
  let lit = 0;
  for (const rodPos of rods.slice(0, 6)) {
    const held = itemsNamed(bot, /Eternal Crystal/)[0];
    if (!held) break;
    await bot.equip(held, 'hand');
    bot.chats.length = 0;
    const pedestal = bot.blockAt(rodPos.offset(0, -1, 0));
    cmd(`execute in minecraft:the_end run tp Explorer ${rodPos.x + 0.5} 72 ${rodPos.z + 1.5}`);
    await sleep(1200);
    await bot.activateBlock(pedestal);
    await sleep(1500);
    if (said(bot, /pedestals lit|way home opens/)) lit++;
  }
  console.log(`   lit ${lit} pedestal(s); last: ${last(bot, /lit|way home/)}`);
  await sleep(1500);
  const portalBlocks = bot.findBlocks({ matching: (b) => b.name === 'end_portal', maxDistance: 16, count: 20 });
  check(lit === 6, 'all six pedestals took a crystal', `${lit}`);
  check(portalBlocks.length >= 9, 'and the ring filled with end portal blocks', `${portalBlocks.length}`);
  cmd('execute if entity @a[name=Explorer,advancements={beyond:way_home=true}] run say ADV_HOME');
  await sleep(1500);
  check(said(bot, /ADV_HOME/), 'The Way Home was granted');

  // ----------------------------------------------------------------- 8. creature
  console.log('\n== 8. a Shadow Walker ==');
  bot.chats.length = 0;
  bot.chat('/beyond tp shadow_forest');
  await sleep(4500);
  // A bot worn down by a hundred landings dies to the first hit, respawns in the Overworld,
  // and then nothing below happens in the End. Patch it up first; the check is about the
  // walker's name and tag, not about the damage.
  cmd('effect give Explorer minecraft:instant_health 1 4 true');
  cmd('effect give Explorer minecraft:resistance 30 3 true');
  await sleep(500);
  cmd('execute in minecraft:the_end as Explorer at @s run summon minecraft:wither_skeleton ~ ~ ~');
  await sleep(2000);
  cmd('execute in minecraft:the_end run execute if entity @e[type=minecraft:wither_skeleton,name="Shadow Walker",tag=beyond_shadow_walker] run say WALKER_OK');
  await sleep(1500);
  check(said(bot, /WALKER_OK/), 'a wither skeleton in the Shadow Forest becomes a Shadow Walker');
  cmd('execute in minecraft:the_end run kill @e[type=minecraft:wither_skeleton]');

  // ------------------------------------------------ 8b. the two new halls and their bosses
  // Each hall is built by command on a pad, its dais block is found, and using that block
  // wakes the boss: the server says which entity woke and with what health. Killing it must
  // drop its relic, named. Then the halls' footprint is protected like the Throne City.
  console.log('\n== 8b. the Void Crypt, the Storm Spire, and what sleeps in them ==');
  const bosses = [
    { hall: 'void_crypt', dais: 'sculk_shrieker', boss: 'warden', tag: 'beyond_void_warden', name: 'Void Warden',
      relic: /Void Heart/, relicName: 'Void Heart', relicItem: 'nether_star', hp: 600 },
    { hall: 'storm_spire', dais: 'lightning_rod', boss: 'breeze', tag: 'beyond_gale_sovereign', name: 'Gale Sovereign',
      relic: /Tempest Horn/, relicName: 'Tempest Horn', relicItem: 'goat_horn', hp: 450 },
  ];
  let bx = 900;
  for (const b of bosses) {
    bx += 120;
    await pad(bx, 300, 20);
    cmd('effect give Explorer minecraft:resistance 60 4 true');
    cmd('effect give Explorer minecraft:instant_health 1 4 true');
    bot.chats.length = 0;
    bot.chat('/beyond build ' + b.hall);
    await sleep(5000);
    const builtLine = last(bot, /Built/);
    const m = builtLine.match(/dais is at (-?\d+) (-?\d+) (-?\d+)/);
    check(!!m, `${b.hall} built, and the reply says where its dais is`, builtLine.slice(0, 120));
    if (!m) continue;
    const dais = { x: +m[1], y: +m[2], z: +m[3] };
    cmd(`execute in minecraft:the_end run tp Explorer ${dais.x + 2.5} ${dais.y} ${dais.z + 0.5}`);
    await sleep(3000);
    cmd(`execute in minecraft:the_end if block ${dais.x} ${dais.y} ${dais.z} minecraft:${b.dais} run say DAIS_OK ${b.hall}`);
    await sleep(1200);
    check(said(bot, new RegExp('DAIS_OK ' + b.hall)), `the ${b.hall} dais carries a ${b.dais} (server-side)`);
    // The hall holds: a survival dig at the dais's neighbour is refused.
    await sleep(600);
    const wallPos = { x: dais.x + 1, y: dais.y - 1, z: dais.z };
    const wallName = (bot.blockAt(new Vec3(wallPos.x, wallPos.y, wallPos.z)) || {}).name;
    const digOffset = fs.readFileSync(RUN + '/test.log', 'utf8').length;
    try { await Promise.race([bot.dig(bot.blockAt(new Vec3(wallPos.x, wallPos.y, wallPos.z))), sleep(6000)]); }
    catch (e) { console.log('   dig refused client-side: ' + e.message); }
    await sleep(1000);
    const digReached = /tried to break a boss hall/.test(fs.readFileSync(RUN + '/test.log', 'utf8').slice(digOffset));
    cmd(`execute in minecraft:the_end if block ${wallPos.x} ${wallPos.y} ${wallPos.z} minecraft:${wallName || 'air'} run say HALL_HOLDS ${b.hall}`);
    await sleep(1200);
    check(!!wallName && said(bot, new RegExp('HALL_HOLDS ' + b.hall)), `the ${b.hall} cannot be mined in survival`, wallName || '?');
    // The message only comes when the dig reached the server; mineflayer sometimes refuses
    // a dig client-side (out of reach after a fall, mid-teleport) and sends nothing.
    if (!digReached) console.log('   (no dig packet reached the server, so no "hall holds" message to check)');
    else check(said(bot, /The hall holds/), 'and the player is told so', last(bot, /hall holds/));
    // Wake it.
    cmd(`execute in minecraft:the_end run kill @e[type=minecraft:${b.boss}]`);
    await sleep(500);
    bot.chats.length = 0;
    const daisBlock = bot.blockAt(new Vec3(dais.x, dais.y, dais.z));
    if (daisBlock) {
      try { await bot.lookAt(daisBlock.position.offset(0.5, 0.5, 0.5), true); } catch (e) {}
      try { await bot.activateBlock(daisBlock); } catch (e) { console.log('   activate: ' + e.message); }
    }
    await sleep(3000);
    cmd(`execute in minecraft:the_end if entity @e[type=minecraft:${b.boss},tag=${b.tag}] run say BOSS_OK ${b.tag}`);
    await sleep(1200);
    check(said(bot, new RegExp('BOSS_OK ' + b.tag)), `using the ${b.dais} woke the ${b.name}, tagged`, last(bot, /stirs|rises/).slice(0, 80));
    check(said(bot, new RegExp(b.name)), `everyone was told the ${b.name} woke`);
    cmd(`execute in minecraft:the_end run data get entity @e[type=minecraft:${b.boss},tag=${b.tag},limit=1] Health`);
    await sleep(1000);
    const hpLine = fs.readFileSync(RUN + '/test.log', 'utf8').split('\n').filter((l) => /has the following entity data: \d/.test(l)).slice(-1)[0] || '';
    check(new RegExp(`data: ${b.hp}(\\.0)?f`).test(hpLine), `the ${b.name} has ${b.hp} health`, hpLine.slice(-40));
    // Kill it: the relic drops, named.
    cmd('clear Explorer');
    cmd(`execute in minecraft:the_end run kill @e[type=minecraft:${b.boss},tag=${b.tag}]`);
    await sleep(2500);
    cmd(`execute in minecraft:the_end run tp @e[type=minecraft:item] ${dais.x + 2.5} ${dais.y + 1} ${dais.z + 0.5}`);
    await sleep(2500);
    const relic = itemsNamed(bot, b.relic)[0];
    check(!!relic && relic.name === b.relicItem, `the ${b.name} dropped the ${b.relicName} (a ${b.relicItem})`,
        relic ? relic.name : bot.inventory.items().map((i) => i.name).join(','));
    check(said(bot, /is still|falls silent/), `everyone was told the ${b.name} fell`, last(bot, /still|silent/).slice(0, 80));
    // The relic fires.
    if (relic) {
      await bot.equip(relic, 'hand');
      bot.chats.length = 0;
      bot.activateItem();
      await sleep(2000);
      check(said(bot, b.relic), `the ${b.relicName} reports on the action bar`, last(bot, b.relic));
    }
    cmd(`execute in minecraft:the_end run kill @e[type=minecraft:${b.boss}]`);
    cmd('execute in minecraft:the_end run kill @e[type=minecraft:item]');
    cmd('execute in minecraft:the_end run kill @e[type=minecraft:endermite]');
    cmd('execute in minecraft:the_end run kill @e[type=minecraft:phantom]');
  }

  // ------------------------------------------------ 8c. /beyond seed on the land already made
  // Everything above generated around the bot as it went. Seeding the same area again must
  // build nothing new in regions already handled, and must report what it did.
  console.log('\n== 8c. /beyond seed is idempotent over land already handled ==');
  bot.chats.length = 0;
  bot.chat('/beyond seed 300');
  let seeded = null;
  for (let i = 0; i < 60 && !seeded; i++) { await sleep(1000); seeded = last(bot, /Seeded \d+ thing/); }
  console.log('   ' + seeded);
  check(!!seeded, '/beyond seed replies within 60 s', seeded || last(bot, /Seeding/));
  cmd('list');
  await sleep(1000);
  check(/There are \d+ of a max/.test(fs.readFileSync(RUN + '/test.log', 'utf8').split('\n').slice(-40).join('\n')),
      'the server is still answering commands after seeding');

  // --------------------------------------------------------------- 9. loot override
  console.log('\n== 9. an ore only drops its End material inside the End ==');
  cmd('clear Explorer');
  cmd('execute in minecraft:the_end as Explorer at @s run setblock ~ ~-1 ~ minecraft:lapis_ore');
  await sleep(1000);
  cmd('execute in minecraft:the_end as Explorer at @s run loot give Explorer mine ~ ~-1 ~');
  await sleep(2500);
  const dustDrop = itemsNamed(bot, /Thallasium Dust/);
  const lapis = bot.inventory.items().filter((i) => i.name === 'lapis_lazuli');
  check(dustDrop.length > 0 && lapis.length === 0, 'lapis ore mined in the End drops Thallasium Dust, not lapis',
      `${dustDrop.length} dust stack(s), ${lapis.length} lapis`);

  // ------------------------------------------- 10. no resource pack with an empty pack_url
  console.log('\n== 10. no resource pack is pushed while pack_url is empty ==');
  check(bot.packPushes.length === 0, 'no add_resource_pack packet arrived during the whole run',
      bot.packPushes.length ? JSON.stringify(bot.packPushes[0]).slice(0, 160) : '');
  check(bot.kicks.length === 0, 'the bot was never kicked', bot.kicks.join(' | ').slice(0, 160));
  console.log(`   ${bot.waypoints.length} waypoint packet(s) over the run; operations: `
      + [...new Set(bot.waypoints.map((p) => p.operation))].join(','));

  console.log(`\n=========== ${failures === 0 ? 'ALL CHECKS PASSED' : failures + ' CHECK(S) FAILED'} ===========`);
  bot.quit();
  await sleep(800);
  process.exit(failures === 0 ? 0 : 1);
}

main().catch((e) => { console.log('!! harness error: ' + ((e && e.stack) || e)); process.exit(2); });
