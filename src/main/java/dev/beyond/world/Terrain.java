package dev.beyond.world;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.level.block.BushBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.Heightmap;

/** Where the ground really is: the heightmaps count trees, and the End has tall ones. */
public final class Terrain {

    private Terrain() {
    }

    /** The y of the first block that is solid ground, looking down from the surface. */
    public static int ground(ServerLevel level, int x, int z) {
        int y = level.getHeight(Heightmap.Types.WORLD_SURFACE_WG, x, z);
        for (int i = 0; i < 24 && y > level.getMinY(); i++) {
            BlockState state = level.getBlockState(new BlockPos(x, y - 1, z));
            if (state.isAir() || state.is(BlockTags.LEAVES) || state.is(BlockTags.LOGS)
                    || state.is(BlockTags.SAPLINGS) || state.is(BlockTags.FLOWERS)
                    || state.getBlock() instanceof BushBlock || state.canBeReplaced()
                    || !state.getFluidState().isEmpty() && false) {
                y--;
            } else {
                return y;
            }
        }
        return y;
    }
}
