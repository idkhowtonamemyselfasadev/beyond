package dev.beyond.mixin;

import dev.beyond.Halls;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.ServerExplosion;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.List;

/** No explosion - TNT, creeper, wither skull, crystal, bed - takes a block out of a boss hall. */
@Mixin(ServerExplosion.class)
public abstract class ServerExplosionMixin {

    @Inject(method = "interactWithBlocks", at = @At("HEAD"))
    private void beyond$keepHalls(List<BlockPos> positions, CallbackInfo ci) {
        ServerExplosion self = (ServerExplosion) (Object) this;
        positions.removeIf(pos -> Halls.protects(self.level(), pos));
    }
}
