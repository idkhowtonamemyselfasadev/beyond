// The Gale Rod: can you actually craft it in a crafting table, does the server throw you
// up, and does it make you wait twenty seconds for the next one?
//
// The launch is checked as the velocity packet the server sends, not as a change in the
// bot's position: mineflayer's headless physics drops an entity_velocity aimed at its own
// player, so a real client rises and this one does not. The packet is the whole of what
// the server does, so it is the whole of what there is to check.
const mineflayer = require('/home/tim/claude/anticheat-fabric/test/node_modules/mineflayer')
const { Vec3 } = require('vec3')
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
    bot.once('spawn', () => resolve(bot))
    bot.on('error', reject)
    setTimeout(() => reject(new Error('never spawned')), 40000)
  })
}

// Where in the open window is a stack of this item? Slots 0-9 are the result and the grid.
function findSlot(bot, name) {
  return bot.currentWindow.slots.findIndex((s, i) => i > 9 && s && s.name === name)
}

async function main() {
  const bot = await connect('Smith')
  const bar = []
  bot.on('message', (m) => { const t = m.toString().trim(); if (t) bar.push(t) })
  let topSpeed = null
  // 1.21 sends this already decoded - dividing by 8000 here reads every launch as zero.
  bot._client.on('entity_velocity', (p) => {
    if (p.entityId !== bot.entity.id) return
    const y = p.velocity ? p.velocity.y : p.velocityY / 8000
    if (topSpeed === null || y > topSpeed) topSpeed = y
  })
  await wait(1500)
  rcon('op Smith')
  await wait(500)

  console.log('--- the recipe is a real recipe')
  const given = rcon('recipe give Smith beyond:gale_rod')
  console.log('  ' + given)
  check('beyond:gale_rod is registered', !given.toLowerCase().includes('unknown'))

  console.log('\n--- and a crafting table actually makes one')
  const p = bot.entity.position.floored()
  rcon(`fill ${p.x - 3} ${p.y - 1} ${p.z - 3} ${p.x + 3} ${p.y - 1} ${p.z + 3} minecraft:stone`)
  rcon(`fill ${p.x - 3} ${p.y} ${p.z - 3} ${p.x + 3} ${p.y + 2} ${p.z + 3} minecraft:air`)
  rcon(`setblock ${p.x + 2} ${p.y} ${p.z} minecraft:crafting_table`)
  rcon('clear Smith')
  rcon('give Smith minecraft:breeze_rod 2')
  rcon('give Smith minecraft:netherite_ingot 1')
  rcon('give Smith minecraft:stick 1')
  await wait(1500)

  const table = bot.blockAt(new Vec3(p.x + 2, p.y, p.z))
  console.log('  table in front of the bot: ' + (table && table.name))
  await bot.lookAt(table.position.offset(0.5, 0.5, 0.5), true)
  await bot.activateBlock(table)
  await wait(1200)
  console.log('  window open: ' + (bot.currentWindow ? bot.currentWindow.type : 'none'))

  // The pattern is  B_B / _N_ / _S_  over grid slots 1..9; the result is slot 0. Both
  // breeze rods arrive as one stack, so they go in with right-clicks, one rod per corner.
  const rods = findSlot(bot, 'breeze_rod')
  await bot.clickWindow(rods, 0, 0)
  await wait(250)
  await bot.clickWindow(1, 1, 0)
  await wait(250)
  await bot.clickWindow(3, 1, 0)
  await wait(400)
  for (const [item, slot] of [['netherite_ingot', 5], ['stick', 8]]) {
    const from = findSlot(bot, item)
    if (from < 0) { console.log('  missing ' + item); continue }
    await bot.clickWindow(from, 0, 0)
    await wait(200)
    await bot.clickWindow(slot, 0, 0)
    await wait(300)
  }
  await wait(800)
  const grid = bot.currentWindow.slots.slice(1, 10)
    .map((s) => (s ? s.name[0].toUpperCase() : '.')).join('')
  console.log('  grid: ' + grid.slice(0, 3) + ' / ' + grid.slice(3, 6) + ' / ' + grid.slice(6))
  const result = bot.currentWindow.slots[0]
  console.log('  result slot: ' + (result ? `${result.count}x ${result.name}` : 'empty'))
  check('the grid produces something', !!result)
  if (result) {
    await bot.clickWindow(0, 0, 1)   // shift-click the result into the inventory
  }
  await wait(600)
  bot.closeWindow(bot.currentWindow)
  await wait(1000)
  const inv = rcon('data get entity Smith Inventory')
  check('and what it makes is a Gale Rod', inv.includes('gale_rod'),
        inv.includes('gale_rod') ? 'stamped beyond_item gale_rod' : '')
  check('the item sweep names and describes it',
        inv.includes('Gale Rod') && inv.includes('blocks straight up'))
  const promised = inv.match(/leap about (\d+) blocks/)
  console.log('  lore promises: ' + (promised ? promised[0] : '(none)'))

  console.log('\n--- right-click throws you up')
  rcon('clear Smith')
  rcon('give Smith minecraft:breeze_rod[minecraft:custom_data={beyond_item:"gale_rod"}] 1')
  await wait(1200)
  bot.setQuickBarSlot(0)
  await wait(500)
  console.log('  holding: ' + (bot.heldItem && bot.heldItem.name))

  topSpeed = null
  bar.length = 0
  bot.activateItem()
  await wait(1200)
  console.log(`  server pushed the player at ${topSpeed === null ? 'nothing' : topSpeed.toFixed(2) + ' b/t'} upward`)
  check('it launches the player upward', topSpeed !== null && topSpeed > 1.0,
        topSpeed === null ? 'no velocity packet arrived' : topSpeed.toFixed(2) + ' blocks/tick')
  // 1.5 b/t under vanilla gravity is a twelve-block hop; the lore had better say so.
  check('the launch matches what the lore promises',
        promised !== null && Math.abs(parseInt(promised[1], 10) - 12) <= 1,
        promised ? promised[1] + ' blocks' : '')
  check('the action bar says what happened', bar.some((t) => t.includes('Gale Rod')),
        bar.slice(0, 2).join(' | '))

  console.log('\n--- and then makes you wait twenty seconds')
  await wait(1500)
  bar.length = 0
  bot.activateItem()
  await wait(1000)
  const pattern = new RegExp('Gale Rod\\s+(\\d+(?:\\.\\d)?)s')
  const line = bar.find((t) => pattern.test(t))
  console.log('  action bar: ' + (line || bar.join(' | ') || '(nothing)'))
  check('a second use is refused', !!line)
  const left = line ? parseFloat(line.match(pattern)[1]) : 0
  check('with about twenty seconds left', left > 14 && left <= 20, left + 's')

  console.log(`\n${pass} passed, ${fail} failed`)
  bot.quit()
  process.exit(fail ? 1 : 0)
}
main().catch((e) => { console.log('ERROR ' + e.message); process.exit(1) })
