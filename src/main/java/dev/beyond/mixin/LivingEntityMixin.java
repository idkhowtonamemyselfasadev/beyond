package dev.beyond.mixin;

import dev.beyond.Beyond;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.LivingEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** A hit that actually landed, and the death it may have caused. */
@Mixin(LivingEntity.class)
public class LivingEntityMixin {

    @Inject(method = "hurtServer(Lnet/minecraft/server/level/ServerLevel;"
            + "Lnet/minecraft/world/damagesource/DamageSource;F)Z", at = @At("RETURN"))
    private void beyond$hurt(ServerLevel level, DamageSource source, float amount,
                             CallbackInfoReturnable<Boolean> cir) {
        if (cir.getReturnValue()) {
            Beyond.onLivingHurt((LivingEntity) (Object) this, source, amount);
        }
    }

    @Inject(method = "die(Lnet/minecraft/world/damagesource/DamageSource;)V",
            at = @At("HEAD"))
    private void beyond$died(DamageSource cause, CallbackInfo ci) {
        Beyond.onLivingDeath((LivingEntity) (Object) this);
    }
}
