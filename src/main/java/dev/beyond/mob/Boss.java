package dev.beyond.mob;

import dev.beyond.Beyond;
import dev.beyond.BeyondConfig;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.boss.wither.WitherBoss;
import net.minecraft.world.entity.monster.Endermite;
import net.minecraft.world.entity.monster.Shulker;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;

import java.util.List;

/**
 * The Hollow King - the End's own boss, and the only source of the Dashing Elytra.
 *
 * <p>A vanilla client cannot be shown a new entity, so the King is a wither wearing a
 * different name: it already flies, already has a boss bar the client draws for free
 * (the bar takes the entity's display name, so renaming it renames the bar), and
 * already shoots. Everything that makes it a fight rather than a buffed wither is
 * here - the health, the phases, the adds, and the fact that it will not let you stand
 * still and shoot it.
 *
 * <p>It is woken by using the dragon egg on the dais of a Throne City, so the fight is
 * something you go looking for rather than something that happens to you.
 */
public final class Boss {

    public static final String TAG = "beyond_hollow_king";
    private static final String NAME = "The Hollow King";

    private Boss() {
    }

    // ---------------------------------------------------------------- summoning

    public static boolean isKing(Entity entity) {
        return entity instanceof WitherBoss && entity.getTags().contains(TAG);
    }

    /** @return true if a king was woken here */
    public static boolean summon(ServerLevel level, BlockPos pos, ServerPlayer by,
                                 BeyondConfig config) {
        if (!level.getEntitiesOfClass(WitherBoss.class,
                new AABB(pos).inflate(96)).stream().anyMatch(Boss::isKing)) {
            WitherBoss king = EntityType.WITHER.create(level, EntitySpawnReason.EVENT);
            if (king == null) {
                return false;
            }
            king.snapTo(new net.minecraft.world.phys.Vec3(pos.getX() + 0.5,
                    pos.getY() + 4.0, pos.getZ() + 0.5), 0f, 0f);
            king.addTag(TAG);
            king.setCustomName(Component.literal(NAME)
                    .withStyle(ChatFormatting.LIGHT_PURPLE, ChatFormatting.BOLD));
            king.setCustomNameVisible(false);
            set(king, Attributes.MAX_HEALTH, config.hollow_king_health);
            set(king, Attributes.ARMOR, config.hollow_king_armor);
            set(king, Attributes.MOVEMENT_SPEED, config.hollow_king_speed);
            set(king, Attributes.FOLLOW_RANGE, 96.0);
            king.setHealth((float) config.hollow_king_health);
            // Skip the wither's own spawn sequence: it detonates the room, and the
            // room is a throne hall somebody built.
            king.setInvulnerableTicks(0);
            level.addFreshEntity(king);
            startTheme(level, pos);
            level.playSound(null, pos, SoundEvents.WITHER_SPAWN, SoundSource.HOSTILE,
                    2.0f, 0.6f);
            announce(level.getServer(), Component.literal(NAME)
                    .withStyle(ChatFormatting.LIGHT_PURPLE)
                    .append(Component.literal(" wakes.")
                            .withStyle(ChatFormatting.GRAY)));
            Beyond.log("hollow king woken by {} at {}", by.getName().getString(), pos);
            return true;
        }
        by.sendSystemMessage(Component.literal("The King is already awake.")
                .withStyle(ChatFormatting.GRAY), true);
        return false;
    }

    private static void set(WitherBoss king,
                            net.minecraft.core.Holder<Attribute> which, double value) {
        AttributeInstance instance = king.getAttribute(which);
        if (instance != null) {
            instance.setBaseValue(value);
        }
    }

    // ---------------------------------------------------------------- the fight

    /**
     * Three phases, each one taking away a way of fighting it easily.
     *
     * <ul>
     *   <li>Full - a wither, but faster and much harder to kill.
     *   <li>Under two thirds - it calls shulkers, so the air above you stops being safe.
     *   <li>Under a third - it pulls you off the ground and blinds you, so bow duelling
     *       from a ledge stops working, and it starts healing unless you keep hitting it.
     * </ul>
     */
    public static void onTick(MinecraftServer server, BeyondConfig config, long tick) {
        if (tick % 20 != 0) {
            return;
        }
        for (ServerLevel level : server.getAllLevels()) {
            for (WitherBoss king : level.getEntitiesOfClass(WitherBoss.class,
                    new AABB(-3.0E7, level.getMinY(), -3.0E7,
                            3.0E7, level.getMaxY(), 3.0E7), Boss::isKing)) {
                fight(level, king, config, tick);
            }
        }
    }

    private static void fight(ServerLevel level, WitherBoss king, BeyondConfig config,
                              long tick) {
        float fraction = king.getHealth() / king.getMaxHealth();
        List<ServerPlayer> near = level.getEntitiesOfClass(ServerPlayer.class,
                king.getBoundingBox().inflate(48), p -> !p.isCreative()
                        && !p.isSpectator());
        if (near.isEmpty()) {
            return;
        }
        level.sendParticles(ParticleTypes.PORTAL, king.getX(), king.getY() + 1,
                king.getZ(), 12, 1.2, 1.2, 1.2, 0.4);

        if (fraction < 0.66f && tick % 200 == 0) {
            summonGuards(level, king, config);
        }
        if (fraction < 0.33f) {
            if (tick % 120 == 0) {
                for (ServerPlayer player : near) {
                    player.addEffect(new MobEffectInstance(MobEffects.LEVITATION, 60, 0));
                    player.addEffect(new MobEffectInstance(MobEffects.BLINDNESS, 60, 0));
                }
                level.playSound(null, king.blockPosition(), SoundEvents.WITHER_AMBIENT,
                        SoundSource.HOSTILE, 2.0f, 0.5f);
            }
            // It mends itself, so a long-range war of attrition is not a strategy.
            if (tick % 60 == 0 && king.getHealth() < king.getMaxHealth()) {
                king.heal((float) config.hollow_king_regen);
            }
        }
    }

    private static void summonGuards(ServerLevel level, WitherBoss king,
                                     BeyondConfig config) {
        for (int i = 0; i < config.hollow_king_guards; i++) {
            double a = i * (Math.PI * 2 / config.hollow_king_guards);
            double x = king.getX() + Math.cos(a) * 5;
            double z = king.getZ() + Math.sin(a) * 5;
            Entity guard = (i % 2 == 0)
                    ? EntityType.SHULKER.create(level, EntitySpawnReason.EVENT)
                    : EntityType.ENDERMITE.create(level, EntitySpawnReason.EVENT);
            if (guard == null) {
                continue;
            }
            guard.snapTo(new net.minecraft.world.phys.Vec3(x, king.getY() - 1, z), 0f, 0f);
            guard.addTag(TAG + "_guard");
            if (guard instanceof Shulker s) {
                s.setCustomName(Component.literal("Throne Guard")
                        .withStyle(ChatFormatting.DARK_PURPLE));
            } else if (guard instanceof Endermite m) {
                m.setCustomName(Component.literal("Throne Mite")
                        .withStyle(ChatFormatting.DARK_PURPLE));
                m.setPersistenceRequired();
            }
            level.addFreshEntity(guard);
        }
        level.playSound(null, king.blockPosition(), SoundEvents.SHULKER_OPEN,
                SoundSource.HOSTILE, 1.6f, 0.6f);
    }

    // ---------------------------------------------------------------- the end of it

    private static final net.minecraft.resources.Identifier THEME =
            net.minecraft.resources.Identifier.parse("beyond:music.beyond.hollow_king");

    /** The boss theme, for everyone near the throne: whatever was playing stops first. */
    public static void startTheme(ServerLevel level, BlockPos at) {
        for (ServerPlayer player : level.getPlayers(p -> p.blockPosition().closerThan(at, 128))) {
            player.connection.send(new net.minecraft.network.protocol.game.ClientboundStopSoundPacket(
                    null, net.minecraft.sounds.SoundSource.MUSIC));
        }
        level.playSound(null, at, net.minecraft.sounds.SoundEvent.createVariableRangeEvent(THEME),
                net.minecraft.sounds.SoundSource.MUSIC, 8.0f, 1.0f);
    }

    public static void stopTheme(ServerLevel level, BlockPos at) {
        for (ServerPlayer player : level.getPlayers(p -> p.blockPosition().closerThan(at, 192))) {
            player.connection.send(new net.minecraft.network.protocol.game.ClientboundStopSoundPacket(
                    THEME, net.minecraft.sounds.SoundSource.MUSIC));
        }
    }

    public static void onDeath(ServerLevel level, LivingEntity dead) {
        if (!isKing(dead)) {
            return;
        }
        ItemStack wings = DashElytra.create();
        stopTheme(level, dead.blockPosition());
        dead.spawnAtLocation(level, wings);
        level.playSound(null, dead.blockPosition(), SoundEvents.END_PORTAL_SPAWN,
                SoundSource.HOSTILE, 2.0f, 1.2f);
        // Its guard dies with it, so the arena is not left full of shulkers.
        for (Entity guard : level.getEntitiesOfClass(Entity.class,
                dead.getBoundingBox().inflate(64),
                e -> e.getTags().contains(TAG + "_guard"))) {
            guard.discard();
        }
        announce(level.getServer(), Component.literal(NAME)
                .withStyle(ChatFormatting.LIGHT_PURPLE)
                .append(Component.literal(" has fallen. The wings are loose.")
                        .withStyle(ChatFormatting.GRAY)));
        Beyond.log("hollow king killed");
    }

    private static void announce(MinecraftServer server, Component message) {
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            player.sendSystemMessage(message);
        }
    }
}
