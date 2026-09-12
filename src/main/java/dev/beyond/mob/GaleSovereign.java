package dev.beyond.mob;

import dev.beyond.Beyond;
import dev.beyond.BeyondConfig;
import dev.beyond.item.BeyondItems;
import dev.beyond.item.Specials;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.game.ClientboundSetEntityMotionPacket;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.BossEvent;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.monster.Phantom;
import net.minecraft.world.entity.monster.breeze.Breeze;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * The Gale Sovereign - what the wind serves on top of a Storm Spire, and the only source
 * of the Tempest Horn.
 *
 * <p>A breeze the client already knows how to draw, with a boss bar the server puts up
 * for it. Woken by using the lightning rod on the spire's dais. It fights the way a
 * breeze does - leaping, shooting wind - and then some.
 */
public final class GaleSovereign {

    public static final String TAG = "beyond_gale_sovereign";
    private static final String NAME = "The Gale Sovereign";
    private static final Component DISPLAY = Component.literal(NAME)
            .withStyle(ChatFormatting.AQUA, ChatFormatting.BOLD);

    private GaleSovereign() {
    }

    public static boolean is(Entity entity) {
        return entity instanceof Breeze && entity.getTags().contains(TAG);
    }

    /** @return true if a Sovereign was woken here */
    public static boolean summon(ServerLevel level, BlockPos pos, ServerPlayer by, BeyondConfig config) {
        if (level.getEntitiesOfClass(Breeze.class, new AABB(pos).inflate(96)).stream().anyMatch(GaleSovereign::is)) {
            by.sendSystemMessage(Component.literal("The Sovereign is already awake.")
                    .withStyle(ChatFormatting.GRAY), true);
            return false;
        }
        Breeze breeze = EntityType.BREEZE.create(level, EntitySpawnReason.EVENT);
        if (breeze == null) {
            return false;
        }
        breeze.snapTo(new Vec3(pos.getX() + 0.5, pos.getY() + 1.0, pos.getZ() + 0.5), 0f, 0f);
        breeze.addTag(TAG);
        breeze.addTag(Mobs.TAG_DRESSED);
        breeze.setCustomName(DISPLAY);
        breeze.setCustomNameVisible(false);
        set(breeze, Attributes.MAX_HEALTH, config.gale_sovereign_health);
        set(breeze, Attributes.ARMOR, config.gale_sovereign_armor);
        set(breeze, Attributes.FOLLOW_RANGE, 64.0);
        breeze.setHealth((float) config.gale_sovereign_health);
        breeze.setPersistenceRequired();
        level.addFreshEntity(breeze);
        Boss.startTheme(level, pos);
        level.playSound(null, pos, SoundEvents.BREEZE_CHARGE, SoundSource.HOSTILE, 2.0f, 0.6f);
        level.playSound(null, pos, SoundEvents.LIGHTNING_BOLT_THUNDER, SoundSource.HOSTILE, 1.5f, 1.2f);
        level.sendParticles(ParticleTypes.CLOUD, pos.getX() + 0.5, pos.getY() + 1.5, pos.getZ() + 0.5,
                60, 2.0, 1.0, 2.0, 0.1);
        BossBars.announce(level.getServer(), Component.literal(NAME).withStyle(ChatFormatting.AQUA)
                .append(Component.literal(" rises on the wind.").withStyle(ChatFormatting.GRAY)));
        Beyond.log("gale sovereign woken by {} at {}", by.getName().getString(), pos);
        return true;
    }

    private static void set(Breeze breeze, net.minecraft.core.Holder<Attribute> which, double value) {
        AttributeInstance instance = breeze.getAttribute(which);
        if (instance != null) {
            instance.setBaseValue(value);
        }
    }

    /** Once a second, from {@link BossBars#onTick}. @return the ids of the Sovereigns alive */
    static Set<UUID> tick(MinecraftServer server, BeyondConfig config, long tick) {
        Set<UUID> alive = new HashSet<>();
        for (ServerLevel level : server.getAllLevels()) {
            for (Breeze breeze : level.getEntitiesOfClass(Breeze.class,
                    new AABB(-3.0E7, level.getMinY(), -3.0E7, 3.0E7, level.getMaxY(), 3.0E7), GaleSovereign::is)) {
                alive.add(breeze.getUUID());
                fight(level, breeze, config, tick);
            }
        }
        return alive;
    }

    /**
     * <ul>
     *   <li>Full - a breeze with boss health, on a platform in the sky.
     *   <li>Under two thirds - every six seconds a gust throws everyone near it outward
     *       and upward. On a spire top, that is the point.
     *   <li>Under a third - it calls Gale Wisps, quickens, and mends itself unless you
     *       keep hitting it.
     * </ul>
     */
    private static void fight(ServerLevel level, Breeze breeze, BeyondConfig config, long tick) {
        BossBars.track(level, breeze, DISPLAY, BossEvent.BossBarColor.BLUE);
        List<ServerPlayer> near = level.getEntitiesOfClass(ServerPlayer.class,
                breeze.getBoundingBox().inflate(40), p -> !p.isCreative() && !p.isSpectator());
        if (near.isEmpty()) {
            return;
        }
        level.sendParticles(ParticleTypes.CLOUD, breeze.getX(), breeze.getY() + 1.0, breeze.getZ(),
                6, 0.8, 0.6, 0.8, 0.02);
        float fraction = breeze.getHealth() / breeze.getMaxHealth();
        if (fraction < 0.66f && tick % 120 == 0) {
            for (ServerPlayer player : near) {
                Vec3 away = player.position().subtract(breeze.position());
                Vec3 flat = new Vec3(away.x, 0, away.z);
                flat = flat.lengthSqr() < 0.01 ? new Vec3(1, 0, 0) : flat.normalize();
                player.setDeltaMovement(flat.scale(config.gale_sovereign_gust).add(0, config.gale_sovereign_gust * 0.6, 0));
                player.hurtMarked = true;
                player.connection.send(new ClientboundSetEntityMotionPacket(player));
            }
            level.playSound(null, breeze.blockPosition(), SoundEvents.BREEZE_WIND_CHARGE_BURST.value(), SoundSource.HOSTILE, 2.0f, 0.7f);
            level.sendParticles(ParticleTypes.GUST_EMITTER_LARGE, breeze.getX(), breeze.getY() + 0.5, breeze.getZ(), 1, 0, 0, 0, 0);
        }
        if (fraction < 0.33f) {
            AttributeInstance speed = breeze.getAttribute(Attributes.MOVEMENT_SPEED);
            if (speed != null && speed.getBaseValue() < 0.9) {
                speed.setBaseValue(0.9);
            }
            if (tick % 240 == 0) {
                summonWisps(level, breeze, config);
            }
            if (tick % 40 == 0 && breeze.getHealth() < breeze.getMaxHealth()) {
                breeze.heal(1.5f);
            }
        }
    }

    private static void summonWisps(ServerLevel level, Breeze breeze, BeyondConfig config) {
        for (int i = 0; i < config.gale_sovereign_wisps; i++) {
            Phantom wisp = EntityType.PHANTOM.create(level, EntitySpawnReason.EVENT);
            if (wisp == null) {
                continue;
            }
            double a = i * (Math.PI * 2 / Math.max(1, config.gale_sovereign_wisps));
            wisp.snapTo(new Vec3(breeze.getX() + Math.cos(a) * 4, breeze.getY() + 6, breeze.getZ() + Math.sin(a) * 4), 0f, 0f);
            wisp.setPhantomSize(2);
            wisp.addTag(TAG + "_wisp");
            wisp.addTag(Mobs.TAG_DRESSED);
            wisp.setCustomName(Component.literal("Gale Wisp").withStyle(ChatFormatting.AQUA));
            wisp.setPersistenceRequired();
            level.addFreshEntity(wisp);
        }
        level.playSound(null, breeze.blockPosition(), SoundEvents.PHANTOM_AMBIENT, SoundSource.HOSTILE, 1.6f, 0.8f);
    }

    public static void onDeath(ServerLevel level, LivingEntity dead) {
        if (!is(dead)) {
            return;
        }
        Boss.stopTheme(level, dead.blockPosition());
        BossBars.drop(dead);
        dead.spawnAtLocation(level, BeyondItems.create(Specials.TEMPEST_HORN, 1));
        level.playSound(null, dead.blockPosition(), SoundEvents.BREEZE_DEATH, SoundSource.HOSTILE, 2.0f, 0.6f);
        level.playSound(null, dead.blockPosition(), SoundEvents.LIGHTNING_BOLT_THUNDER, SoundSource.HOSTILE, 1.5f, 0.8f);
        for (Entity wisp : level.getEntitiesOfClass(Entity.class, dead.getBoundingBox().inflate(64),
                e -> e.getTags().contains(TAG + "_wisp"))) {
            wisp.discard();
        }
        BossBars.announce(level.getServer(), Component.literal(NAME).withStyle(ChatFormatting.AQUA)
                .append(Component.literal(" falls silent. The winds are yours.").withStyle(ChatFormatting.GRAY)));
        Beyond.log("gale sovereign killed");
    }
}
