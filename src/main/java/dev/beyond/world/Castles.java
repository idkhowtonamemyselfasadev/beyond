package dev.beyond.world;

import dev.beyond.Beyond;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Vec3i;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructurePlaceSettings;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;

import java.util.List;
import java.util.Optional;

/**
 * The three castles, placed by the mod on islands it has measured.
 *
 * <p>They are ordinary structure templates (gen/castles.py), but not jigsaw structures: a
 * jigsaw start that lands over the void is dropped without a word, and the End is mostly
 * void. So the region grid in {@link Sites} nominates a spot, this checks that there is an
 * island under the whole footprint, and only then stamps the template down, sunk six rows
 * so the foundation is buried and the courtyard sits on the surface.
 */
public final class Castles {

    public static final String OBSIDIAN_FORTRESS = "obsidian_fortress";
    public static final String PURPUR_CITADEL = "purpur_citadel";
    public static final String TIDE_BASTION = "tide_bastion";
    public static final List<String> TYPES = List.of(OBSIDIAN_FORTRESS, PURPUR_CITADEL, TIDE_BASTION);

    private static final int VARIANTS = 3;
    /** Rows of foundation under the courtyard, the same G as the generator. */
    private static final int SINK = 6;
    /** An island counts if its surface is at least this high everywhere the walls stand. */
    private static final int MIN_SURFACE = 44;

    private Castles() {
    }

    public static boolean isCastle(String type) {
        return TYPES.contains(type);
    }

    /**
     * Tries to build the castle centred on (x, z).
     *
     * @return the placed position, or null if there is no island big enough here
     */
    public static BlockPos place(ServerLevel level, String type, int x, int z, RandomSource random) {
        return place(level, type, x, z, random, false);
    }

    /**
     * @param force build whatever the ground is like: the castle stands on a plinth of end
     *              stone raised under its whole footprint, a fortress floating in the void
     */
    public static BlockPos place(ServerLevel level, String type, int x, int z, RandomSource random, boolean force) {
        int variant = random.nextInt(VARIANTS);
        Optional<StructureTemplate> loaded = level.getStructureManager()
                .get(Identifier.parse(Beyond.MODID + ":" + type + "/" + variant));
        if (loaded.isEmpty()) {
            Beyond.LOGGER.warn("Castle template {}/{} is missing", type, variant);
            return null;
        }
        StructureTemplate template = loaded.get();
        Vec3i size = template.getSize();
        int half = Math.max(size.getX(), size.getZ()) / 2;

        // Every chunk the walls touch has to exist before the ground can be measured.
        for (int cx = (x - half) >> 4; cx <= (x + half) >> 4; cx++) {
            for (int cz = (z - half) >> 4; cz <= (z + half) >> 4; cz++) {
                level.getChunk(cx, cz);
            }
        }
        int centre = surface(level, x, z);
        if (centre < MIN_SURFACE && !force) {
            return null;
        }
        int lowest = Math.max(centre, 56);
        int reach = half - 6;
        for (int[] d : new int[][] {{reach, 0}, {-reach, 0}, {0, reach}, {0, -reach},
                {reach * 2 / 3, reach * 2 / 3}, {-reach * 2 / 3, reach * 2 / 3},
                {reach * 2 / 3, -reach * 2 / 3}, {-reach * 2 / 3, -reach * 2 / 3}}) {
            int s = surface(level, x + d[0], z + d[1]);
            if (!force && (s < MIN_SURFACE || Math.abs(s - centre) > 16)) {
                return null;   // the walls would hang off the edge or climb a cliff
            }
            if (s >= MIN_SURFACE) {
                lowest = Math.min(lowest, s);
            }
        }
        if (force) {
            plinth(level, x, z, size, lowest - SINK);
        }

        Rotation rotation = Rotation.getRandom(random);
        BlockPos corner = new BlockPos(x - size.getX() / 2, lowest - SINK, z - size.getZ() / 2);
        StructurePlaceSettings settings = new StructurePlaceSettings()
                .setRotation(rotation)
                .setMirror(Mirror.NONE)
                .setRotationPivot(new BlockPos(size.getX() / 2, 0, size.getZ() / 2))
                .setIgnoreEntities(false)
                .setKnownShape(true);
        template.placeInWorld(level, corner, corner, settings, random, Block.UPDATE_CLIENTS);
        BlockPos placed = new BlockPos(x, lowest, z);
        Garrison.man(level, type, placed, Math.max(size.getX(), size.getZ()), random, Beyond.config());
        return placed;
    }

    /** Solid end stone under the footprint, down to whatever is there or 28 rows, whichever first. */
    private static void plinth(ServerLevel level, int x, int z, Vec3i size, int top) {
        int rx = size.getX() / 2 + 2, rz = size.getZ() / 2 + 2;
        for (int dx = -rx; dx <= rx; dx++) {
            for (int dz = -rz; dz <= rz; dz++) {
                // rounded corners, so it reads as a rock the castle was cut into
                if (Math.abs(dx) > rx - 6 && Math.abs(dz) > rz - 6 && Math.hypot(Math.abs(dx) - (rx - 6), Math.abs(dz) - (rz - 6)) > 6) {
                    continue;
                }
                for (int dy = 0; dy < 28; dy++) {
                    BlockPos p = new BlockPos(x + dx, top - dy, z + dz);
                    if (!level.getBlockState(p).isAir()) {
                        if (dy > 2) {
                            break;
                        }
                        continue;
                    }
                    level.setBlock(p, net.minecraft.world.level.block.Blocks.END_STONE.defaultBlockState(), Block.UPDATE_CLIENTS);
                }
            }
        }
    }

    private static int surface(ServerLevel level, int x, int z) {
        return Terrain.ground(level, x, z);
    }
}
