const mcData = require('/home/tim/claude/anticheat-fabric/test/node_modules/minecraft-data')('1.21.11')
const names = Object.keys(mcData.protocol.play.toServer.types)
console.log(names.filter(n => n.indexOf('action') >= 0 || n.indexOf('command') >= 0).join('  '))
