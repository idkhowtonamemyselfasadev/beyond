package dev.beyond.mob;

import dev.beyond.Beyond;
import dev.beyond.BeyondConfig;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.animal.bee.Bee;
import net.minecraft.world.entity.monster.Slime;
import net.minecraft.world.entity.monster.skeleton.WitherSkeleton;
import net.minecraft.world.item.ItemStack;

import java.util.Optional;

/**
 * The End's creatures, built on vanilla mobs.
 *
 * <p>A new entity type cannot be shown to a vanilla client, so each creature is a vanilla mob
 * that spawns in one of the new biomes and is dressed the moment it appears: a name, tuned
 * attributes, stripped equipment, and a tag the rest of the mod recognises. Their drops are
 * loot table overrides that only apply inside the End.
 */
public final class Mobs {

    public static final String TAG_SHADOW_WALKER = "beyond_shadow_walker";
    public static final String TAG_DRESSED = "beyond_dressed";

    private Mobs() {
    }

    private static Optional<String> biomeOf(ServerLevel level, Entity entity) {
        return level.getBiome(entity.blockPosition()).unwrapKey().map(k -> k.identifier().toString());
    }

    public static void dress(ServerLevel level, Entity entity, BeyondConfig config) {
        if (!(entity instanceof Mob mob) || mob.getTags().contains(TAG_DRESSED)) {
            return;
        }
        Optional<String> biome = biomeOf(level, entity);
        if (biome.isEmpty() || !biome.get().startsWith(Beyond.MODID + ":")) {
            return;
        }
        String name;
        if (mob instanceof WitherSkeleton && biome.get().endsWith("shadow_forest")) {
            name = "Shadow Walker";
            mob.addTag(TAG_SHADOW_WALKER);
            // Nothing in its hands: it hurts you by being near you, not with a sword.
            mob.setItemSlot(EquipmentSlot.MAINHAND, ItemStack.EMPTY);
            attribute(mob, Attributes.MAX_HEALTH, config.shadow_walker_health);
            attribute(mob, Attributes.MOVEMENT_SPEED, config.shadow_walker_speed);
            attribute(mob, Attributes.ATTACK_DAMAGE, config.shadow_walker_damage);
            mob.setHealth((float) config.shadow_walker_health);
            mob.setCustomNameVisible(false);
        } else if (mob instanceof Slime) {
            name = "End Slime";
        } else if (mob instanceof net.minecraft.world.entity.animal.squid.GlowSquid) {
            name = "Cubozoa";
        } else if (mob instanceof net.minecraft.world.entity.animal.fish.Cod) {
            name = "End Fish";
        } else if (mob instanceof Bee) {
            name = "Silk Moth";
        } else if (mob instanceof net.minecraft.world.entity.ambient.Bat) {
            name = "Dragonfly";
        } else {
            return;
        }
        mob.setCustomName(Component.literal(name).withStyle(ChatFormatting.LIGHT_PURPLE));
        mob.addTag(TAG_DRESSED);
        Beyond.log("dressed {} as {} in {}", mob.getType().toShortString(), name, biome.get());
    }

    private static void attribute(Mob mob, net.minecraft.core.Holder<net.minecraft.world.entity.ai.attributes.Attribute> which, double value) {
        AttributeInstance instance = mob.getAttribute(which);
        if (instance != null) {
            instance.setBaseValue(value);
        }
    }

    /** The Shadow Walker's touch: a player it hits loses their sight for a moment. */
    public static void onHurt(LivingEntity victim, DamageSource source, BeyondConfig config) {
        if (!(victim instanceof ServerPlayer player)) {
            return;
        }
        if (!(source.getEntity() instanceof LivingEntity attacker) || !attacker.getTags().contains(TAG_SHADOW_WALKER)) {
            return;
        }
        player.addEffect(new MobEffectInstance(MobEffects.BLINDNESS, config.shadow_walker_blindness_ticks, 0));
        player.addEffect(new MobEffectInstance(MobEffects.SLOWNESS, config.shadow_walker_blindness_ticks, 0));
        Beyond.log("shadow walker blinded {}", player.getName().getString());
    }
}
