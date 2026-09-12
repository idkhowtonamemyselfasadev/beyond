package dev.beyond;

import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/** Per-player, per-ability cooldowns on the server tick clock, mirrored onto the hotbar sweep. */
public final class Cooldowns {

    private final Map<UUID, Map<String, Long>> readyAt = new HashMap<>();
    private long tick;

    public void onTick() {
        tick++;
    }

    public long tick() {
        return tick;
    }

    public int remaining(ServerPlayer player, String key) {
        Map<String, Long> byKey = readyAt.get(player.getUUID());
        if (byKey == null) {
            return 0;
        }
        Long ready = byKey.get(key);
        if (ready == null) {
            return 0;
        }
        long left = ready - tick;
        return left <= 0 ? 0 : (int) left;
    }

    public boolean ready(ServerPlayer player, String key) {
        return remaining(player, key) <= 0;
    }

    /** Sets the cooldown, and shows it on the item so the client draws the sweep. */
    public void set(ServerPlayer player, String key, int ticks, ItemStack stack) {
        readyAt.computeIfAbsent(player.getUUID(), id -> new HashMap<>()).put(key, tick + ticks);
        if (stack != null) {
            player.getCooldowns().addCooldown(stack, ticks);
        }
    }

    public void forget(UUID player) {
        readyAt.remove(player);
    }
}
