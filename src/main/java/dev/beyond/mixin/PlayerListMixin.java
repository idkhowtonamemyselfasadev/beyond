package dev.beyond.mixin;

import dev.beyond.Beyond;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.players.PlayerList;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Drops a player's session state when they leave. */
@Mixin(PlayerList.class)
public class PlayerListMixin {

    @Inject(method = "placeNewPlayer", at = @At("TAIL"))
    private void beyond$join(net.minecraft.network.Connection connection, ServerPlayer player,
                             net.minecraft.server.network.CommonListenerCookie cookie, CallbackInfo ci) {
        Beyond.onPlayerJoin(player);
    }

    @Inject(method = "remove(Lnet/minecraft/server/level/ServerPlayer;)V", at = @At("HEAD"))
    private void beyond$disconnect(ServerPlayer player, CallbackInfo ci) {
        Beyond.onPlayerDisconnect(player);
    }
}
