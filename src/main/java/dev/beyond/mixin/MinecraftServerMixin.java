package dev.beyond.mixin;

import dev.beyond.Beyond;
import net.minecraft.server.MinecraftServer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.function.BooleanSupplier;

/** The server tick drives cooldowns, the item sweep and structure placement; the stop saves. */
@Mixin(MinecraftServer.class)
public class MinecraftServerMixin {

    @Inject(method = "tickServer(Ljava/util/function/BooleanSupplier;)V", at = @At("TAIL"))
    private void beyond$tick(BooleanSupplier hasTimeLeft, CallbackInfo ci) {
        Beyond.onServerTick((MinecraftServer) (Object) this);
    }

    @Inject(method = "stopServer()V", at = @At("HEAD"))
    private void beyond$stopping(CallbackInfo ci) {
        Beyond.onServerStopping();
    }
}
