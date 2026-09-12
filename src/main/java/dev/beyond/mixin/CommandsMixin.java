package dev.beyond.mixin;

import dev.beyond.Beyond;
import net.minecraft.commands.Commands;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Registers {@code /beyond} when the command tree is built. */
@Mixin(Commands.class)
public class CommandsMixin {

    @Inject(method = "<init>", at = @At("RETURN"))
    private void beyond$register(CallbackInfo ci) {
        Beyond.onCommandsBuilt(((Commands) (Object) this).getDispatcher());
    }
}
