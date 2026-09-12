package dev.beyond.item;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;

/**
 * The Aeternium Pickaxe mines 3×3.
 *
 * <p>Called from {@code ServerPlayerGameModeMixin} after a block was really broken (no Fabric
 * API here: the mod runs without it). The eight blocks around it in the plane the player is
 * facing go too: looking at a wall gives a 3×3 wall, looking down gives a 3×3 floor. Each
 * extra block is broken through the normal path ({@code ServerPlayerGameMode.destroyBlock}),
 * so drops, silk touch and fortune, tool damage and protection mods all apply exactly as if
 * the player had mined it by hand. Only blocks the pickaxe is the right tool for, and that
 * are no harder than the one actually hit, come along — so hitting stone next to obsidian
 * does not also eat the obsidian, and bedrock never moves.
 *
 * <p>Sneaking mines a single block, for precision.
 */
public final class AreaMining {

    /** The extra breaks re-enter the break event; this keeps them from fanning out again. */
    private static final ThreadLocal<Boolean> BUSY = ThreadLocal.withInitial(() -> false);

    private AreaMining() {
    }

    public static void afterBreak(Level level, ServerPlayer sp, BlockPos pos, BlockState state) {
        if (BUSY.get() || sp.isShiftKeyDown() || sp.isCreative()) {
            return;
        }
        ItemStack tool = sp.getMainHandItem();
        if (!(BeyondItems.of(tool) instanceof GearItem gear)
                || gear.tier != GearItem.Tier.AETERNIUM || gear.kind != GearItem.Kind.PICKAXE) {
            return;
        }
        Direction face = facing(sp, pos);
        float limit = state.getDestroySpeed(level, pos);
        BUSY.set(true);
        try {
            for (int a = -1; a <= 1; a++) {
                for (int b = -1; b <= 1; b++) {
                    if (a == 0 && b == 0) {
                        continue;
                    }
                    BlockPos p = offset(pos, face, a, b);
                    BlockState s = level.getBlockState(p);
                    if (s.isAir() || s.getBlock().asItem() == null) {
                        continue;
                    }
                    float hardness = s.getDestroySpeed(level, p);
                    if (hardness < 0 || hardness > Math.max(limit, 0.0f) + 0.001f && limit >= 0) {
                        continue;   // bedrock, or something harder than what was hit
                    }
                    if (!sp.hasCorrectToolForDrops(s) || level.getBlockEntity(p) != null) {
                        continue;   // wrong tool for it, or a container: leave those alone
                    }
                    if (tool.isEmpty() || tool.isBroken()) {
                        return;     // the pickaxe just broke; stop here
                    }
                    sp.gameMode.destroyBlock(p);
                }
            }
        } finally {
            BUSY.set(false);
        }
    }

    /** The face the player hit, from a fresh ray cast; falls back to the look direction. */
    private static Direction facing(ServerPlayer p, BlockPos broken) {
        HitResult hit = p.pick(p.blockInteractionRange() + 1, 0f, false);
        if (hit instanceof BlockHitResult bhr && bhr.getType() == HitResult.Type.BLOCK && bhr.getBlockPos().equals(broken)) {
            return bhr.getDirection();
        }
        return Direction.getApproximateNearest(p.getViewVector(1f)).getOpposite();
    }

    private static BlockPos offset(BlockPos pos, Direction face, int a, int b) {
        return switch (face.getAxis()) {
            case Y -> pos.offset(a, 0, b);
            case X -> pos.offset(0, a, b);
            case Z -> pos.offset(a, b, 0);
        };
    }
}
