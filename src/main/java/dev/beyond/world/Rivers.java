package dev.beyond.world;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.Heightmap;

import java.util.ArrayList;
import java.util.List;

/**
 * Rivers across the islands, ending in a fall off the edge into the void.
 *
 * <p>Carved rather than generated: a path is walked over the surface with a heading that
 * wanders, the channel is cut two deep and filled with source water, the banks are dressed
 * in the island's own stone, and where the ground drops away the water is left to pour
 * over the edge. A bridge of end stone bricks crosses at the halfway point, and sea lanterns
 * on the bed light it from below.
 */
public final class Rivers {

    public static final String TYPE = "river";

    private Rivers() {
    }

    /** @return the number of blocks of river carved, 0 if the spot was no good */
    public static int build(ServerLevel level, BlockPos start, RandomSource random) {
        double heading = random.nextDouble() * Math.PI * 2;
        double x = start.getX() + 0.5, z = start.getZ() + 0.5;
        int length = 70 + random.nextInt(80);
        int width = 1 + random.nextInt(2);           // half-width: 3 or 5 blocks across
        int lastSurface = Terrain.ground(level, start.getX(), start.getZ());
        if (lastSurface < 40) {
            return 0;
        }
        // The path is measured first and carved afterwards: carving changes the ground it
        // would otherwise be reading as it goes, and a channel read as terrain looks like
        // a cliff at its own edge.
        List<BlockPos> bed = new ArrayList<>();
        List<Double> headings = new ArrayList<>();
        boolean fell = false;
        for (int step = 0; step < length; step++) {
            heading = steer(level, x, z, heading, random);
            x += Math.cos(heading);
            z += Math.sin(heading);
            int bx = (int) Math.floor(x), bz = (int) Math.floor(z);
            int surface = Terrain.ground(level, bx, bz);
            if (surface < 40 || surface < lastSurface - 5) {
                fell = true;     // the island ends here: the water will pour over the edge
                break;
            }
            if (surface > lastSurface + 2) {
                break;           // uphill everywhere: the river ends in a pool rather than climbing
            }
            lastSurface = Math.min(surface, lastSurface);   // rivers do not climb
            bed.add(new BlockPos(bx, lastSurface - 2, bz));
            headings.add(heading);
        }
        if (bed.size() < 24) {
            return 0;
        }
        for (int i = 0; i < bed.size(); i++) {
            BlockPos p = bed.get(i);
            carve(level, p.getX(), p.getY(), p.getZ(), width, random);
            if (i == bed.size() / 2) {
                bridge(level, p.getX(), p.getY(), p.getZ(), headings.get(i), width);
            }
        }
        if (fell) {
            fall(level, bed, width);
        }
        return bed.size();
    }

    /** Water goes downhill: of a slight left, straight on and a slight right, the lowest wins. */
    private static double steer(ServerLevel level, double x, double z, double heading, RandomSource random) {
        double best = heading, bestHeight = Double.MAX_VALUE;
        for (double turn : new double[] {-0.45, 0, 0.45}) {
            double h = heading + turn + (random.nextDouble() - 0.5) * 0.2;
            int px = (int) Math.floor(x + Math.cos(h) * 4), pz = (int) Math.floor(z + Math.sin(h) * 4);
            level.getChunk(px >> 4, pz >> 4);   // the look-ahead reaches past the loaded area
            double s = Terrain.ground(level, px, pz) + random.nextDouble() * 1.5;
            if (s < bestHeight) {
                bestHeight = s;
                best = h;
            }
        }
        return best;
    }

    private static void carve(ServerLevel level, int cx, int bedY, int cz, int width, RandomSource random) {
        for (int dx = -width - 1; dx <= width + 1; dx++) {
            for (int dz = -width - 1; dz <= width + 1; dz++) {
                double d = Math.hypot(dx, dz);
                BlockPos column = new BlockPos(cx + dx, bedY, cz + dz);
                if (d <= width + 0.5) {
                    // the channel: bed, two of water, open air above
                    Block floor = random.nextInt(9) == 0 ? Blocks.SEA_LANTERN : bedBlock(level, column);
                    set(level, column.below(), floor);
                    set(level, column, Blocks.WATER);
                    set(level, column.above(), Blocks.WATER);
                    for (int dy = 2; dy <= 5; dy++) {
                        BlockState above = level.getBlockState(column.above(dy));
                        if (!above.isAir()) {
                            set(level, column.above(dy), Blocks.AIR);
                        }
                    }
                } else if (d <= width + 1.5) {
                    // the bank: cut down to one step above the water, and open to the sky
                    BlockPos bank = new BlockPos(column.getX(), bedY + 2, column.getZ());
                    for (int dy = bank.getY() + 1; dy <= bank.getY() + 6; dy++) {
                        set(level, new BlockPos(column.getX(), dy, column.getZ()), Blocks.AIR);
                    }
                    BlockState here = level.getBlockState(bank);
                    if (here.isAir() || !here.getFluidState().isEmpty()) {
                        set(level, bank, Blocks.END_STONE_BRICKS);
                    } else if (random.nextInt(5) == 0) {
                        set(level, bank, random.nextBoolean() ? Blocks.MOSSY_STONE_BRICKS : Blocks.END_STONE_BRICKS);
                    }
                    if (random.nextInt(9) == 0) {
                        set(level, bank.above(), Blocks.END_ROD);
                    }
                }
            }
        }
    }

    /** The bed takes the colour of whatever the island is made of, mostly. */
    private static Block bedBlock(ServerLevel level, BlockPos at) {
        BlockState below = level.getBlockState(at.below(2));
        if (below.is(Blocks.MOSS_BLOCK) || below.is(Blocks.MYCELIUM)) {
            return Blocks.PRISMARINE;
        }
        if (below.is(Blocks.PACKED_ICE) || below.is(Blocks.BLUE_ICE) || below.is(Blocks.SNOW_BLOCK)) {
            return Blocks.PACKED_ICE;
        }
        return Blocks.DARK_PRISMARINE;
    }

    /** Where the ground gives out, the channel is left open so the water pours over the edge. */
    private static void fall(ServerLevel level, List<BlockPos> bed, int width) {
        if (bed.size() < 3) {
            return;
        }
        BlockPos lip = bed.get(bed.size() - 1);
        for (int dx = -width; dx <= width; dx++) {
            for (int dz = -width; dz <= width; dz++) {
                if (Math.hypot(dx, dz) <= width + 0.5) {
                    // clear the rim beyond the lip so nothing dams the fall
                    for (int r = 1; r <= 3; r++) {
                        BlockPos beyond = lip.offset(dx * r, 0, dz * r);
                        for (int dy = -1; dy <= 3; dy++) {
                            BlockPos p = beyond.above(dy);
                            if (!level.getBlockState(p).isAir() && level.getBlockState(p).getFluidState().isEmpty()) {
                                int surface = Terrain.ground(level, p.getX(), p.getZ());
                                if (surface < 40) {
                                    set(level, p, Blocks.AIR);
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    /** An arched footbridge across the middle, with rails, wide enough to walk two abreast. */
    private static void bridge(ServerLevel level, int cx, int bedY, int cz, double heading, int width) {
        double px = -Math.sin(heading), pz = Math.cos(heading);   // across the river
        int span = width + 2;
        int deckY = bedY + 3;
        for (int i = -span - 1; i <= span + 1; i++) {
            int rise = Math.abs(i) <= 1 ? 1 : 0;
            for (int w = -1; w <= 1; w++) {
                int bx = (int) Math.round(cx + px * i + Math.cos(heading) * w);
                int bz = (int) Math.round(cz + pz * i + Math.sin(heading) * w);
                set(level, new BlockPos(bx, deckY + rise, bz), Blocks.END_STONE_BRICKS);
                for (int dy = 1; dy <= 3; dy++) {
                    set(level, new BlockPos(bx, deckY + rise + dy, bz), Blocks.AIR);
                }
                if (Math.abs(w) == 1) {
                    set(level, new BlockPos(bx, deckY + rise + 1, bz), Blocks.END_STONE_BRICK_WALL);
                }
            }
            if (Math.abs(i) == span + 1) {
                int bx = (int) Math.round(cx + px * i), bz = (int) Math.round(cz + pz * i);
                set(level, new BlockPos(bx, deckY + 2, bz), Blocks.END_ROD);
            }
        }
    }

    private static void set(ServerLevel level, BlockPos pos, Block block) {
        if (pos.getY() > level.getMinY() && pos.getY() < level.getMaxY()) {
            level.setBlock(pos, block.defaultBlockState(), Block.UPDATE_CLIENTS);
        }
    }
}
