package dev.beyond.item;

import dev.beyond.Advancements;
import dev.beyond.Beyond;
import dev.beyond.BeyondConfig;
import dev.beyond.Cooldowns;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.util.List;

/**
 * The relics: one per structure, each with an ability, none obtainable any other way.
 *
 * <p>Every ability reads back on the action bar and plays a vanilla sound and particle, because
 * with no resource pack those are the only ways an ability can be seen to have happened.
 */
public final class Specials {

    private Specials() {
    }

    /** Shared plumbing: cooldown check, feedback, logging. */
    abstract static class Relic extends BeyondItem {
        private final String id;
        private final Item base;
        private final String name;
        private final String source;

        Relic(String id, Item base, String name, String source) {
            this.id = id;
            this.base = base;
            this.name = name;
            this.source = source;
        }

        @Override
        public String id() {
            return id;
        }

        @Override
        public Item baseItem() {
            return base;
        }

        @Override
        public Component displayName() {
            return Component.literal(name)
                    .withStyle(style -> style.withColor(ChatFormatting.GOLD).withBold(true).withItalic(false));
        }

        @Override
        public String source() {
            return source;
        }

        @Override
        public void customise(ItemStack stack, BeyondConfig config) {
            stack.set(DataComponents.ENCHANTMENT_GLINT_OVERRIDE, true);
        }

        abstract int cooldown(BeyondConfig config);

        abstract boolean fire(ServerPlayer player, ServerLevel level, BeyondConfig config);

        @Override
        public boolean onRightClick(ServerPlayer player, ItemStack stack, BeyondConfig config) {
            Cooldowns cooldowns = Beyond.cooldowns();
            int left = cooldowns.remaining(player, id);
            if (left > 0) {
                player.displayClientMessage(Component.literal(String.format("%s  %.1fs", name, left / 20.0))
                        .withStyle(ChatFormatting.GRAY), true);
                return true;
            }
            if (!(player.level() instanceof ServerLevel level) || !fire(player, level, config)) {
                return true;
            }
            cooldowns.set(player, id, cooldown(config), stack);
            player.displayClientMessage(Component.literal(name).withStyle(ChatFormatting.GOLD), true);
            Beyond.log("relic {} used by {}", id, player.getName().getString());
            return true;
        }

        void feedback(ServerPlayer player, ServerLevel level, SoundEvent sound, float pitch,
                      net.minecraft.core.particles.ParticleOptions particle, int count) {
            level.playSound(null, player.getX(), player.getY(), player.getZ(), sound, SoundSource.PLAYERS, 1.0f, pitch);
            level.sendParticles(particle, player.getX(), player.getY() + 1.0, player.getZ(), count, 0.5, 0.6, 0.5, 0.05);
        }
    }

    public static final BeyondItem CHORUS_LANTERN = new Relic("chorus_lantern", Items.SOUL_LANTERN,
            "Chorus Lantern", "Violecite Ruin") {
        @Override
        public List<Component> lore(BeyondConfig config) {
            return List.of(BeyondItems.loreLine(String.format("Right-click: blink %.0f blocks forward",
                            config.chorus_lantern_range)),
                    BeyondItems.loreLine("No pearl, no fall, no damage"),
                    BeyondItems.loreLine(String.format("Cooldown %.0fs", config.chorus_lantern_cooldown_ticks / 20.0)));
        }

        @Override
        int cooldown(BeyondConfig config) {
            return config.chorus_lantern_cooldown_ticks;
        }

        @Override
        boolean fire(ServerPlayer player, ServerLevel level, BeyondConfig config) {
            Vec3 look = player.getLookAngle().normalize();
            Vec3 from = player.position();
            // Walk the line back from the far end until there is room for a player.
            for (double d = config.chorus_lantern_range; d >= 1.0; d -= 0.5) {
                Vec3 to = from.add(look.scale(d));
                BlockPos feet = BlockPos.containing(to);
                if (level.getBlockState(feet).getCollisionShape(level, feet).isEmpty()
                        && level.getBlockState(feet.above()).getCollisionShape(level, feet.above()).isEmpty()) {
                    feedback(player, level, SoundEvents.CHORUS_FRUIT_TELEPORT, 1.0f, ParticleTypes.PORTAL, 40);
                    player.teleportTo(to.x, to.y, to.z);
                    level.sendParticles(ParticleTypes.PORTAL, to.x, to.y + 1.0, to.z, 40, 0.5, 0.6, 0.5, 0.05);
                    return true;
                }
            }
            player.displayClientMessage(Component.literal("No room to blink there.").withStyle(ChatFormatting.GRAY), true);
            return false;
        }
    };

    public static final BeyondItem CRYSTAL_FOCUS = new Relic("crystal_focus", Items.PRISMARINE_SHARD,
            "Crystal Focus", "Crystal Shrine") {
        @Override
        public List<Component> lore(BeyondConfig config) {
            return List.of(BeyondItems.loreLine(String.format("Right-click: every monster within %.0f blocks glows",
                            config.crystal_focus_radius)),
                    BeyondItems.loreLine(String.format("for %.0fs, through walls", config.crystal_focus_glow_ticks / 20.0)),
                    BeyondItems.loreLine(String.format("Cooldown %.0fs", config.crystal_focus_cooldown_ticks / 20.0)));
        }

        @Override
        int cooldown(BeyondConfig config) {
            return config.crystal_focus_cooldown_ticks;
        }

        @Override
        boolean fire(ServerPlayer player, ServerLevel level, BeyondConfig config) {
            AABB box = player.getBoundingBox().inflate(config.crystal_focus_radius);
            int lit = 0;
            for (Monster monster : level.getEntitiesOfClass(Monster.class, box)) {
                monster.addEffect(new MobEffectInstance(MobEffects.GLOWING, config.crystal_focus_glow_ticks, 0));
                lit++;
            }
            feedback(player, level, SoundEvents.AMETHYST_BLOCK_CHIME, 1.4f, ParticleTypes.END_ROD, 30);
            player.displayClientMessage(Component.literal("Crystal Focus  " + lit + " revealed")
                    .withStyle(ChatFormatting.GOLD), true);
            return true;
        }
    };

    public static final BeyondItem AMBER_HEART = new Relic("amber_heart", Items.HEART_OF_THE_SEA,
            "Amber Heart", "Amber Vault") {
        @Override
        public List<Component> lore(BeyondConfig config) {
            return List.of(BeyondItems.loreLine(String.format("Right-click: Regeneration II and Absorption for %.0fs",
                            config.amber_heart_regen_ticks / 20.0)),
                    BeyondItems.loreLine(String.format("Cooldown %.0fs", config.amber_heart_cooldown_ticks / 20.0)));
        }

        @Override
        int cooldown(BeyondConfig config) {
            return config.amber_heart_cooldown_ticks;
        }

        @Override
        boolean fire(ServerPlayer player, ServerLevel level, BeyondConfig config) {
            player.addEffect(new MobEffectInstance(MobEffects.REGENERATION, config.amber_heart_regen_ticks, 1));
            player.addEffect(new MobEffectInstance(MobEffects.ABSORPTION, config.amber_heart_regen_ticks * 2, 1));
            feedback(player, level, SoundEvents.BEACON_POWER_SELECT, 1.2f, ParticleTypes.HEART, 12);
            return true;
        }
    };

    public static final BeyondItem VEIL_OF_SHADOWS = new Relic("veil_of_shadows", Items.PHANTOM_MEMBRANE,
            "Veil of Shadows", "Shadow Nest") {
        @Override
        public List<Component> lore(BeyondConfig config) {
            return List.of(BeyondItems.loreLine(String.format("Right-click: Invisibility for %.0fs",
                            config.veil_invisibility_ticks / 20.0)),
                    BeyondItems.loreLine("Your armour still shows. Take it off."),
                    BeyondItems.loreLine(String.format("Cooldown %.0fs", config.veil_cooldown_ticks / 20.0)));
        }

        @Override
        int cooldown(BeyondConfig config) {
            return config.veil_cooldown_ticks;
        }

        @Override
        boolean fire(ServerPlayer player, ServerLevel level, BeyondConfig config) {
            player.addEffect(new MobEffectInstance(MobEffects.INVISIBILITY, config.veil_invisibility_ticks, 0));
            feedback(player, level, SoundEvents.PHANTOM_FLAP, 0.7f, ParticleTypes.ASH, 40);
            return true;
        }
    };

    public static final BeyondItem TIDAL_LENS = new Relic("tidal_lens", Items.NAUTILUS_SHELL,
            "Tidal Lens", "Sunken Observatory") {
        @Override
        public List<Component> lore(BeyondConfig config) {
            return List.of(BeyondItems.loreLine(String.format("Right-click: Water Breathing and Conduit Power for %.0fs",
                            config.tidal_lens_ticks / 20.0)),
                    BeyondItems.loreLine(String.format("Cooldown %.0fs", config.tidal_lens_cooldown_ticks / 20.0)));
        }

        @Override
        int cooldown(BeyondConfig config) {
            return config.tidal_lens_cooldown_ticks;
        }

        @Override
        boolean fire(ServerPlayer player, ServerLevel level, BeyondConfig config) {
            player.addEffect(new MobEffectInstance(MobEffects.WATER_BREATHING, config.tidal_lens_ticks, 0));
            player.addEffect(new MobEffectInstance(MobEffects.CONDUIT_POWER, config.tidal_lens_ticks, 0));
            feedback(player, level, SoundEvents.CONDUIT_ACTIVATE, 1.0f, ParticleTypes.BUBBLE_POP, 30);
            return true;
        }
    };

    public static final BeyondItem STARFALL_SHARD = new Relic("starfall_shard", Items.QUARTZ,
            "Starfall Shard", "Starfall Cairn") {
        @Override
        public List<Component> lore(BeyondConfig config) {
            return List.of(BeyondItems.loreLine(String.format("Right-click: Slow Falling and Speed for %.0fs",
                            config.starfall_shard_ticks / 20.0)),
                    BeyondItems.loreLine("The void is a little less final"),
                    BeyondItems.loreLine(String.format("Cooldown %.0fs", config.starfall_shard_cooldown_ticks / 20.0)));
        }

        @Override
        int cooldown(BeyondConfig config) {
            return config.starfall_shard_cooldown_ticks;
        }

        @Override
        boolean fire(ServerPlayer player, ServerLevel level, BeyondConfig config) {
            player.addEffect(new MobEffectInstance(MobEffects.SLOW_FALLING, config.starfall_shard_ticks, 0));
            player.addEffect(new MobEffectInstance(MobEffects.SPEED, config.starfall_shard_ticks, 0));
            feedback(player, level, SoundEvents.AMETHYST_BLOCK_RESONATE, 1.6f, ParticleTypes.SNOWFLAKE, 40);
            return true;
        }
    };

    /** The portal key. No ability of its own; the pedestal is what it is for. */
    public static final BeyondItem ETERNAL_CRYSTAL = new SimpleItem("eternal_crystal", Items.AMETHYST_SHARD,
            "Eternal Crystal", ChatFormatting.LIGHT_PURPLE, "forged",
            "Set into a pedestal of an Eternal Portal", "Six of them open the way home") {
        @Override
        public void customise(ItemStack stack, BeyondConfig config) {
            stack.set(DataComponents.ENCHANTMENT_GLINT_OVERRIDE, true);
        }
    };


    /**
     * The Gale Rod - the one relic you make rather than find.
     *
     * <p>Everything else in this class is pulled out of a structure. This is crafted,
     * from two breeze rods, a stick and a netherite ingot, and it does the one thing
     * the King's wings cannot: it throws you straight up. Wings carry you forward
     * once you are already flying; the rod is how you get off the ground, or off a
     * ledge you have just been knocked from.
     */
    /**
     * How high a launch at this speed actually carries you, by running vanilla's own
     * gravity forward a tick at a time. The lore quotes a real number this way, and keeps
     * quoting a real one if the config changes.
     */
    private static double apex(double speed) {
        double height = 0;
        for (double v = speed; v > 0; v = (v - 0.08) * 0.98) {
            height += v;
        }
        return height;
    }

    public static final BeyondItem GALE_ROD = new Relic("gale_rod", Items.BREEZE_ROD,
            "Gale Rod", "crafted: 2 breeze rods, a stick and a netherite ingot") {
        @Override
        public List<Component> lore(BeyondConfig config) {
            return List.of(BeyondItems.loreLine(String.format("Right-click: leap about %.0f blocks straight up",
                            apex(config.gale_rod_lift))),
                    BeyondItems.loreLine("The fall it saves you from is your own problem"),
                    BeyondItems.loreLine(String.format("Cooldown %.0fs",
                            config.gale_rod_cooldown_ticks / 20.0)));
        }

        @Override
        int cooldown(BeyondConfig config) {
            return config.gale_rod_cooldown_ticks;
        }

        @Override
        boolean fire(ServerPlayer player, ServerLevel level, BeyondConfig config) {
            // Replace downward motion rather than adding to it, so using it while
            // already falling is a rescue and not a slightly slower fall.
            Vec3 motion = player.getDeltaMovement();
            player.setDeltaMovement(motion.x, config.gale_rod_lift, motion.z);
            player.hurtMarked = true;
            player.connection.send(
                    new net.minecraft.network.protocol.game.ClientboundSetEntityMotionPacket(player));
            player.resetFallDistance();
            feedback(player, level, SoundEvents.BREEZE_JUMP, 1.0f,
                    ParticleTypes.GUST, 30);
            return true;
        }
    };

    /** The Void Warden's heart: a step through the void, along your look, to solid footing. */
    public static final BeyondItem VOID_HEART = new Relic("void_heart", Items.NETHER_STAR,
            "Void Heart", "The Void Warden") {
        @Override
        public List<Component> lore(BeyondConfig config) {
            return List.of(BeyondItems.loreLine(String.format("Right-click: step up to %.0f blocks through the void",
                            config.void_heart_range)),
                    BeyondItems.loreLine("along your look, to solid footing, and land softly"),
                    BeyondItems.loreLine(String.format("Cooldown %.0fs", config.void_heart_cooldown_ticks / 20.0)),
                    BeyondItems.loreLine("Cut from the Void Warden"));
        }

        @Override
        int cooldown(BeyondConfig config) {
            return config.void_heart_cooldown_ticks;
        }

        @Override
        boolean fire(ServerPlayer player, ServerLevel level, BeyondConfig config) {
            Vec3 look = player.getLookAngle().normalize();
            Vec3 from = player.position();
            for (double d = config.void_heart_range; d >= 1.0; d -= 0.5) {
                Vec3 to = from.add(look.scale(d));
                BlockPos feet = BlockPos.containing(to);
                if (level.getBlockState(feet).getCollisionShape(level, feet).isEmpty()
                        && level.getBlockState(feet.above()).getCollisionShape(level, feet.above()).isEmpty()) {
                    feedback(player, level, SoundEvents.WARDEN_SONIC_CHARGE, 1.3f, ParticleTypes.SCULK_SOUL, 40);
                    player.teleportTo(to.x, to.y, to.z);
                    player.addEffect(new MobEffectInstance(MobEffects.SLOW_FALLING, 60, 0));
                    level.sendParticles(ParticleTypes.SCULK_SOUL, to.x, to.y + 1.0, to.z, 40, 0.5, 0.6, 0.5, 0.05);
                    level.playSound(null, to.x, to.y, to.z, SoundEvents.WARDEN_TENDRIL_CLICKS, SoundSource.PLAYERS, 1.0f, 0.6f);
                    return true;
                }
            }
            player.displayClientMessage(Component.literal("Nowhere to step to.").withStyle(ChatFormatting.GRAY), true);
            return false;
        }
    };

    /** The Gale Sovereign's horn: a blast of wind that throws everything near you away. */
    public static final BeyondItem TEMPEST_HORN = new Relic("tempest_horn", Items.GOAT_HORN,
            "Tempest Horn", "The Gale Sovereign") {
        @Override
        public List<Component> lore(BeyondConfig config) {
            return List.of(BeyondItems.loreLine(String.format("Right-click: a blast of wind throws everything within %.0f blocks",
                            config.tempest_horn_radius)),
                    BeyondItems.loreLine("away from you, and carries you gently down for 15s"),
                    BeyondItems.loreLine(String.format("Cooldown %.0fs", config.tempest_horn_cooldown_ticks / 20.0)),
                    BeyondItems.loreLine("Torn from the Gale Sovereign"));
        }

        @Override
        int cooldown(BeyondConfig config) {
            return config.tempest_horn_cooldown_ticks;
        }

        @Override
        boolean fire(ServerPlayer player, ServerLevel level, BeyondConfig config) {
            AABB box = player.getBoundingBox().inflate(config.tempest_horn_radius);
            int thrown = 0;
            for (net.minecraft.world.entity.LivingEntity target : level.getEntitiesOfClass(
                    net.minecraft.world.entity.LivingEntity.class, box, e -> e != player && e.isAlive())) {
                Vec3 away = target.position().subtract(player.position());
                Vec3 flat = new Vec3(away.x, 0, away.z);
                flat = flat.lengthSqr() < 0.01 ? player.getLookAngle().multiply(1, 0, 1).normalize() : flat.normalize();
                target.setDeltaMovement(flat.scale(config.tempest_horn_power).add(0, config.tempest_horn_power * 0.5, 0));
                target.hurtMarked = true;
                if (target instanceof ServerPlayer other) {
                    other.connection.send(new net.minecraft.network.protocol.game.ClientboundSetEntityMotionPacket(other));
                }
                thrown++;
            }
            player.addEffect(new MobEffectInstance(MobEffects.SLOW_FALLING, 300, 0));
            feedback(player, level, SoundEvents.BREEZE_WIND_CHARGE_BURST.value(), 0.9f, ParticleTypes.CLOUD, 50);
            level.sendParticles(ParticleTypes.GUST_EMITTER_SMALL, player.getX(), player.getY() + 0.5, player.getZ(), 1, 0, 0, 0, 0);
            player.displayClientMessage(Component.literal("Tempest Horn  " + thrown + " thrown")
                    .withStyle(ChatFormatting.GOLD), true);
            return true;
        }
    };

    public static List<BeyondItem> all() {
        return List.of(CHORUS_LANTERN, CRYSTAL_FOCUS, AMBER_HEART, VEIL_OF_SHADOWS, TIDAL_LENS, STARFALL_SHARD,
                ETERNAL_CRYSTAL, GALE_ROD, VOID_HEART, TEMPEST_HORN);
    }

    /** Called when a relic first reaches a player's hands. */
    public static void onRelicObtained(ServerPlayer player) {
        Advancements.grant(player, "relic");
    }
}
