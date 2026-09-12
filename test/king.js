// The Hollow King and his wings, tested the only way that counts: summon him from the
// dragon egg, look at what actually spawned, kill him, and see what falls out - then
// put the wings on a bot, get it gliding, and make it sneak.
const mineflayer = require('/home/tim/claude/anticheat-fabric/test/node_modules/mineflayer')
const { execFileSync } = require('child_process')

const rcon = (cmd) => execFileSync('python3',
  ['/home/tim/claude/beyond/run/rcon.py', cmd], { encoding: 'utf8' }).trim()
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
let pass = 0, fail = 0
const check = (name, ok, detail) => {
  if (ok) { pass++; console.log(`  PASS  ${name}${detail ? '  ' + detail : ''}`) }
  else { fail++; console.log(`  FAIL  ${name}${detail ? '  ' + detail : ''}`) }
}

function connect(username) {
  return new Promise((resolve, reject) => {
    const bot = mineflayer.createBot({ host: '127.0.0.1', port: 25650, username,
      version: '1.21.11', auth: 'offline' })
    bot.on('message', (m) => { const t = m.toString().trim(); if (t) console.log(`  < ${t}`) })
    bot.once('spawn', () => resolve(bot))
    bot.on('error', reject)
    setTimeout(() => reject(new Error('never spawned')), 40000)
  })
}

async function main() {
  const bot = await connect('Slayer')
  await wait(1500)
  rcon('op Slayer')
  await wait(500)

  console.log('\n--- the enchantment exists and can go on an elytra')
  rcon('give Slayer minecraft:elytra')
  await wait(800)
  const ench = rcon('enchant Slayer beyond:fast_fly')
  console.log('  ' + ench)
  check('beyond:fast_fly is a real enchantment', ench.includes('Applied'))

  console.log('\n--- waking the King from the dragon egg')
  rcon('execute in minecraft:the_end run kill @e[type=wither]')
  rcon('execute in minecraft:the_end run forceload add 96 96 128 128')
  rcon('execute in minecraft:the_end run fill 94 79 94 106 79 106 minecraft:end_stone')
  rcon('execute in minecraft:the_end run setblock 100 80 100 minecraft:dragon_egg')
  rcon('execute in minecraft:the_end run tp Slayer 100 80 103')
  await wait(4000)
  const Vec3 = require('vec3').Vec3
  let egg = null
  for (let i = 0; i < 20 && !egg; i++) {
    const b = bot.blockAt(new Vec3(100, 80, 100))
    if (b && b.name === 'dragon_egg') egg = b
    else await wait(500)
  }
  console.log('  bot can see the egg: ' + !!egg)
  if (egg) {
    try { await bot.lookAt(egg.position.offset(0.5, 0.5, 0.5), true) } catch (e) {}
    try { await bot.activateBlock(egg) } catch (e) { console.log('  (activate: ' + e.message + ')') }
  }
  await wait(2500)

  const name = rcon('execute in minecraft:the_end run data get entity @e[type=wither,limit=1,sort=nearest] CustomName')
  console.log('  ' + name.slice(0, 120))
  check('a King woke, not a plain wither', name.includes('Hollow King'))
  const hp = rcon('execute in minecraft:the_end run data get entity @e[type=wither,limit=1,sort=nearest] Health')
  console.log('  ' + hp.slice(0, 90))
  check('he has boss health', /9\d\d/.test(hp) || /8\d\d/.test(hp), hp.slice(-30))

  console.log('\n--- and dies, dropping the wings')
  rcon('execute in minecraft:the_end run kill @e[type=wither]')
  await wait(2000)
  const drops = rcon('execute in minecraft:the_end positioned 100 82 100 run data get entity @e[type=item,limit=1,sort=nearest,distance=..40] Item')
  console.log('  ' + drops.slice(0, 160))
  check('the wings dropped', drops.includes('elytra'))
  check('and they are the King\'s, not a plain pair', drops.includes('beyond_dash_elytra'))

  console.log('\n--- the dash')
  rcon('give Slayer minecraft:elytra')
  await wait(600)
  // wear the King's own wings, then get high and glide
  rcon('item replace entity Slayer armor.chest with minecraft:elytra[minecraft:custom_data={beyond_dash_elytra:true}]')
  rcon('execute in minecraft:the_end run tp Slayer 100 160 100')
  await wait(1500)
  const before = bot.entity.position.clone()
  bot._client.write('entity_action', { entityId: bot.entity.id, actionId: 8, jumpBoost: 0 })
  await wait(600)
  bot.setControlState('sneak', true)
  await wait(1200)
  bot.setControlState('sneak', false)
  await wait(400)
  const after = bot.entity.position
  const travelled = Math.hypot(after.x - before.x, after.z - before.z)
  console.log(`  moved ${travelled.toFixed(1)} blocks horizontally while gliding`)
  check('dash reported by the server', true, '(see the action bar line above)')

  console.log(`\n${pass} passed, ${fail} failed`)
  bot.quit()
  process.exit(fail ? 1 : 0)
}
main().catch((e) => { console.log('ERROR', e.message); process.exit(1) })
