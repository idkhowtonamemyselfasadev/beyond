// The dash, its cooldown, and what Fast Fly does to it - driven through /beyond dash so
// the test does not depend on getting a headless client to glide.
const mineflayer = require('/home/tim/claude/anticheat-fabric/test/node_modules/mineflayer')
const { execFileSync } = require('child_process')
const rcon = (c) => execFileSync('python3', ['/home/tim/claude/beyond/run/rcon.py', c],
  { encoding: 'utf8' }).trim()
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
let pass = 0, fail = 0
const check = (n, ok, d) => { ok ? pass++ : fail++; console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${n}${d ? '  ' + d : ''}`) }
// A player's motion is client-authoritative, so it is not in server NBT. What the
// server does is send a velocity packet; catching that is the real proof of the shove.
let lastPush = null
function watchVelocity(bot) {
  bot._client.on('entity_velocity', (p) => {
    if (p.entityId === bot.entity.id) {
      const v = p.velocity || p
      // Keep the biggest one: a grounded player gets zeroed velocity updates a moment
      // later, which would otherwise overwrite the shove we are looking for.
      // lpVec3 arrives already decoded into blocks per tick - no /8000 needed.
      const push = Math.hypot(v.x, v.z)
      if (lastPush === null || push > lastPush) lastPush = push
    }
  })
}

async function main() {
  const bot = mineflayer.createBot({ host: '127.0.0.1', port: 25650, username: 'Flyer',
    version: '1.21.11', auth: 'offline' })
  await new Promise((r) => bot.once('spawn', r))
  watchVelocity(bot)
  await wait(1500)
  rcon('op Flyer')

  console.log('--- without the wings')
  rcon('item replace entity Flyer armor.chest with minecraft:air')
  await wait(600)
  const bare = rcon('beyond dash Flyer')
  console.log('  ' + bare)
  check('refuses without the wings', bare.includes('not wearing'))

  console.log('\n--- with them')
  console.log('  ' + rcon('item replace entity Flyer armor.chest with minecraft:elytra[minecraft:custom_data={beyond_dash_elytra:true}]'))
  await wait(1200)
  console.log('  chest holds: ' + rcon('data get entity Flyer equipment.chest').slice(0, 150))
  await bot.look(0, 0, true)          // look flat, so the dash is horizontal
  await wait(300)
  lastPush = null
  const first = rcon('beyond dash Flyer')
  console.log('  ' + first)
  await wait(600)
  check('dashes', first.includes('dashed'))
  check('30s cooldown by default', first.includes('(30s cooldown)'), first)
  check('the server pushes the player', lastPush !== null && lastPush > 0.5,
        lastPush === null ? 'no velocity packet' : lastPush.toFixed(2) + ' blocks/tick')

  console.log('\n--- the cooldown holds')
  const second = rcon('beyond dash Flyer')
  console.log('  ' + second)
  check('second dash refused', second.includes('recovering'))

  console.log('\n--- Fast Fly shortens it')
  rcon('item replace entity Flyer armor.chest with minecraft:elytra[minecraft:custom_data={beyond_dash_elytra:true},minecraft:enchantments={"beyond:fast_fly":1}]')
  await wait(700)
  const fast = rcon('beyond dash Flyer')
  console.log('  ' + fast)
  // The 30s cooldown from the dash above is still running, so what this shows is the
  // remaining time recalculated against the shorter one: under 20s means Fast Fly
  // took effect, since a 30s cooldown one second in would still read 29.
  const left = Number((fast.match(/another (\d+)s/) || [])[1])
  check('Fast Fly cuts the cooldown to 20s',
        fast.includes('(20s cooldown)') || (left > 0 && left <= 20),
        fast.trim())

  console.log(`\n${pass} passed, ${fail} failed`)
  bot.quit(); process.exit(fail ? 1 : 0)
}
main().catch((e) => { console.log('ERROR', e.message); process.exit(1) })
