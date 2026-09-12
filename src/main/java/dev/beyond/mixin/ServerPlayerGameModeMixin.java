package dev.beyond.mixin;

import dev.beyond.Beyond;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.ServerPlayerGameMode;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.BlockHitResult;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Right-clicks. A block click may be the forge or a portal pedestal; an item click may be an
 * ability. Either way the mod answers first, and vanilla only runs if it declined.
 */
@Mixin(ServerPlayerGameMode.class)
public class ServerPlayerGameModeMixin {

    @Inject(method = "useItemOn(Lnet/minecraft/server/level/ServerPlayer;Lnet/minecraft/world/level/Level;"
            + "Lnet/minecraft/world/item/ItemStack;Lnet/minecraft/world/InteractionHand;"
            + "Lnet/minecraft/world/phys/BlockHitResult;)Lnet/minecraft/world/InteractionResult;",
            at = @At("HEAD"), cancellable = true)
    private void beyond$useItemOn(ServerPlayer player, Level level, ItemStack stack, InteractionHand hand,
                                  BlockHitResult hit, CallbackInfoReturnable<InteractionResult> cir) {
        if (level instanceof ServerLevel serverLevel
                && Beyond.onUseBlock(player, serverLevel, stack, hand, hit)) {
            cir.setReturnValue(InteractionResult.SUCCESS_SERVER);
        }
    }

    @Inject(method = "useItem(Lnet/minecraft/server/level/ServerPlayer;Lnet/minecraft/world/level/Level;"
            + "Lnet/minecraft/world/item/ItemStack;Lnet/minecraft/world/InteractionHand;)"
            + "Lnet/minecraft/world/InteractionResult;",
            at = @At("HEAD"), cancellable = true)
    private void beyond$useItem(ServerPlayer player, Level level, ItemStack stack, InteractionHand hand,
                                CallbackInfoReturnable<InteractionResult> cir) {
        if (level instanceof ServerLevel serverLevel
                && Beyond.onUseItem(player, serverLevel, stack, hand)) {
            cir.setReturnValue(InteractionResult.SUCCESS_SERVER);
        }
    }

    @org.spongepowered.asm.mixin.Shadow
    protected net.minecraft.server.level.ServerLevel level;
    @org.spongepowered.asm.mixin.Shadow
    @org.spongepowered.asm.mixin.Final
    protected ServerPlayer player;

    /** A survival player cannot break a boss hall; the client is resynced by vanilla on a false. */
    @Inject(method = "destroyBlock(Lnet/minecraft/core/BlockPos;)Z", at = @At("HEAD"), cancellable = true)
    private void beyond$keepHalls(net.minecraft.core.BlockPos pos, CallbackInfoReturnable<Boolean> cir) {
        if (!dev.beyond.Halls.allowBreak(this.level, this.player, pos)) {
            cir.setReturnValue(false);
        }
    }
}
