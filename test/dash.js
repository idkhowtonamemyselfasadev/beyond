// The dash, checked from the server's side: is the player really gliding, and does the
// sneak actually change their motion? A bot's own physics cannot be trusted for this.
const mineflayer = require('/home/tim/claude/anticheat-fabric/test/node_modules/mineflayer')
const { execFileSync } = require('child_process')
const rcon = (c) => execFileSync('python3', ['/home/tim/claude/beyond/run/rcon.py', c],
  { encoding: 'utf8' }).trim()
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

const motion = () => {
  const m = rcon('data get entity Flyer Motion')
  const nums = (m.match(/-?\d+\.\d+/g) || []).map(Number)
  return nums.length >= 3 ? Math.hypot(nums[0], nums[2]) : -1
}

async function main() {
  const bot = mineflayer.createBot({ host: '127.0.0.1', port: 25650, username: 'Flyer',
    version: '1.21.11', auth: 'offline' })
  const seen = []
  bot.on('message', (m) => { const t = m.toString().trim(); if (t) { seen.push(t); console.log('  < ' + t) } })
  await new Promise((r) => bot.once('spawn', r))
  await wait(1500)
  rcon('op Flyer')
  rcon('gamerule fallDamage false')
  rcon('item replace entity Flyer armor.chest with minecraft:elytra[minecraft:custom_data={beyond_dash_elytra:true}]')
  rcon('execute in minecraft:the_end run tp Flyer 100 220 100')
  await wait(2000)

  // fall a moment, then start gliding
  bot._client.write('entity_action', { entityId: bot.entity.id, actionId: 8, jumpBoost: 0 })
  await wait(1200)
  // the server's own view: bit 7 of the shared entity flags is "fall flying"
  const flags = bot.entity.metadata && bot.entity.metadata[0]
  const gliding = typeof flags === 'number' && (flags & 0x80) !== 0
  console.log('  entity flags = ' + flags + '  -> gliding: ' + gliding)
  console.log(gliding ? '  PASS  the server sees the player gliding'
                      : '  FAIL  never started gliding - cannot test the dash')
  if (!gliding) { bot.quit(); process.exit(1) }

  const before = motion()
  bot.setControlState('sneak', true)
  await wait(900)
  const after = motion()
  bot.setControlState('sneak', false)
  console.log(`  horizontal motion ${before.toFixed(2)} -> ${after.toFixed(2)}`)
  const dashed = seen.some((t) => t === 'Dash')
  console.log(dashed ? '  PASS  the dash fired' : '  FAIL  no dash')

  // and again straight away, to prove the cooldown holds
  seen.length = 0
  bot.setControlState('sneak', true)
  await wait(900)
  bot.setControlState('sneak', false)
  const held = seen.some((t) => t.startsWith('Wings recovering'))
  console.log(held ? '  PASS  the cooldown holds the second dash'
                   : '  FAIL  cooldown did not report')
  bot.quit()
  process.exit(dashed && held ? 0 : 1)
}
main().catch((e) => { console.log('ERROR', e.message); process.exit(1) })
