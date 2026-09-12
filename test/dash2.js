// Getting a bot to actually glide is the whole difficulty here, so this one watches it
// fall before it tries, and says what it saw either way.
const mineflayer = require('/home/tim/claude/anticheat-fabric/test/node_modules/mineflayer')
const { execFileSync } = require('child_process')
const rcon = (c) => execFileSync('python3', ['/home/tim/claude/beyond/run/rcon.py', c],
  { encoding: 'utf8' }).trim()
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

async function main() {
  const bot = mineflayer.createBot({ host: '127.0.0.1', port: 25650, username: 'Flyer',
    version: '1.21.11', auth: 'offline' })
  const seen = []
  bot.on('message', (m) => { const t = m.toString().trim(); if (t) seen.push(t) })
  await new Promise((r) => bot.once('spawn', r))
  await wait(1500)
  rcon('op Flyer')
  rcon('gamerule fallDamage false')
  rcon('item replace entity Flyer armor.chest with minecraft:elytra[minecraft:custom_data={beyond_dash_elytra:true}]')
  rcon('execute in minecraft:the_end run tp Flyer 100 300 100')
  await wait(900)
  // start gliding while still high up, before the ground gets in the way
  bot._client.write('entity_action', { entityId: bot.entity.id, actionId: 8, jumpBoost: 0 })
  await wait(400)

  // gliding is observable without metadata: a falling player loses ~30 blocks a second,
  // a gliding one loses a fraction of that.
  const a = bot.entity.position.y
  await wait(1000)
  const b = bot.entity.position.y
  const rate = a - b
  console.log(`  descending ${rate.toFixed(1)} blocks/s at y=${b.toFixed(0)}`)
  const gliding = rate < 18
  console.log('  gliding: ' + gliding)

  seen.length = 0
  bot.setControlState('sneak', true)
  await wait(1000)
  bot.setControlState('sneak', false)
  await wait(300)
  const dashed = seen.some((t) => t === 'Dash')
  console.log('  messages after sneak: ' + (seen.join(' | ') || '(none)'))
  console.log(dashed ? '  PASS  the dash fired while gliding'
                     : '  (no dash - see whether the bot was gliding above)')

  if (dashed) {
    seen.length = 0
    bot.setControlState('sneak', true); await wait(900); bot.setControlState('sneak', false)
    console.log(seen.some((t) => t.startsWith('Wings recovering'))
      ? '  PASS  the cooldown holds the second one' : '  FAIL  cooldown silent')
  }
  bot.quit(); process.exit(dashed ? 0 : 2)
}
main().catch((e) => { console.log('ERROR', e.message); process.exit(1) })
