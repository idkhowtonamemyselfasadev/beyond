package dev.beyond.world;

import dev.beyond.Beyond;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.RandomizableContainerBlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.loot.LootTable;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * The seven structures, built block by block from vanilla blocks.
 *
 * <p>Each builder clears its footprint, puts a foundation under itself so it never hangs off
 * a cliff, and ends with a chest whose loot table holds an item found nowhere else. The
 * Eternal Portal returns its six pedestal positions; everything else returns nothing.
 */
public final class Structures {

    public static final String VIOLECITE_RUIN = "violecite_ruin";
    public static final String CRYSTAL_SHRINE = "crystal_shrine";
    public static final String AMBER_VAULT = "amber_vault";
    public static final String SHADOW_NEST = "shadow_nest";
    public static final String SUNKEN_OBSERVATORY = "sunken_observatory";
    public static final String STARFALL_CAIRN = "starfall_cairn";
    public static final String ETERNAL_PORTAL = "eternal_portal";

    public static final List<String> TYPES = List.of(VIOLECITE_RUIN, CRYSTAL_SHRINE, AMBER_VAULT,
            SHADOW_NEST, SUNKEN_OBSERVATORY, STARFALL_CAIRN, ETERNAL_PORTAL);

    /** Which structure a biome hosts. Biomes not listed host only the portal. */
    private static final Map<String, List<String>> BY_BIOME = Map.of(
            "beyond:chorus_forest", List.of(VIOLECITE_RUIN),
            "beyond:dust_wastelands", List.of(VIOLECITE_RUIN),
            "beyond:crystal_mountains", List.of(CRYSTAL_SHRINE),
            "beyond:amber_land", List.of(AMBER_VAULT),
            "beyond:shadow_forest", List.of(SHADOW_NEST),
            "beyond:megalake", List.of(SUNKEN_OBSERVATORY),
            "beyond:foggy_mushroomland", List.of(SUNKEN_OBSERVATORY),
            "beyond:ice_starfield", List.of(STARFALL_CAIRN));

    private Structures() {
    }

    public static String typeFor(String biome, RandomSource random) {
        List<String> options = BY_BIOME.get(biome);
        if (options == null || options.isEmpty()) {
            return null;
        }
        return options.get(random.nextInt(options.size()));
    }

    /** The cairn stands on a shard of ice it makes for itself, out in the void. */
    public static boolean floats(String type) {
        return STARFALL_CAIRN.equals(type);
    }

    public static List<BlockPos> build(ServerLevel level, String type, BlockPos floor, RandomSource random) {
        switch (type) {
            case VIOLECITE_RUIN -> ruin(level, floor, random);
            case CRYSTAL_SHRINE -> shrine(level, floor, random);
            case AMBER_VAULT -> vault(level, floor, random);
            case SHADOW_NEST -> nest(level, floor, random);
            case SUNKEN_OBSERVATORY -> observatory(level, floor, random);
            case STARFALL_CAIRN -> cairn(level, floor, random);
            case ETERNAL_PORTAL -> {
                return portal(level, floor);
            }
            default -> Beyond.LOGGER.warn("Unknown structure type {}", type);
        }
        return List.of();
    }

    // ---------------------------------------------------------------------- helpers

    private static void set(ServerLevel level, BlockPos pos, Block block) {
        set(level, pos, block.defaultBlockState());
    }

    private static void set(ServerLevel level, BlockPos pos, BlockState state) {
        if (pos.getY() > level.getMinY() && pos.getY() < level.getMaxY()) {
            level.setBlock(pos, state, Block.UPDATE_CLIENTS);
        }
    }

    private static void clear(ServerLevel level, BlockPos floor, int radius, int height) {
        for (int dx = -radius; dx <= radius; dx++) {
            for (int dz = -radius; dz <= radius; dz++) {
                for (int dy = 1; dy <= height; dy++) {
                    set(level, floor.offset(dx, dy, dz), Blocks.AIR);
                }
            }
        }
    }

    /** A floor, and a foundation under it down to whatever is solid. */
    private static void platform(ServerLevel level, BlockPos floor, int radius, Block top, Block fill) {
        for (int dx = -radius; dx <= radius; dx++) {
            for (int dz = -radius; dz <= radius; dz++) {
                set(level, floor.offset(dx, 0, dz), top);
                for (int dy = -1; dy >= -8; dy--) {
                    BlockPos p = floor.offset(dx, dy, dz);
                    BlockState existing = level.getBlockState(p);
                    if (existing.isAir() || !existing.getFluidState().isEmpty() || dy == -1) {
                        set(level, p, fill);
                    } else {
                        break;
                    }
                }
            }
        }
    }

    private static void box(ServerLevel level, BlockPos floor, int radius, int y0, int y1, Block block) {
        for (int dx = -radius; dx <= radius; dx++) {
            for (int dz = -radius; dz <= radius; dz++) {
                if (Math.abs(dx) != radius && Math.abs(dz) != radius) {
                    continue;
                }
                for (int dy = y0; dy <= y1; dy++) {
                    set(level, floor.offset(dx, dy, dz), block);
                }
            }
        }
    }

    private static void pillar(ServerLevel level, BlockPos base, int height, Block block, Block cap) {
        for (int dy = 1; dy <= height; dy++) {
            set(level, base.above(dy), block);
        }
        if (cap != null) {
            set(level, base.above(height + 1), cap);
        }
    }

    private static void chest(ServerLevel level, BlockPos pos, String table, RandomSource random) {
        set(level, pos, Blocks.CHEST);
        if (level.getBlockEntity(pos) instanceof RandomizableContainerBlockEntity container) {
            container.setLootTable(ResourceKey.create(Registries.LOOT_TABLE,
                    Identifier.parse(Beyond.MODID + ":chests/" + table)));
            container.setLootTableSeed(random.nextLong());
        }
    }

    private static void doorways(ServerLevel level, BlockPos floor, int radius, int height) {
        for (Direction d : Direction.Plane.HORIZONTAL) {
            for (int dy = 1; dy <= height; dy++) {
                set(level, floor.relative(d, radius).above(dy), Blocks.AIR);
            }
        }
    }

    // ------------------------------------------------------------- Violecite Ruin

    /** A collapsed purpur hall in the Chorus Forest: half the walls are gone, the vault is not. */
    private static void ruin(ServerLevel level, BlockPos floor, RandomSource random) {
        clear(level, floor, 6, 8);
        platform(level, floor, 6, Blocks.PURPUR_BLOCK, Blocks.END_STONE_BRICKS);
        for (int dx = -6; dx <= 6; dx++) {
            for (int dz = -6; dz <= 6; dz++) {
                boolean wall = Math.abs(dx) == 6 || Math.abs(dz) == 6;
                if (!wall) {
                    continue;
                }
                // Ruined: each wall column stands to a random height, some not at all.
                int h = random.nextInt(6);
                for (int dy = 1; dy <= h; dy++) {
                    set(level, floor.offset(dx, dy, dz), random.nextInt(5) == 0 ? Blocks.END_STONE_BRICKS : Blocks.PURPUR_BLOCK);
                }
            }
        }
        for (int dx = -4; dx <= 4; dx += 8) {
            for (int dz = -4; dz <= 4; dz += 8) {
                pillar(level, floor.offset(dx, 0, dz), 3 + random.nextInt(4), Blocks.PURPUR_PILLAR, Blocks.END_ROD);
            }
        }
        // The vault: a sunken 3x3 room under the floor with the chest, reached by breaking in.
        for (int dx = -1; dx <= 1; dx++) {
            for (int dz = -1; dz <= 1; dz++) {
                for (int dy = -1; dy >= -3; dy--) {
                    set(level, floor.offset(dx, dy, dz), dy == -3 ? Blocks.OBSIDIAN : Blocks.AIR);
                }
            }
        }
        set(level, floor, Blocks.PURPUR_PILLAR);   // the lid
        chest(level, floor.below(2), VIOLECITE_RUIN, random);
        set(level, floor.offset(0, -1, 0).north(2).below(1), Blocks.SHROOMLIGHT);
    }

    // -------------------------------------------------------------- Crystal Shrine

    /** A calcite ring around one great amethyst spire, the chest set into its base. */
    private static void shrine(ServerLevel level, BlockPos floor, RandomSource random) {
        clear(level, floor, 5, 14);
        platform(level, floor, 5, Blocks.CALCITE, Blocks.SMOOTH_BASALT);
        box(level, floor, 5, 1, 1, Blocks.SMOOTH_BASALT);
        for (Direction d : Direction.Plane.HORIZONTAL) {
            pillar(level, floor.relative(d, 4), 4, Blocks.CALCITE, Blocks.AMETHYST_CLUSTER);
        }
        // The spire: widens as it rises, then tapers.
        int[] widths = {1, 2, 2, 2, 1, 1, 0, 0};
        for (int dy = 1; dy <= widths.length; dy++) {
            int w = widths[dy - 1];
            for (int dx = -w; dx <= w; dx++) {
                for (int dz = -w; dz <= w; dz++) {
                    boolean shell = Math.abs(dx) == w || Math.abs(dz) == w;
                    set(level, floor.offset(dx, dy, dz),
                            shell && random.nextInt(4) == 0 ? Blocks.BUDDING_AMETHYST : Blocks.AMETHYST_BLOCK);
                }
            }
        }
        set(level, floor.above(widths.length + 1), Blocks.AMETHYST_CLUSTER);
        set(level, floor.above(widths.length + 2), Blocks.END_ROD);
        // The chest sits in an alcove at the spire's foot, facing south.
        set(level, floor.offset(0, 1, 3), Blocks.AIR);
        set(level, floor.offset(0, 2, 3), Blocks.AIR);
        chest(level, floor.offset(0, 1, 2), CRYSTAL_SHRINE, random);
    }

    // ---------------------------------------------------------------- Amber Vault

    /** A squat honey-and-terracotta strongroom, sealed with amber, one way in. */
    private static void vault(ServerLevel level, BlockPos floor, RandomSource random) {
        clear(level, floor, 5, 7);
        platform(level, floor, 5, Blocks.ORANGE_TERRACOTTA, Blocks.TERRACOTTA);
        for (int dy = 1; dy <= 4; dy++) {
            box(level, floor, 4, dy, dy, dy == 4 ? Blocks.HONEYCOMB_BLOCK : Blocks.TERRACOTTA);
        }
        for (int dx = -4; dx <= 4; dx++) {
            for (int dz = -4; dz <= 4; dz++) {
                set(level, floor.offset(dx, 5, dz), Math.abs(dx) == 4 || Math.abs(dz) == 4 ? Blocks.HONEYCOMB_BLOCK : Blocks.ORANGE_TERRACOTTA);
            }
        }
        // Amber windows.
        for (Direction d : Direction.Plane.HORIZONTAL) {
            set(level, floor.relative(d, 4).above(2), Blocks.ORANGE_STAINED_GLASS);
            set(level, floor.relative(d, 4).above(3), Blocks.ORANGE_STAINED_GLASS);
        }
        // One doorway, sealed with honey blocks you have to dig through.
        set(level, floor.offset(0, 1, 4), Blocks.HONEY_BLOCK);
        set(level, floor.offset(0, 2, 4), Blocks.HONEY_BLOCK);
        for (int dx = -2; dx <= 2; dx += 4) {
            for (int dz = -2; dz <= 2; dz += 4) {
                set(level, floor.offset(dx, 1, dz), Blocks.HONEYCOMB_BLOCK);
                set(level, floor.offset(dx, 2, dz), Blocks.SHROOMLIGHT);
            }
        }
        chest(level, floor.offset(0, 1, -3), AMBER_VAULT, random);
        set(level, floor.offset(0, 1, -2), Blocks.HONEYCOMB_BLOCK);
    }

    // ---------------------------------------------------------------- Shadow Nest

    /** A pale-oak thicket grown over a pit. Something lives here. */
    private static void nest(ServerLevel level, BlockPos floor, RandomSource random) {
        clear(level, floor, 6, 10);
        platform(level, floor, 6, Blocks.PALE_MOSS_BLOCK, Blocks.BLACKSTONE);
        // Trunks around the rim, leaning in, roofed with pale leaves.
        for (int i = 0; i < 8; i++) {
            double a = Math.PI * 2 * i / 8;
            int dx = (int) Math.round(Math.cos(a) * 5);
            int dz = (int) Math.round(Math.sin(a) * 5);
            pillar(level, floor.offset(dx, 0, dz), 5 + random.nextInt(3), Blocks.PALE_OAK_LOG, null);
        }
        for (int dx = -6; dx <= 6; dx++) {
            for (int dz = -6; dz <= 6; dz++) {
                if (dx * dx + dz * dz <= 36 && random.nextInt(3) != 0) {
                    set(level, floor.offset(dx, 7, dz), Blocks.PALE_OAK_LEAVES.defaultBlockState()
                            .setValue(net.minecraft.world.level.block.LeavesBlock.PERSISTENT, true));
                    if (random.nextInt(4) == 0) {
                        set(level, floor.offset(dx, 6, dz), Blocks.PALE_HANGING_MOSS);
                    }
                }
            }
        }
        // The pit, with the chest at the bottom under a bone-block cairn.
        for (int dx = -2; dx <= 2; dx++) {
            for (int dz = -2; dz <= 2; dz++) {
                for (int dy = 0; dy >= -4; dy--) {
                    set(level, floor.offset(dx, dy, dz), dy == -4 ? Blocks.BLACKSTONE : Blocks.AIR);
                }
            }
        }
        set(level, floor.offset(0, -3, 0), Blocks.BONE_BLOCK);
        chest(level, floor.offset(0, -3, 1), SHADOW_NEST, random);
        set(level, floor.offset(-2, -3, -2), Blocks.SOUL_LANTERN);
        set(level, floor.offset(2, -3, 2), Blocks.SOUL_LANTERN);
        // Its residents.
        for (int i = 0; i < 3; i++) {
            net.minecraft.world.entity.Entity walker = net.minecraft.world.entity.EntityType.WITHER_SKELETON.create(
                    level, net.minecraft.world.entity.EntitySpawnReason.STRUCTURE);
            if (walker != null) {
                walker.snapTo(floor.getX() + 0.5 + random.nextInt(3) - 1, floor.getY() - 3, floor.getZ() + 0.5 + random.nextInt(3) - 1, 0, 0);
                level.addFreshEntity(walker);
            }
        }
    }

    // --------------------------------------------------------- Sunken Observatory

    /** A prismarine dome, half-drowned, with a sea lantern eye and the chest in the dry room. */
    private static void observatory(ServerLevel level, BlockPos floor, RandomSource random) {
        clear(level, floor, 6, 8);
        platform(level, floor, 6, Blocks.PRISMARINE_BRICKS, Blocks.PRISMARINE);
        int r = 5;
        for (int dx = -r; dx <= r; dx++) {
            for (int dy = 1; dy <= r; dy++) {
                for (int dz = -r; dz <= r; dz++) {
                    double d = Math.sqrt(dx * dx + dy * dy + dz * dz);
                    if (d <= r && d > r - 1.2) {
                        boolean window = dy >= 2 && (dx == 0 || dz == 0) && random.nextInt(3) == 0;
                        set(level, floor.offset(dx, dy, dz), window ? Blocks.LIGHT_BLUE_STAINED_GLASS
                                : (random.nextInt(6) == 0 ? Blocks.DARK_PRISMARINE : Blocks.PRISMARINE_BRICKS));
                    }
                }
            }
        }
        set(level, floor.above(r), Blocks.SEA_LANTERN);
        doorways(level, floor, r, 2);
        // A shallow pool inside, lanterns at its corners, the chest on a dais.
        for (int dx = -2; dx <= 2; dx++) {
            for (int dz = -2; dz <= 2; dz++) {
                set(level, floor.offset(dx, 0, dz), Blocks.WATER);
            }
        }
        set(level, floor, Blocks.DARK_PRISMARINE);
        set(level, floor.above(), Blocks.DARK_PRISMARINE);
        chest(level, floor.above(2), SUNKEN_OBSERVATORY, random);
        for (int dx = -3; dx <= 3; dx += 6) {
            for (int dz = -3; dz <= 3; dz += 6) {
                set(level, floor.offset(dx, 1, dz), Blocks.SEA_LANTERN);
            }
        }
    }

    // -------------------------------------------------------------- Starfall Cairn

    /** A shard of blue ice adrift in the void, with a cairn of packed ice and snow on top. */
    private static void cairn(ServerLevel level, BlockPos floor, RandomSource random) {
        int r = 5;
        for (int dx = -r; dx <= r; dx++) {
            for (int dz = -r; dz <= r; dz++) {
                double d = Math.sqrt(dx * dx + dz * dz);
                if (d > r) {
                    continue;
                }
                int depth = (int) Math.round((r - d) * 1.2) + 1;
                for (int dy = 0; dy > -depth; dy--) {
                    set(level, floor.offset(dx, dy, dz), dy == 0 ? Blocks.PACKED_ICE : Blocks.BLUE_ICE);
                }
                if (dy_snow(random)) {
                    set(level, floor.offset(dx, 1, dz), Blocks.SNOW);
                }
            }
        }
        int[] tiers = {2, 2, 1, 1, 0};
        for (int dy = 1; dy <= tiers.length; dy++) {
            int w = tiers[dy - 1];
            for (int dx = -w; dx <= w; dx++) {
                for (int dz = -w; dz <= w; dz++) {
                    set(level, floor.offset(dx, dy, dz), Blocks.PACKED_ICE);
                }
            }
        }
        set(level, floor.above(tiers.length + 1), Blocks.BLUE_ICE);
        set(level, floor.above(tiers.length + 2), Blocks.END_ROD);
        chest(level, floor.offset(0, 1, 3), STARFALL_CAIRN, random);
        set(level, floor.offset(0, 0, 3), Blocks.BLUE_ICE);
    }

    private static boolean dy_snow(RandomSource random) {
        return random.nextInt(3) == 0;
    }

    // ------------------------------------------------------------- Eternal Portal

    /**
     * A ring of obsidian and crying obsidian, six chiseled purpur pedestals around it, each
     * topped with an end rod that a lit crystal replaces. When all six are lit, the mod fills
     * the ring with end portal blocks - which, in the End, lead home.
     */
    private static List<BlockPos> portal(ServerLevel level, BlockPos floor) {
        clear(level, floor, 8, 6);
        platform(level, floor, 8, Blocks.END_STONE_BRICKS, Blocks.END_STONE);
        for (int dx = -8; dx <= 8; dx++) {
            for (int dz = -8; dz <= 8; dz++) {
                if (Math.abs(dx) == 8 || Math.abs(dz) == 8) {
                    set(level, floor.offset(dx, 0, dz), Blocks.PURPUR_BLOCK);
                }
            }
        }
        // The frame: a 5x5 ring one block high around a 3x3 hollow.
        for (int dx = -2; dx <= 2; dx++) {
            for (int dz = -2; dz <= 2; dz++) {
                boolean frame = Math.abs(dx) == 2 || Math.abs(dz) == 2;
                if (frame) {
                    boolean corner = Math.abs(dx) == 2 && Math.abs(dz) == 2;
                    set(level, floor.offset(dx, 1, dz), corner ? Blocks.CRYING_OBSIDIAN : Blocks.OBSIDIAN);
                } else {
                    set(level, floor.offset(dx, 0, dz), Blocks.OBSIDIAN);   // the bed the portal fills
                }
            }
        }
        List<BlockPos> pedestals = new ArrayList<>();
        for (int i = 0; i < 6; i++) {
            double a = Math.PI * 2 * i / 6;
            int dx = (int) Math.round(Math.cos(a) * 5.5);
            int dz = (int) Math.round(Math.sin(a) * 5.5);
            BlockPos base = floor.offset(dx, 1, dz);
            set(level, base, Blocks.PURPUR_PILLAR);
            set(level, base.above(), Blocks.END_ROD);
            pedestals.add(base);
        }
        for (int dx = -7; dx <= 7; dx += 14) {
            for (int dz = -7; dz <= 7; dz += 14) {
                pillar(level, floor.offset(dx, 0, dz), 3, Blocks.PURPUR_PILLAR, Blocks.SOUL_LANTERN);
            }
        }
        chest(level, floor.offset(0, 1, -7), ETERNAL_PORTAL, RandomSource.create(floor.asLong()));
        return pedestals;
    }
}
