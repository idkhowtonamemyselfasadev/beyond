package dev.beyond;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.LivingEntity;

/** Ability damage that ignores invulnerability frames, and is recognisable as ability damage. */
public final class Hurt {

    private static boolean inAbilityDamage;

    private Hurt() {
    }

    /** True while an ability's own damage is being applied; the hit hooks stay out of the way. */
    public static boolean isAbilityDamage() {
        return inAbilityDamage;
    }

    public static boolean deal(LivingEntity victim, DamageSource source, float amount) {
        if (!(victim.level() instanceof ServerLevel level) || !victim.isAlive()) {
            return false;
        }
        int saved = victim.invulnerableTime;
        victim.invulnerableTime = 0;
        inAbilityDamage = true;
        try {
            return victim.hurtServer(level, source, amount);
        } finally {
            inAbilityDamage = false;
            victim.invulnerableTime = saved;
        }
    }
}
