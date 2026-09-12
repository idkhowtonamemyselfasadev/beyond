// Short re-check on an existing world: section 1b of test-bots.js (the throne locator and
// /throne), then /beyond tp verdigris_dust_wastelands from three far-apart origins.
const mineflayer = require('/home/tim/claude/anticheat/test/node_modules/mineflayer');
const fs = require('fs');
const PORT = parseInt(process.env.PORT || '25609', 10);
const fifo = fs.createWriteStream(__dirname + '/console.fifo', { flags: 'a' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let failures = 0;
const cmd = (c) => fifo.write(c + '\n');
const check = (c, n, e = '') => { if (!c) failures++; console.log(`${c ? '   PASS' : '!! FAIL'}  ${n}${e ? '  ' + e : ''}`); };
const said = (bot, re) => bot.chats.some((m) => re.test(m));
const last = (bot, re) => bot.chats.filter((m) => re.test(m)).slice(-1)[0] || '';
function connect(username) {
  return new Promise((resolve, reject) => {
    const bot = mineflayer.createBot({ host: '127.0.0.1', port: PORT, username, version: '1.21.11', auth: 'offline' });
    bot.chats = []; bot.log = []; bot.waypoints = []; bot.packPushes = []; bot.kicks = [];
    bot.on('message', (m) => { const t = m.toString(); bot.chats.push(t); bot.log.push(t); });
    bot._client.on('tracked_waypoint', (p) => bot.waypoints.push(p));
    bot._client.on('add_resource_pack', (p) => bot.packPushes.push(p));
    bot.once('spawn', () => resolve(bot));
    bot.on('error', reject);
    bot.on('kicked', (r) => { bot.kicks.push(JSON.stringify(r)); reject(new Error('kicked: ' + JSON.stringify(r))); });
  });
}
async function main() {
  const bot = await connect('Explorer');
  await sleep(1500);
  cmd('op Explorer'); cmd('gamerule keep_inventory true');
  await sleep(1500);
  console.log('== 1b (rerun) ==');
  cmd('execute in minecraft:the_end run tp Explorer 100 80 0');
  await sleep(6000);
  cmd('effect give Explorer minecraft:resistance 120 4 true');
  await sleep(10000);
  const wp = bot.waypoints[0];
  check(!!wp, 'a tracked_waypoint packet arrived', wp ? `op=${wp.operation} type=${wp.waypoint.type} data=${JSON.stringify(wp.waypoint.data)}` : '');
  check(bot.log.some((m) => /Hollow King's throne lies/.test(m)), 'chat told where the throne lies', bot.log.filter((m) => /throne lies/.test(m))[0] || '');
  bot.chats.length = 0;
  cmd('execute as Explorer at @s if dimension minecraft:the_end run say STILL_IN_END');
  await sleep(1500);
  if (!said(bot, /STILL_IN_END/)) { console.log('   (bot left the End, sending it back)'); cmd('execute in minecraft:the_end run tp Explorer 100 80 0'); await sleep(4000); }
  bot.chats.length = 0;
  bot.chat('/throne');
  await sleep(3000);
  check(said(bot, /The Hollow King's throne:/), '/throne answers with the throne position', last(bot, /Hollow King|Throne City|waits in the End/).slice(0, 120));
  console.log('== verdigris_dust_wastelands from three origins ==');
  for (const [x, z] of [[-3708, -3272], [-1096, -9400], [-895, 17545]]) {
    cmd(`execute in minecraft:the_end run tp Explorer ${x} 80 ${z}`);
    await sleep(4000);
    bot.chats.length = 0;
    bot.chat('/beyond tp verdigris_dust_wastelands');
    let line = '';
    for (let i = 0; i < 40 && !line; i++) { await sleep(1000); line = last(bot, /Teleported to beyond:|No .* within/); }
    console.log(`   from ${x},${z}: ${line.slice(0, 90)}`);
    if (/Teleported/.test(line)) break;
  }
  console.log(`   ${bot.waypoints.length} waypoint packets; packPushes=${bot.packPushes.length} kicks=${bot.kicks.length}`);
  console.log(`=========== ${failures === 0 ? 'ALL CHECKS PASSED' : failures + ' CHECK(S) FAILED'} ===========`);
  bot.quit(); await sleep(800); process.exit(failures === 0 ? 0 : 1);
}
main().catch((e) => { console.log('!! harness error: ' + ((e && e.stack) || e)); process.exit(2); });
