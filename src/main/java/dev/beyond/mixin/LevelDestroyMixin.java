package dev.beyond.mixin;

import dev.beyond.Halls;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Mobs that break blocks (a wither above all) cannot break a boss hall. */
@Mixin(Level.class)
public abstract class LevelDestroyMixin {

    @Inject(method = "destroyBlock(Lnet/minecraft/core/BlockPos;ZLnet/minecraft/world/entity/Entity;I)Z",
            at = @At("HEAD"), cancellable = true)
    private void beyond$keepHalls(BlockPos pos, boolean drop, Entity breaker, int depth,
                                 CallbackInfoReturnable<Boolean> cir) {
        if ((Object) this instanceof ServerLevel level && Halls.protects(level, pos)) {
            cir.setReturnValue(false);
        }
    }
}
