package dev.beyond;

import net.minecraft.core.BlockPos;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.levelgen.structure.Structure;

import java.util.List;

/**
 * The boss halls are not breakable - the Throne City, the Void Crypt and the Storm Spire.
 *
 * <p>A boss is woken on a block inside its hall, so the hall is the arena, and an arena
 * with a hole dug through its floor - or a wall blown out by the boss's own explosions -
 * is a fight that can be skipped. Every block of a hall's structure pieces is protected
 * from players (creative mode excepted, so an operator can still edit one), from
 * explosions of every kind, and from mobs that break blocks. Blocks are looked up by the
 * structure piece they are in, so nothing outside the footprint is touched. Heads and
 * skulls are the one exception: those are loot, and a hall's dragon head can be taken.
 */
public final class Halls {

    private Halls() {
    }

    /** The structures that count as boss halls. */
    public static List<ResourceKey<Structure>> keys() {
        return java.util.List.of(dev.beyond.world.BossLocator.THRONE_CITY);
    }

    /** True if this block belongs to a boss hall and the halls are protected. */
    public static boolean protects(ServerLevel level, BlockPos pos) {
        // Heads and skulls are loot, not walls: a dragon head or a wither skeleton skull set
        // into a hall is there to be taken.
        if (level.getBlockState(pos).getBlock() instanceof net.minecraft.world.level.block.AbstractSkullBlock) {
            return false;
        }
        if (!Beyond.config().protect_boss_halls) {
            return false;
        }
        for (ResourceKey<Structure> key : keys()) {
            if (level.structureManager().getStructureWithPieceAt(pos, holder -> holder.is(key)).isValid()) {
                return true;
            }
        }
        // The Void Crypt and the Storm Spire are built by the mod, not by worldgen, so they
        // have no structure pieces to look up; the site record knows their footprints.
        return Beyond.sites() != null && Beyond.sites().inHall(pos);
    }

    /** The players' side of it: a survival player may not break a hall. */
    public static boolean allowBreak(ServerLevel level, net.minecraft.world.entity.player.Player player, BlockPos pos) {
        if (player.isCreative() || !protects(level, pos)) {
            return true;
        }
        player.displayClientMessage(net.minecraft.network.chat.Component.literal("The hall holds. Nothing here can be broken.")
                .withStyle(net.minecraft.ChatFormatting.GRAY), true);
        Beyond.log("{} tried to break a boss hall at {}", player.getName().getString(), pos);
        return false;
    }
}
