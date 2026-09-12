const mcData = require('/home/tim/claude/anticheat-fabric/test/node_modules/minecraft-data')('1.21.11')
const t = mcData.protocol.play.toClient.types.packet_entity_velocity
console.log(JSON.stringify(t).slice(0, 400))
