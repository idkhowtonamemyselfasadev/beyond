package dev.beyond;

import net.minecraft.advancements.AdvancementHolder;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;

/** Grants the mod's code-driven advancements. */
public final class Advancements {

    private Advancements() {
    }

    public static void grant(ServerPlayer player, String name) {
        MinecraftServer server = player.level().getServer();
        if (server == null) {
            return;
        }
        AdvancementHolder holder = server.getAdvancements().get(Identifier.parse(Beyond.MODID + ":" + name));
        if (holder != null) {
            player.getAdvancements().award(holder, "granted");
        }
    }
}
