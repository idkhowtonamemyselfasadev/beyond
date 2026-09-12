package dev.beyond.mixin;

import dev.beyond.Beyond;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Every freshly spawned entity passes through here - natural spawns, eggs, commands - which
 * is where a vanilla mob in one of the new biomes gets dressed as one of ours.
 */
@Mixin(ServerLevel.class)
public class ServerLevelMixin {

    @Inject(method = "addFreshEntity(Lnet/minecraft/world/entity/Entity;)Z", at = @At("RETURN"))
    private void beyond$entityAdded(Entity entity, CallbackInfoReturnable<Boolean> cir) {
        if (cir.getReturnValue()) {
            Beyond.onEntityAdded((ServerLevel) (Object) this, entity);
        }
    }
}
