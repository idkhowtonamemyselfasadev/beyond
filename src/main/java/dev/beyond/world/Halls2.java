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

import java.util.List;

/**
 * The two boss halls that are built block by block: the Void Crypt, which the Void Warden
 * sleeps under, and the Storm Spire, which the Gale Sovereign rides the wind above.
 *
 * <p>Neither is a jigsaw structure, for the same reason the castles are not: a jigsaw
 * start over the void is dropped silently, and the End is mostly void. So the region grid
 * in {@link Sites} nominates a spot on an island, this stamps a hall down, and the site
 * record remembers where. The dais block in each is the alarm clock: a sculk shrieker in
 * the crypt, a lightning rod on the spire. Using it wakes the boss.
 */
public final class Halls2 {

    public static final String VOID_CRYPT = "void_crypt";
    public static final String STORM_SPIRE = "storm_spire";
    public static final List<String> TYPES = List.of(VOID_CRYPT, STORM_SPIRE);

    /** Half-width of the footprint either hall protects around its dais. */
    public static final int RADIUS = 14;
    /** How far below the dais the crypt reaches, and how far above it the spire does. */
    public static final int CRYPT_DEPTH = 12;
    public static final int SPIRE_HEIGHT = 36;

    private Halls2() {
    }

    public static boolean isHall(String type) {
        return TYPES.contains(type);
    }

    /** The block at the dais that, used, wakes the hall's boss. */
    public static Block trigger(String type) {
        return VOID_CRYPT.equals(type) ? Blocks.SCULK_SHRIEKER : Blocks.LIGHTNING_ROD;
    }

    /**
     * Builds the hall with its dais block at {@code dais}.
     *
     * @param dais where the trigger block ends up; the crypt digs down from here, the spire
     *             stands its platform here and climbs above it
     */
    public static void build(ServerLevel level, String type, BlockPos dais, RandomSource random) {
        if (VOID_CRYPT.equals(type)) {
            crypt(level, dais, random);
        } else {
            spire(level, dais, random);
        }
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

    private static void chest(ServerLevel level, BlockPos pos, String table, RandomSource random) {
        set(level, pos, Blocks.CHEST);
        if (level.getBlockEntity(pos) instanceof RandomizableContainerBlockEntity container) {
            container.setLootTable(ResourceKey.create(Registries.LOOT_TABLE,
                    Identifier.parse(Beyond.MODID + ":chests/" + table)));
            container.setLootTableSeed(random.nextLong());
        }
    }

    private static void fill(ServerLevel level, BlockPos a, int dx0, int dy0, int dz0, int dx1, int dy1, int dz1, Block block) {
        for (int dx = dx0; dx <= dx1; dx++) {
            for (int dy = dy0; dy <= dy1; dy++) {
                for (int dz = dz0; dz <= dz1; dz++) {
                    set(level, a.offset(dx, dy, dz), block);
                }
            }
        }
    }

    // -------------------------------------------------------------------- Void Crypt

    /**
     * A sunken vault: a ring of sculk-veined deepslate steps down from a surface shrine into
     * a chamber twelve blocks under the island, dark, its floor a spiral of sculk with the
     * shrieker in the middle. Four alcoves with chests, eight pillars, soul fire in the
     * corners, and a well of sculk in the centre so the Warden has somewhere to come from.
     */
    private static void crypt(ServerLevel level, BlockPos dais, RandomSource random) {
        BlockPos top = dais.above(CRYPT_DEPTH);   // surface level: the shrine
        int r = RADIUS - 2;
        // The surface shrine: a low ring of deepslate tiles, a stair down in the middle.
        fill(level, top, -r, 1, -r, r, 8, r, Blocks.AIR);
        fill(level, top, -r, 0, -r, r, 0, r, Blocks.DEEPSLATE_TILES);
        for (int dx = -r; dx <= r; dx++) {
            for (int dz = -r; dz <= r; dz++) {
                int ring = Math.max(Math.abs(dx), Math.abs(dz));
                if (ring == r) {
                    set(level, top.offset(dx, 1, dz), Blocks.DEEPSLATE_BRICK_WALL);
                }
                if (ring == r && (Math.abs(dx) == r && Math.abs(dz) == r)) {
                    set(level, top.offset(dx, 1, dz), Blocks.CHISELED_DEEPSLATE);
                    set(level, top.offset(dx, 2, dz), Blocks.SOUL_LANTERN);
                }
            }
        }
        // The shaft: a 5x5 well from the shrine down to the chamber, with a spiral stair.
        fill(level, top, -2, -CRYPT_DEPTH + 1, -2, 2, 0, 2, Blocks.AIR);
        fill(level, top, -3, -CRYPT_DEPTH + 1, -3, 3, 0, 3, Blocks.DEEPSLATE_BRICKS);
        fill(level, top, -2, -CRYPT_DEPTH + 1, -2, 2, 0, 2, Blocks.AIR);
        int[][] spiral = {{-2, -2}, {-1, -2}, {0, -2}, {1, -2}, {2, -2}, {2, -1}, {2, 0}, {2, 1}, {2, 2},
                {1, 2}, {0, 2}, {-1, 2}, {-2, 2}, {-2, 1}, {-2, 0}, {-2, -1}};
        for (int step = 0; step < CRYPT_DEPTH; step++) {
            int[] s = spiral[step % spiral.length];
            set(level, top.offset(s[0], -step, s[1]), Blocks.DEEPSLATE_TILE_SLAB);
        }
        // The chamber: a hollow under the island, walled in deepslate, floored in sculk.
        int cr = RADIUS - 1;
        fill(level, dais, -cr - 1, -2, -cr - 1, cr + 1, 7, cr + 1, Blocks.DEEPSLATE_BRICKS);
        fill(level, dais, -cr, 0, -cr, cr, 6, cr, Blocks.AIR);
        fill(level, dais, -cr, -1, -cr, cr, -1, cr, Blocks.SCULK);
        for (int dx = -cr; dx <= cr; dx++) {
            for (int dz = -cr; dz <= cr; dz++) {
                double d = Math.hypot(dx, dz);
                if (d > 4 && random.nextInt(3) == 0) {
                    set(level, dais.offset(dx, -1, dz), Blocks.DEEPSLATE_TILES);
                }
                if (d > 9 && d < 10.5 && random.nextInt(4) == 0) {
                    set(level, dais.offset(dx, 0, dz), Blocks.SCULK_VEIN);
                }
            }
        }
        // Eight pillars, soul fire on the four corners.
        for (int i = 0; i < 8; i++) {
            double a = Math.PI * 2 * i / 8;
            int px = (int) Math.round(Math.cos(a) * 9);
            int pz = (int) Math.round(Math.sin(a) * 9);
            fill(level, dais, px, 0, pz, px, 5, pz, Blocks.DEEPSLATE_BRICKS);
            set(level, dais.offset(px, 6, pz), Blocks.CHISELED_DEEPSLATE);
            if (i % 2 == 0) {
                set(level, dais.offset(px, 3, pz), Blocks.SCULK_CATALYST);
            }
        }
        for (int sx = -1; sx <= 1; sx += 2) {
            for (int sz = -1; sz <= 1; sz += 2) {
                set(level, dais.offset(sx * (cr - 1), 0, sz * (cr - 1)), Blocks.SOUL_SAND);
                set(level, dais.offset(sx * (cr - 1), 1, sz * (cr - 1)), Blocks.SOUL_FIRE);
            }
        }
        // Four alcoves cut into the walls, a chest in each.
        for (Direction d : Direction.Plane.HORIZONTAL) {
            BlockPos mouth = dais.relative(d, cr + 1);
            fill(level, mouth, -1, 0, -1, 1, 2, 1, Blocks.AIR);
            fill(level, mouth.relative(d), -1, -1, -1, 1, 3, 1, Blocks.DEEPSLATE_BRICKS);
            fill(level, mouth.relative(d), -1, 0, -1, 1, 2, 1, Blocks.AIR);
            chest(level, mouth.relative(d), "void_crypt", random);
            set(level, mouth.relative(d).above(2), Blocks.SOUL_LANTERN);
        }
        // The dais: a raised sculk ring, the shrieker on a block of reinforced-looking slate.
        fill(level, dais, -2, 0, -2, 2, 0, 2, Blocks.SCULK);
        fill(level, dais, -1, 0, -1, 1, 0, 1, Blocks.POLISHED_DEEPSLATE);
        set(level, dais, Blocks.SCULK_SHRIEKER);
        // The shrieker exists to be right-clicked; vanilla's own shriek on being stepped on
        // would summon a plain warden and spoil the boss, so it is never a "can summon" one.
        for (int sx = -1; sx <= 1; sx += 2) {
            for (int sz = -1; sz <= 1; sz += 2) {
                set(level, dais.offset(sx, 0, sz), Blocks.SCULK_SENSOR);
            }
        }
    }

    // -------------------------------------------------------------------- Storm Spire

    /**
     * A tower of end stone bricks and purpur climbing thirty-six blocks off an island, a
     * spiral stair inside, copper roofing gone green, and an open platform on top with
     * the lightning rod on its dais and nothing between you and the void but a low rail.
     * Four lanterns on chains, four chests at the platform's corners.
     */
    private static void spire(ServerLevel level, BlockPos dais, RandomSource random) {
        BlockPos base = dais.below(SPIRE_HEIGHT);   // island surface
        int r = 6;
        // Foundation down into the island and the tower's shaft up from it.
        fill(level, base, -r - 2, -8, -r - 2, r + 2, -1, r + 2, Blocks.END_STONE_BRICKS);
        fill(level, base, -r - 2, 0, -r - 2, r + 2, 0, r + 2, Blocks.PURPUR_BLOCK);
        for (int dy = 1; dy <= SPIRE_HEIGHT - 1; dy++) {
            for (int dx = -r; dx <= r; dx++) {
                for (int dz = -r; dz <= r; dz++) {
                    double d = Math.hypot(dx, dz);
                    if (d > r + 0.5) {
                        continue;
                    }
                    boolean wall = d > r - 1.0;
                    Block block = wall ? (dy % 6 == 0 ? Blocks.PURPUR_PILLAR : Blocks.END_STONE_BRICKS) : Blocks.AIR;
                    if (wall && (dy % 6 == 3) && (Math.abs(dx) < 2 || Math.abs(dz) < 2)) {
                        block = Blocks.AIR;   // window slits
                    }
                    set(level, base.offset(dx, dy, dz), block);
                }
            }
        }
        // The spiral stair up the inside of the wall.
        int[][] spiral = {{-4, -4}, {-2, -5}, {0, -5}, {2, -5}, {4, -4}, {5, -2}, {5, 0}, {5, 2},
                {4, 4}, {2, 5}, {0, 5}, {-2, 5}, {-4, 4}, {-5, 2}, {-5, 0}, {-5, -2}};
        for (int step = 0; step < SPIRE_HEIGHT; step++) {
            int[] s = spiral[step % spiral.length];
            set(level, base.offset(s[0], step, s[1]), Blocks.PURPUR_SLAB);
            set(level, base.offset(s[0], step + 1, s[1]), Blocks.AIR);
            set(level, base.offset(s[0], step + 2, s[1]), Blocks.AIR);
        }
        // Lanterns in the shaft so the climb is not in the dark.
        for (int dy = 4; dy < SPIRE_HEIGHT; dy += 8) {
            set(level, base.offset(0, dy, 0), Blocks.END_ROD);
        }
        // The platform: a 15x15 disc of purpur with a rail, and a copper canopy at the corners.
        int pr = RADIUS - 7;
        for (int dx = -RADIUS; dx <= RADIUS; dx++) {
            for (int dz = -RADIUS; dz <= RADIUS; dz++) {
                double d = Math.hypot(dx, dz);
                if (d > pr + 0.5) {
                    continue;
                }
                set(level, dais.offset(dx, -1, dz), d > pr - 1.0 ? Blocks.PURPUR_BLOCK : Blocks.END_STONE_BRICKS);
                fill(level, dais, dx, 0, dz, dx, 6, dz, Blocks.AIR);
                if (d > pr - 1.0) {
                    set(level, dais.offset(dx, 0, dz), Blocks.END_STONE_BRICK_WALL);
                }
            }
        }
        // The stair mouth: the last step of the spiral opens through the platform floor.
        int[] mouth = spiral[(SPIRE_HEIGHT - 1) % spiral.length];
        set(level, dais.offset(mouth[0], -1, mouth[1]), Blocks.AIR);
        set(level, dais.offset(mouth[0], -1, mouth[1]).relative(Direction.getNearest(-mouth[0], 0, -mouth[1], Direction.NORTH)), Blocks.PURPUR_STAIRS);
        // Four copper pylons with lanterns on chains, a chest at the foot of each.
        for (int i = 0; i < 4; i++) {
            double a = Math.PI / 4 + Math.PI / 2 * i;
            int px = (int) Math.round(Math.cos(a) * (pr - 2));
            int pz = (int) Math.round(Math.sin(a) * (pr - 2));
            fill(level, dais, px, 0, pz, px, 5, pz, Blocks.OXIDIZED_COPPER);
            set(level, dais.offset(px, 6, pz), Blocks.OXIDIZED_CUT_COPPER);
            Direction inward = Direction.getNearest(-px, 0, -pz, Direction.NORTH);
            set(level, dais.offset(px, 5, pz).relative(inward), Blocks.IRON_CHAIN);
            set(level, dais.offset(px, 4, pz).relative(inward), Blocks.LANTERN);
            chest(level, dais.offset(px, 0, pz).relative(inward), "storm_spire", random);
        }
        // The dais: a copper square set into the floor, the rod standing on it.
        fill(level, dais, -1, -1, -1, 1, -1, 1, Blocks.WAXED_OXIDIZED_COPPER);
        set(level, dais, Blocks.LIGHTNING_ROD);
    }
}
