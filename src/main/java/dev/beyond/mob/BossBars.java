package dev.beyond.mob;

import dev.beyond.BeyondConfig;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerBossEvent;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.BossEvent;
import net.minecraft.world.entity.LivingEntity;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * Boss bars for the bosses that are not withers.
 *
 * <p>The Hollow King is a wither, so the client draws his bar for free. A warden and a
 * breeze have no bar of their own, but the server can put one on any client's screen: one
 * {@link ServerBossEvent} per living boss, shown to whoever is within sixty-four blocks,
 * tracking its health, and taken down when it dies or vanishes.
 */
public final class BossBars {

    private static final Map<UUID, ServerBossEvent> BARS = new HashMap<>();

    private BossBars() {
    }

    /** Keeps this boss's bar up to date and on the screens of everyone near it. */
    public static void track(ServerLevel level, LivingEntity boss, Component name,
                             BossEvent.BossBarColor color) {
        ServerBossEvent bar = BARS.computeIfAbsent(boss.getUUID(), id -> {
            ServerBossEvent made = new ServerBossEvent(name, color, BossEvent.BossBarOverlay.NOTCHED_6);
            made.setDarkenScreen(false);
            return made;
        });
        bar.setProgress(Mth.clamp(boss.getHealth() / boss.getMaxHealth(), 0f, 1f));
        List<ServerPlayer> near = level.getEntitiesOfClass(ServerPlayer.class,
                boss.getBoundingBox().inflate(64));
        for (ServerPlayer player : level.getServer().getPlayerList().getPlayers()) {
            if (near.contains(player)) {
                bar.addPlayer(player);
            } else {
                bar.removePlayer(player);
            }
        }
    }

    /** A player who left must not stay on a bar's list, or the bar keeps a dead connection. */
    public static void forget(ServerPlayer player) {
        for (ServerBossEvent bar : BARS.values()) {
            bar.removePlayer(player);
        }
    }

    public static void drop(LivingEntity boss) {
        ServerBossEvent bar = BARS.remove(boss.getUUID());
        if (bar != null) {
            bar.removeAllPlayers();
        }
    }

    /**
     * Once a second: every boss that is not a wither gets its turn, and a bar whose boss
     * has gone without dying (unloaded, discarded by a command) comes down.
     */
    public static void onTick(MinecraftServer server, BeyondConfig config, long tick) {
        if (tick % 20 != 0) {
            return;
        }
        Set<UUID> alive = new HashSet<>();
        alive.addAll(VoidWarden.tick(server, config, tick));
        alive.addAll(GaleSovereign.tick(server, config, tick));
        for (var it = BARS.entrySet().iterator(); it.hasNext(); ) {
            var entry = it.next();
            if (!alive.contains(entry.getKey())) {
                entry.getValue().removeAllPlayers();
                it.remove();
            }
        }
    }

    public static void announce(MinecraftServer server, Component message) {
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            player.sendSystemMessage(message);
        }
    }
}
