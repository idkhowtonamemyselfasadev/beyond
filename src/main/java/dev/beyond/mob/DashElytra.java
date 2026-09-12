package dev.beyond.mob;

import dev.beyond.Beyond;
import dev.beyond.BeyondConfig;
import net.minecraft.ChatFormatting;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.game.ClientboundSetEntityMotionPacket;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.item.component.ItemLore;
import net.minecraft.world.item.enchantment.Enchantment;
import net.minecraft.world.item.enchantment.EnchantmentHelper;
import net.minecraft.world.phys.Vec3;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * The Hollow King's wings: an elytra you can dash with.
 *
 * <p>Sneak while gliding and it throws you forward along your look. That is the whole
 * ability, and it is deliberately the whole ability - a vanilla client has no way to
 * show a new control, so the input has to be one the player already has and the
 * feedback has to be a vanilla sound, a vanilla particle and the action bar.
 *
 * <p>Thirty seconds between dashes, or twenty with <b>Fast Fly</b> on the wings - a
 * real, data-driven enchantment (1.21 lets a data pack add one), whose name is a
 * literal text component rather than a translation key so that a client with no
 * resource pack still reads "Fast Fly" instead of an enchantment id.
 */
public final class DashElytra {

    public static final String TAG = "beyond_dash_elytra";
    public static final ResourceKey<Enchantment> FAST_FLY = ResourceKey.create(
            Registries.ENCHANTMENT, Identifier.fromNamespaceAndPath(Beyond.MODID,
                    "fast_fly"));

    private static final Map<UUID, Long> LAST_DASH = new HashMap<>();

    private DashElytra() {
    }

    public static ItemStack create() {
        ItemStack stack = new ItemStack(Items.ELYTRA);
        CompoundTag tag = new CompoundTag();
        tag.putBoolean(TAG, true);
        stack.set(DataComponents.CUSTOM_DATA, CustomData.of(tag));
        stack.set(DataComponents.CUSTOM_NAME, Component.literal("Wings of the Hollow King")
                .withStyle(ChatFormatting.LIGHT_PURPLE));
        stack.set(DataComponents.LORE, new ItemLore(List.of(
                Component.literal("Sneak while gliding to dash")
                        .withStyle(ChatFormatting.GRAY),
                Component.literal("Taken from the King's back")
                        .withStyle(ChatFormatting.DARK_GRAY))));
        return stack;
    }

    public static boolean isDashElytra(ItemStack stack) {
        CustomData data = stack.get(DataComponents.CUSTOM_DATA);
        return data != null && data.copyTag().getBooleanOr(TAG, false);
    }

    /** How long between dashes for these wings, in ticks. */
    private static int cooldownTicks(MinecraftServer server, ItemStack wings,
                                     BeyondConfig config) {
        int seconds = config.dash_cooldown_seconds;
        var registry = server.registryAccess().lookupOrThrow(Registries.ENCHANTMENT);
        var holder = registry.get(FAST_FLY).orElse(null);
        if (holder != null && EnchantmentHelper.getItemEnchantmentLevel(holder, wings) > 0) {
            seconds = config.dash_cooldown_seconds_fast;
        }
        return seconds * 20;
    }

    /**
     * Called once a tick per player. Sneaking while gliding is the trigger, because it
     * is an input every vanilla client already has and it means nothing else mid-flight.
     */
    public static void onTick(MinecraftServer server, ServerPlayer player,
                              BeyondConfig config, long tick) {
        if (!player.isFallFlying() || !player.isShiftKeyDown()) {
            return;
        }
        tryDash(server, player, config, tick);
    }

    /**
     * Everything the dash does once the input has happened: the wings check, the
     * cooldown, the enchantment, the shove.
     *
     * <p>Split out from {@link #onTick} on purpose. Getting a headless test client to
     * actually glide turned out to be the hard part of testing this, so
     * {@code /beyond dash} calls straight into here - which means the cooldown, the
     * Fast Fly lookup and the impulse are all covered by a test, and the only thing
     * left resting on inspection is the two-line input condition above.
     *
     * @return null if it dashed, otherwise why not
     */
    public static String tryDash(MinecraftServer server, ServerPlayer player,
                                 BeyondConfig config, long tick) {
        ItemStack wings = player.getItemBySlot(EquipmentSlot.CHEST);
        if (!isDashElytra(wings)) {
            return "not wearing the Wings of the Hollow King";
        }
        // "never dashed" has to be absence, not a sentinel: tick - Long.MIN_VALUE
        // overflows to a large negative number, which reads as "still on cooldown"
        // and refuses the very first dash forever.
        Long last = LAST_DASH.get(player.getUUID());
        int cooldown = cooldownTicks(server, wings, config);
        if (last != null && tick - last < cooldown) {
            long left = (cooldown - (tick - last) + 19) / 20;
            player.sendSystemMessage(Component.literal("Wings recovering - " + left + "s")
                    .withStyle(ChatFormatting.DARK_GRAY), true);
            return "recovering for another " + left + "s";
        }
        dash(player, config, tick);
        return null;
    }

    /** Seconds between dashes for the wings this player is wearing. */
    public static int cooldownSeconds(MinecraftServer server, ServerPlayer player,
                                      BeyondConfig config) {
        return cooldownTicks(server, player.getItemBySlot(EquipmentSlot.CHEST),
                config) / 20;
    }

    private static void dash(ServerPlayer player, BeyondConfig config, long tick) {
        Vec3 look = player.getLookAngle().normalize();
        player.setDeltaMovement(player.getDeltaMovement()
                .add(look.scale(config.dash_strength)));
        player.hurtMarked = true;
        player.connection.send(new ClientboundSetEntityMotionPacket(player));
        LAST_DASH.put(player.getUUID(), tick);

        ServerLevel level = (ServerLevel) player.level();
        level.sendParticles(ParticleTypes.END_ROD, player.getX(), player.getY(),
                player.getZ(), 40, 0.6, 0.6, 0.6, 0.25);
        level.playSound(null, player.blockPosition(), SoundEvents.ENDER_DRAGON_FLAP,
                SoundSource.PLAYERS, 1.2f, 1.4f);
        player.sendSystemMessage(Component.literal("Dash")
                .withStyle(ChatFormatting.LIGHT_PURPLE), true);
        Beyond.log("{} dashed", player.getName().getString());
    }

    public static void forget(UUID player) {
        LAST_DASH.remove(player);
    }
}
