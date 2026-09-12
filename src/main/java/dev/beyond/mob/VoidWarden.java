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
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.monster.Endermite;
import net.minecraft.world.entity.monster.warden.Warden;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * The Void Warden - what sleeps under a Void Crypt, and the only source of the Void Heart.
 *
 * <p>A warden the client already knows how to draw, wearing a different name and a boss
 * bar the server puts up for it. Woken by using the sculk shrieker on the crypt's dais.
 * A warden left alone digs back into the ground after a minute, which would end the fight
 * by walking away from it - so every second it is made angrier at whoever is nearest, and
 * it stays.
 */
public final class VoidWarden {

    public static final String TAG = "beyond_void_warden";
    private static final String NAME = "The Void Warden";
    private static final Component DISPLAY = Component.literal(NAME)
            .withStyle(ChatFormatting.DARK_AQUA, ChatFormatting.BOLD);

    private VoidWarden() {
    }

    public static boolean is(Entity entity) {
        return entity instanceof Warden && entity.getTags().contains(TAG);
    }

    /** @return true if a Warden was woken here */
    public static boolean summon(ServerLevel level, BlockPos pos, ServerPlayer by, BeyondConfig config) {
        if (level.getEntitiesOfClass(Warden.class, new AABB(pos).inflate(96)).stream().anyMatch(VoidWarden::is)) {
            by.sendSystemMessage(Component.literal("The Warden is already awake.")
                    .withStyle(ChatFormatting.GRAY), true);
            return false;
        }
        Warden warden = EntityType.WARDEN.create(level, EntitySpawnReason.EVENT);
        if (warden == null) {
            return false;
        }
        warden.snapTo(new Vec3(pos.getX() + 0.5, pos.getY() + 1.0, pos.getZ() + 0.5), 0f, 0f);
        warden.addTag(TAG);
        warden.addTag(Mobs.TAG_DRESSED);
        warden.setCustomName(DISPLAY);
        warden.setCustomNameVisible(false);
        set(warden, Attributes.MAX_HEALTH, config.void_warden_health);
        set(warden, Attributes.ARMOR, config.void_warden_armor);
        set(warden, Attributes.FOLLOW_RANGE, 64.0);
        warden.setHealth((float) config.void_warden_health);
        warden.setPersistenceRequired();
        level.addFreshEntity(warden);
        warden.increaseAngerAt(by, 150, false);
        Boss.startTheme(level, pos);
        level.playSound(null, pos, SoundEvents.WARDEN_EMERGE, SoundSource.HOSTILE, 2.0f, 0.8f);
        level.sendParticles(ParticleTypes.SCULK_SOUL, pos.getX() + 0.5, pos.getY() + 1.5, pos.getZ() + 0.5,
                60, 1.5, 1.0, 1.5, 0.05);
        BossBars.announce(level.getServer(), Component.literal(NAME).withStyle(ChatFormatting.DARK_AQUA)
                .append(Component.literal(" stirs beneath the crypt.").withStyle(ChatFormatting.GRAY)));
        Beyond.log("void warden woken by {} at {}", by.getName().getString(), pos);
        return true;
    }

    private static void set(Warden warden, net.minecraft.core.Holder<Attribute> which, double value) {
        AttributeInstance instance = warden.getAttribute(which);
        if (instance != null) {
            instance.setBaseValue(value);
        }
    }

    /** Once a second, from {@link BossBars#onTick}. @return the ids of the Wardens alive */
    static Set<UUID> tick(MinecraftServer server, BeyondConfig config, long tick) {
        Set<UUID> alive = new HashSet<>();
        for (ServerLevel level : server.getAllLevels()) {
            for (Warden warden : level.getEntitiesOfClass(Warden.class,
                    new AABB(-3.0E7, level.getMinY(), -3.0E7, 3.0E7, level.getMaxY(), 3.0E7), VoidWarden::is)) {
                alive.add(warden.getUUID());
                fight(level, warden, config, tick);
            }
        }
        return alive;
    }

    /**
     * Three phases, like the King's, each taking away an easy way to fight it.
     *
     * <ul>
     *   <li>Full - a warden with twice the health: hits like a truck, but slow.
     *   <li>Under two thirds - every eight seconds it pulls everyone near it in and
     *       darkens their sight, so keeping your distance stops being a plan.
     *   <li>Under a third - it calls Void Mites, steps through the void to whoever is
     *       farthest away, and mends itself unless you keep hitting it.
     * </ul>
     */
    private static void fight(ServerLevel level, Warden warden, BeyondConfig config, long tick) {
        BossBars.track(level, warden, DISPLAY, BossEvent.BossBarColor.PURPLE);
        List<ServerPlayer> near = level.getEntitiesOfClass(ServerPlayer.class,
                warden.getBoundingBox().inflate(40), p -> !p.isCreative() && !p.isSpectator());
        if (near.isEmpty()) {
            return;
        }
        ServerPlayer nearest = near.get(0);
        ServerPlayer farthest = near.get(0);
        for (ServerPlayer player : near) {
            if (player.distanceToSqr(warden) < nearest.distanceToSqr(warden)) {
                nearest = player;
            }
            if (player.distanceToSqr(warden) > farthest.distanceToSqr(warden)) {
                farthest = player;
            }
        }
        // Never calm enough to dig away, never without a target.
        warden.increaseAngerAt(nearest, 40, false);
        level.sendParticles(ParticleTypes.SCULK_SOUL, warden.getX(), warden.getY() + 1.5, warden.getZ(),
                8, 1.0, 1.0, 1.0, 0.02);

        float fraction = warden.getHealth() / warden.getMaxHealth();
        if (fraction < 0.66f && tick % 160 == 0) {
            for (ServerPlayer player : near) {
                Vec3 pull = warden.position().subtract(player.position());
                Vec3 flat = new Vec3(pull.x, 0, pull.z);
                if (flat.lengthSqr() > 1.0) {
                    flat = flat.normalize().scale(1.1);
                }
                player.setDeltaMovement(player.getDeltaMovement().add(flat.x, 0.35, flat.z));
                player.hurtMarked = true;
                player.connection.send(new ClientboundSetEntityMotionPacket(player));
                player.addEffect(new MobEffectInstance(MobEffects.DARKNESS, 100, 0));
            }
            level.playSound(null, warden.blockPosition(), SoundEvents.WARDEN_SONIC_BOOM, SoundSource.HOSTILE, 2.0f, 0.6f);
            level.sendParticles(ParticleTypes.SONIC_BOOM, warden.getX(), warden.getY() + 1.5, warden.getZ(), 1, 0, 0, 0, 0);
        }
        if (fraction < 0.33f) {
            if (tick % 200 == 0) {
                summonMites(level, warden, config);
            }
            if (tick % 120 == 60 && farthest.distanceToSqr(warden) > 36) {
                Vec3 to = farthest.position().add(farthest.getLookAngle().scale(-2.0));
                level.sendParticles(ParticleTypes.SCULK_SOUL, warden.getX(), warden.getY() + 1, warden.getZ(), 40, 0.6, 1.0, 0.6, 0.1);
                warden.teleportTo(to.x, farthest.getY(), to.z);
                level.playSound(null, BlockPos.containing(to), SoundEvents.WARDEN_TENDRIL_CLICKS, SoundSource.HOSTILE, 2.0f, 0.5f);
            }
            if (tick % 40 == 0 && warden.getHealth() < warden.getMaxHealth()) {
                warden.heal((float) config.void_warden_regen);
            }
        }
    }

    private static void summonMites(ServerLevel level, Warden warden, BeyondConfig config) {
        for (int i = 0; i < config.void_warden_mites; i++) {
            double a = i * (Math.PI * 2 / Math.max(1, config.void_warden_mites));
            Endermite mite = EntityType.ENDERMITE.create(level, EntitySpawnReason.EVENT);
            if (mite == null) {
                continue;
            }
            mite.snapTo(new Vec3(warden.getX() + Math.cos(a) * 3, warden.getY(), warden.getZ() + Math.sin(a) * 3), 0f, 0f);
            mite.addTag(TAG + "_mite");
            mite.addTag(Mobs.TAG_DRESSED);
            mite.setCustomName(Component.literal("Void Mite").withStyle(ChatFormatting.DARK_AQUA));
            mite.setPersistenceRequired();
            level.addFreshEntity(mite);
        }
        level.playSound(null, warden.blockPosition(), SoundEvents.SCULK_SHRIEKER_SHRIEK, SoundSource.HOSTILE, 1.6f, 0.7f);
    }

    public static void onDeath(ServerLevel level, LivingEntity dead) {
        if (!is(dead)) {
            return;
        }
        Boss.stopTheme(level, dead.blockPosition());
        BossBars.drop(dead);
        dead.spawnAtLocation(level, BeyondItems.create(Specials.VOID_HEART, 1));
        level.playSound(null, dead.blockPosition(), SoundEvents.WARDEN_DEATH, SoundSource.HOSTILE, 2.0f, 0.7f);
        for (Entity mite : level.getEntitiesOfClass(Entity.class, dead.getBoundingBox().inflate(64),
                e -> e.getTags().contains(TAG + "_mite"))) {
            mite.discard();
        }
        BossBars.announce(level.getServer(), Component.literal(NAME).withStyle(ChatFormatting.DARK_AQUA)
                .append(Component.literal(" is still. Its heart lies in the dust.").withStyle(ChatFormatting.GRAY)));
        Beyond.log("void warden killed");
    }
}
