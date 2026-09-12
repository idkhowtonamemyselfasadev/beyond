package dev.beyond.world;

import com.mojang.datafixers.util.Pair;
import dev.beyond.Beyond;
import dev.beyond.BeyondConfig;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.HolderSet;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.game.ClientboundTrackedWaypointPacket;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.waypoints.Waypoint;
import net.minecraft.world.waypoints.WaypointStyleAssets;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Points every player in the End at the Hollow King's throne.
 *
 * <p>A vanilla client already has a locator bar that shows where the other players are.
 * The server can put anything on it, so the nearest Throne City is sent as a purple mark:
 * turn until it is centred and walk. Nothing to install. The search is the same one
 * {@code /locate} uses, run once and then only again when the player has moved far.
 */
public final class BossLocator {

    private static final UUID MARK = UUID.nameUUIDFromBytes("beyond:throne".getBytes());
    public static final ResourceKey<Structure> THRONE_CITY =
            ResourceKey.create(Registries.STRUCTURE, Identifier.parse(Beyond.MODID + ":throne_city"));

    private record Known(BlockPos throne, BlockPos foundFrom, boolean told) {
    }

    private final Map<UUID, Known> known = new HashMap<>();

    public void onTick(MinecraftServer server, BeyondConfig config, long tick) {
        if (tick % 40 != 0) {
            return;
        }
        ServerLevel end = server.getLevel(Level.END);
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            UUID id = player.getUUID();
            if (!config.boss_marker || end == null || player.level() != end) {
                if (known.remove(id) != null) {
                    player.connection.send(ClientboundTrackedWaypointPacket.removeWaypoint(MARK));
                }
                continue;
            }
            Known current = known.get(id);
            BlockPos here = player.blockPosition();
            // The search costs what /locate costs, so it is not repeated while the known
            // throne is still reasonably near: only after 800 blocks of travel, and only if
            // the throne itself is now more than 1,200 blocks away.
            if (current != null && (current.foundFrom().distSqr(here) < 800 * 800
                    || current.throne().distSqr(here) < 1200 * 1200)) {
                continue;
            }
            BlockPos throne = find(end, here);
            if (throne == null) {
                continue;
            }
            Waypoint.Icon icon = new Waypoint.Icon();
            icon.style = WaypointStyleAssets.BOWTIE;
            icon.color = Optional.of(0xB050FF);
            player.connection.send(current == null
                    ? ClientboundTrackedWaypointPacket.addWaypointPosition(MARK, icon, throne)
                    : ClientboundTrackedWaypointPacket.updateWaypointPosition(MARK, icon, throne));
            boolean told = current != null && current.told();
            if (!told) {
                player.sendSystemMessage(Component.literal("The Hollow King's throne lies ")
                        .withStyle(ChatFormatting.LIGHT_PURPLE)
                        .append(Component.literal(describe(here, throne)).withStyle(ChatFormatting.WHITE))
                        .append(Component.literal(". The purple mark on your locator bar points the way.")
                                .withStyle(ChatFormatting.LIGHT_PURPLE)));
                told = true;
            }
            known.put(id, new Known(throne, here, told));
        }
    }

    /** The nearest Throne City to a point, or null if none is within the search radius. */
    public static BlockPos find(ServerLevel end, BlockPos from) {
        Optional<Holder.Reference<Structure>> holder =
                end.registryAccess().lookupOrThrow(Registries.STRUCTURE).get(THRONE_CITY);
        if (holder.isEmpty()) {
            return null;
        }
        Pair<BlockPos, Holder<Structure>> found = end.getChunkSource().getGenerator()
                .findNearestMapStructure(end, HolderSet.direct(holder.get()), from, 100, false);
        return found == null ? null : found.getFirst();
    }

    /** "1,240 blocks to the north-east". */
    public static String describe(BlockPos from, BlockPos to) {
        int dx = to.getX() - from.getX();
        int dz = to.getZ() - from.getZ();
        int distance = (int) Math.sqrt((double) dx * dx + (double) dz * dz);
        String[] names = {"south", "south-west", "west", "north-west", "north", "north-east", "east", "south-east"};
        double angle = Math.toDegrees(Math.atan2(-dx, dz));   // 0 = south (+z), 90 = west (-x)
        int index = (int) Math.floor(((angle + 360 + 22.5) % 360) / 45);
        return String.format("%,d blocks to the %s", distance, names[index]);
    }

    public void forget(UUID player) {
        known.remove(player);
    }
}
