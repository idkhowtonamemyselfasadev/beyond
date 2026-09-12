package dev.beyond.pack;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.protocol.common.ClientboundResourcePackPushPacket;
import net.minecraft.network.protocol.common.ServerboundResourcePackPacket;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.storage.LevelResource;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

/**
 * Offers the 3D model resource pack in chat when a player joins.
 *
 * <p>Vanilla's own {@code resource-pack} server property either forces the pack on
 * everyone or nags on every join. This asks once, in chat, with a clickable answer: the
 * pack is sent only to players who click Install, and a player who clicks Never is not
 * asked again on this world. Both answers are ordinary commands, so a player can also just
 * type them.
 */
public final class PackOffer {

    /** Fixed id, so re-sending the pack replaces the previous copy instead of stacking. */
    private static final UUID PACK_ID = UUID.fromString("8a2d4c6e-1f3b-4a5c-9d7e-2b4c6d8e0f11");
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

    private final Set<UUID> declined = new HashSet<>();
    private Path file;

    public void load(MinecraftServer server) {
        file = server.getWorldPath(LevelResource.ROOT).resolve("beyond-pack-declined.json");
        declined.clear();
        if (!Files.exists(file)) {
            return;
        }
        try {
            Set<String> ids = GSON.fromJson(Files.readString(file, StandardCharsets.UTF_8),
                    new TypeToken<Set<String>>() { }.getType());
            if (ids != null) {
                ids.forEach(id -> declined.add(UUID.fromString(id)));
            }
        } catch (Exception e) {
            dev.beyond.Beyond.LOGGER.error("Could not read {}: {}", file, e.toString());
        }
    }

    public void save() {
        if (file == null) {
            return;
        }
        try {
            Set<String> ids = new HashSet<>();
            declined.forEach(id -> ids.add(id.toString()));
            Files.writeString(file, GSON.toJson(ids), StandardCharsets.UTF_8);
        } catch (IOException e) {
            dev.beyond.Beyond.LOGGER.error("Could not write {}: {}", file, e.toString());
        }
    }

    public boolean configured(dev.beyond.BeyondConfig config) {
        return config.pack_offer_on_join && config.pack_url != null && !config.pack_url.isBlank();
    }

    /** On join: the required dialog, or the chat question, depending on the config. */
    public void onJoin(ServerPlayer player, dev.beyond.BeyondConfig config) {
        if (config.pack_required && config.pack_url != null && !config.pack_url.isBlank()) {
            push(player, config, true);
            return;
        }
        if (!configured(config) || declined.contains(player.getUUID())) {
            return;
        }
        player.sendSystemMessage(Component.literal(""));
        player.sendSystemMessage(Component.literal(config.pack_offer_message)
                .withStyle(ChatFormatting.GOLD));
        Component install = button("[Install]", ChatFormatting.GREEN, "/endmusic install",
                "Download the End music now (about 25 MB)");
        Component later = button("[Not now]", ChatFormatting.GRAY, "/endmusic later",
                "Ask again next time you join");
        Component never = button("[Never]", ChatFormatting.RED, "/endmusic never",
                "Do not ask again. /endmusic install still works.");
        player.sendSystemMessage(Component.literal("   ")
                .append(install).append(Component.literal("   "))
                .append(later).append(Component.literal("   "))
                .append(never));
    }

    private static Component button(String label, ChatFormatting colour, String command, String hover) {
        return Component.literal(label).withStyle(style -> style
                .withColor(colour).withBold(true)
                .withClickEvent(new ClickEvent.RunCommand(command))
                .withHoverEvent(new HoverEvent.ShowText(Component.literal(hover))));
    }

    /** Sends the pack. Not required: declining the client-side dialog just leaves it off. */
    public void install(ServerPlayer player, dev.beyond.BeyondConfig config) {
        if (config.pack_url == null || config.pack_url.isBlank()) {
            player.sendSystemMessage(Component.literal("No resource pack is configured on this server.")
                    .withStyle(ChatFormatting.RED));
            return;
        }
        declined.remove(player.getUUID());
        push(player, config, config.pack_required);
        player.sendSystemMessage(Component.literal(
                        "Sending the End music. If nothing happens, set this server's "
                                + "resource pack setting to Prompt or Enabled in the multiplayer menu.")
                .withStyle(ChatFormatting.GRAY));
        if (config.log_events) {
            dev.beyond.Beyond.LOGGER.info("PACK sent to {}", player.getName().getString());
        }
    }

    private static void push(ServerPlayer player, dev.beyond.BeyondConfig config, boolean required) {
        player.connection.send(new ClientboundResourcePackPushPacket(PACK_ID, config.pack_url,
                config.pack_sha1 == null ? "" : config.pack_sha1, required,
                Optional.of(Component.literal(config.pack_offer_message))));
    }

    /** Whether this response is about our pack and, under pack_required, a reason to leave. */
    public static boolean isRefusal(UUID id, ServerboundResourcePackPacket.Action action, dev.beyond.BeyondConfig config) {
        if (!config.pack_required || !PACK_ID.equals(id)) {
            return false;
        }
        return action == ServerboundResourcePackPacket.Action.DECLINED
                || action == ServerboundResourcePackPacket.Action.FAILED_DOWNLOAD
                || action == ServerboundResourcePackPacket.Action.INVALID_URL
                || action == ServerboundResourcePackPacket.Action.FAILED_RELOAD;
    }

    public void never(ServerPlayer player) {
        declined.add(player.getUUID());
        save();
        player.sendSystemMessage(Component.literal(
                        "Alright, no more asking. /endmusic install brings the models back any time.")
                .withStyle(ChatFormatting.GRAY));
    }

    public void later(ServerPlayer player) {
        player.sendSystemMessage(Component.literal("Alright, next time then.")
                .withStyle(ChatFormatting.GRAY));
    }
}
