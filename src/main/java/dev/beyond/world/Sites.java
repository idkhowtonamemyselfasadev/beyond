package dev.beyond.world;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;
import dev.beyond.Beyond;
import dev.beyond.BeyondConfig;
import net.minecraft.core.BlockPos;
import net.minecraft.core.SectionPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.storage.LevelResource;

import java.io.Reader;
import java.io.Writer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;

/**
 * Where the structures are, and the decision to put one somewhere.
 *
 * <p>Vanilla structures need template NBT and jigsaw pools. These are built by code instead,
 * the way the biomes' own flora is, which keeps them free of anything a client would need.
 * Placement is seed-deterministic on a grid of regions, one candidate chunk per region, so
 * the same seed gives the same map and no two are neighbours. A region is considered once,
 * when a player is near enough for its candidate chunk to be loaded, and recorded either way
 * - so nothing is ever placed twice, and a chunk whose surface a structure has raised is
 * never re-read for a second one.
 */
public final class Sites {

    public static final class Site {
        public String type;
        public int x, y, z;
        /** Portal pedestals, as packed block positions. Empty for anything else. */
        public List<Long> pedestals = new ArrayList<>();
        /** Portal: a bit per lit pedestal. */
        public int lit;

        public BlockPos pos() {
            return new BlockPos(x, y, z);
        }
    }

    private static final class Saved {
        List<Site> sites = new ArrayList<>();
        Set<String> regions = new HashSet<>();
    }

    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final long SALT = 0x4245_594F_4E44L;   // "BEYOND"

    private final List<Site> sites = new ArrayList<>();
    private final Set<String> handledRegions = new HashSet<>();
    private Path file;
    private boolean dirty;

    // ------------------------------------------------------------------- persistence

    public void load(MinecraftServer server) {
        sites.clear();
        handledRegions.clear();
        file = server.getWorldPath(LevelResource.ROOT).resolve("beyond-sites.json");
        if (!Files.exists(file)) {
            return;
        }
        try (Reader reader = Files.newBufferedReader(file)) {
            Saved saved = GSON.fromJson(reader, new TypeToken<Saved>() {
            }.getType());
            if (saved != null) {
                sites.addAll(saved.sites);
                handledRegions.addAll(saved.regions);
            }
            Beyond.LOGGER.info("Loaded {} End structure sites", sites.size());
        } catch (Exception e) {
            Beyond.LOGGER.error("Could not read {}; existing structures will not respond: {}", file, e.toString());
        }
    }

    public void save() {
        if (!dirty || file == null) {
            return;
        }
        Saved saved = new Saved();
        saved.sites = sites;
        saved.regions = handledRegions;
        try (Writer writer = Files.newBufferedWriter(file)) {
            GSON.toJson(saved, writer);
            dirty = false;
        } catch (Exception e) {
            Beyond.LOGGER.error("Could not write {}: {}", file, e.toString());
        }
    }

    public List<Site> all() {
        return sites;
    }

    public int count() {
        return sites.size();
    }

    // --------------------------------------------------------------------- placement

    /** Once a second: the regions around every player in the End. */
    public void onTick(MinecraftServer server, BeyondConfig config) {
        if (!config.structures_enabled) {
            return;
        }
        ServerLevel end = server.getLevel(Level.END);
        if (end == null) {
            return;
        }
        boolean changed = false;
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            if (player.level() != end) {
                continue;
            }
            changed |= scan(end, player.blockPosition(), config.structure_spacing_chunks, "s", config);
            changed |= scan(end, player.blockPosition(), config.portal_spacing_chunks, "p", config);
            if (config.rivers_enabled) {
                changed |= scan(end, player.blockPosition(), config.river_spacing_chunks, "r", config);
            }
            if (config.castles_enabled) {
                changed |= scan(end, player.blockPosition(), config.castle_spacing_chunks, "c", config);
            }
            if (config.boss_halls_enabled) {
                changed |= scan(end, player.blockPosition(), config.hall_spacing_chunks, "h", config);
            }
        }
        if (changed) {
            save();
        }
    }

    /**
     * Walks every region of every grid within the radius, loading each candidate chunk so
     * that the ordinary placement runs for it - for a world generated before the mod, whose
     * regions were never seen loaded. Regions already handled stay handled.
     *
     * @param loaded incremented for every chunk this had to load
     * @return how many regions were visited
     */
    public int seed(ServerLevel level, BlockPos around, int radiusBlocks, BeyondConfig config, int[] loaded) {
        int visited = 0;
        String[][] grids = {
                {"s", String.valueOf(config.structure_spacing_chunks)},
                {"p", String.valueOf(config.portal_spacing_chunks)},
                {"r", String.valueOf(config.river_spacing_chunks)},
                {"c", String.valueOf(config.castle_spacing_chunks)},
                {"h", String.valueOf(config.hall_spacing_chunks)}};
        for (String[] grid : grids) {
            String g = grid[0];
            if (g.equals("r") && !config.rivers_enabled || g.equals("c") && !config.castles_enabled
                    || g.equals("h") && !config.boss_halls_enabled) {
                continue;
            }
            int spacing = Math.max(1, Integer.parseInt(grid[1]));
            int regionRadius = radiusBlocks / (spacing * 16) + 1;
            int regionX = Math.floorDiv(SectionPos.blockToSectionCoord(around.getX()), spacing);
            int regionZ = Math.floorDiv(SectionPos.blockToSectionCoord(around.getZ()), spacing);
            for (int rx = regionX - regionRadius; rx <= regionX + regionRadius; rx++) {
                for (int rz = regionZ - regionRadius; rz <= regionZ + regionRadius; rz++) {
                    String key = g + ":" + rx + ":" + rz;
                    if (handledRegions.contains(key)) {
                        continue;
                    }
                    RandomSource random = RandomSource.create(level.getSeed()
                            ^ (rx * 341873128712L + rz * 132897987541L) ^ SALT ^ g.hashCode());
                    int cx = rx * spacing + random.nextInt(spacing);
                    int cz = rz * spacing + random.nextInt(spacing);
                    if (Math.hypot(cx * 16 + 8 - around.getX(), cz * 16 + 8 - around.getZ()) > radiusBlocks) {
                        continue;
                    }
                    if (!level.hasChunk(cx, cz)) {
                        loaded[0]++;
                    }
                    level.getChunk(cx, cz);
                    handledRegions.add(key);
                    dirty = true;
                    visited++;
                    try {
                        switch (g) {
                            case "r" -> considerRiver(level, cx, cz, random);
                            case "c" -> considerCastle(level, cx, cz, random);
                            case "h" -> considerHall(level, cx, cz, random);
                            default -> consider(level, cx, cz, g.equals("p"), random);
                        }
                    } catch (Exception e) {
                        Beyond.LOGGER.error("Seeding {} at chunk {} {} failed: {}", g, cx, cz, e.toString());
                    }
                }
            }
        }
        save();
        return visited;
    }

    private boolean scan(ServerLevel level, BlockPos around, int spacing, String grid, BeyondConfig config) {
        int reach = Math.max(1, config.structure_scan_regions);
        int chunkX = SectionPos.blockToSectionCoord(around.getX());
        int chunkZ = SectionPos.blockToSectionCoord(around.getZ());
        int regionX = Math.floorDiv(chunkX, spacing);
        int regionZ = Math.floorDiv(chunkZ, spacing);
        boolean changed = false;
        for (int dx = -reach; dx <= reach; dx++) {
            for (int dz = -reach; dz <= reach; dz++) {
                int rx = regionX + dx;
                int rz = regionZ + dz;
                String key = grid + ":" + rx + ":" + rz;
                if (handledRegions.contains(key)) {
                    continue;
                }
                RandomSource random = RandomSource.create(level.getSeed()
                        ^ (rx * 341873128712L + rz * 132897987541L) ^ SALT ^ grid.hashCode());
                int cx = rx * spacing + random.nextInt(spacing);
                int cz = rz * spacing + random.nextInt(spacing);
                if (!level.hasChunk(cx, cz)) {
                    continue;   // not generated yet; look again when it is
                }
                handledRegions.add(key);
                dirty = true;
                changed = true;
                if (grid.equals("r")) {
                    considerRiver(level, cx, cz, random);
                } else if (grid.equals("c")) {
                    considerCastle(level, cx, cz, random);
                } else if (grid.equals("h")) {
                    considerHall(level, cx, cz, random);
                } else {
                    consider(level, cx, cz, grid.equals("p"), random);
                }
            }
        }
        return changed;
    }

    private void consider(ServerLevel level, int chunkX, int chunkZ, boolean portal, RandomSource random) {
        int x = chunkX * 16 + 8;
        int z = chunkZ * 16 + 8;
        BlockPos column = new BlockPos(x, 64, z);
        Optional<String> biome = level.getBiome(column).unwrapKey().map(k -> k.identifier().toString());
        if (biome.isEmpty() || !biome.get().startsWith(Beyond.MODID + ":")) {
            return;
        }
        String type = portal ? Structures.ETERNAL_PORTAL : Structures.typeFor(biome.get(), random);
        if (type == null) {
            return;
        }
        // The Ice Starfield is the void between every island, so its cairn would otherwise be
        // three quarters of everything that generates.
        if (Structures.floats(type) && random.nextInt(4) != 0) {
            return;
        }
        int surface = level.getHeight(Heightmap.Types.WORLD_SURFACE_WG, x, z);
        BlockPos floor;
        if (Structures.floats(type)) {
            floor = new BlockPos(x, 50 + random.nextInt(40), z);
        } else {
            if (surface < 8) {
                return;   // void
            }
            floor = new BlockPos(x, surface - 1, z);
        }
        place(level, type, floor, random);
    }

    /** A castle needs a whole island: a few spots in the region are tried before giving up. */
    private void considerCastle(ServerLevel level, int chunkX, int chunkZ, RandomSource random) {
        String type = Castles.TYPES.get(random.nextInt(Castles.TYPES.size()));
        for (int attempt = 0; attempt < 6; attempt++) {
            int x = (chunkX + random.nextInt(9) - 4) * 16 + 8;
            int z = (chunkZ + random.nextInt(9) - 4) * 16 + 8;
            Optional<String> biome = level.getBiome(new BlockPos(x, 64, z)).unwrapKey().map(k -> k.identifier().toString());
            if (biome.isEmpty() || !biome.get().startsWith(Beyond.MODID + ":") || biome.get().endsWith("ice_starfield")) {
                continue;
            }
            if (Terrain.ground(level, x, z) < 44) {
                continue;
            }
            BlockPos placed = Castles.place(level, type, x, z, random);
            if (placed == null) {
                continue;
            }
            Site site = new Site();
            site.type = type;
            site.x = placed.getX();
            site.y = placed.getY();
            site.z = placed.getZ();
            sites.add(site);
            dirty = true;
            Beyond.LOGGER.info("Castle placed: {} at {} {} {}", type, site.x, site.y, site.z);
            return;
        }
    }

    /**
     * A boss hall needs an island like a castle does. The crypt digs into it; the spire
     * stands on it. Which one a region gets is the region's own roll.
     */
    private void considerHall(ServerLevel level, int chunkX, int chunkZ, RandomSource random) {
        String type = Halls2.TYPES.get(random.nextInt(Halls2.TYPES.size()));
        for (int attempt = 0; attempt < 6; attempt++) {
            int x = (chunkX + random.nextInt(7) - 3) * 16 + 8;
            int z = (chunkZ + random.nextInt(7) - 3) * 16 + 8;
            Optional<String> biome = level.getBiome(new BlockPos(x, 64, z)).unwrapKey().map(k -> k.identifier().toString());
            if (biome.isEmpty() || !biome.get().startsWith(Beyond.MODID + ":") || biome.get().endsWith("ice_starfield")) {
                continue;
            }
            int ground = Terrain.ground(level, x, z);
            if (ground < 48) {
                continue;
            }
            // The island has to be there under the whole footprint, not just the middle.
            boolean solid = true;
            for (int[] d : new int[][] {{Halls2.RADIUS, 0}, {-Halls2.RADIUS, 0}, {0, Halls2.RADIUS}, {0, -Halls2.RADIUS}}) {
                if (Terrain.ground(level, x + d[0], z + d[1]) < 40) {
                    solid = false;
                    break;
                }
            }
            if (!solid) {
                continue;
            }
            placeHall(level, type, new BlockPos(x, ground, z), random);
            return;
        }
    }

    /** Builds a hall whose island surface is at {@code surface}, records it, and says so. */
    public Site placeHall(ServerLevel level, String type, BlockPos surface, RandomSource random) {
        BlockPos dais = Halls2.VOID_CRYPT.equals(type)
                ? surface.below(1 + Halls2.CRYPT_DEPTH)
                : surface.below(1).above(Halls2.SPIRE_HEIGHT);
        Halls2.build(level, type, dais, random);
        Site site = new Site();
        site.type = type;
        site.x = dais.getX();
        site.y = dais.getY();
        site.z = dais.getZ();
        sites.add(site);
        dirty = true;
        save();
        Beyond.LOGGER.info("Boss hall placed: {} at {} {} {}", type, site.x, site.y, site.z);
        return site;
    }

    /** The hall whose dais block this is, or null. */
    public Site hallAt(BlockPos pos) {
        for (Site site : sites) {
            if (Halls2.isHall(site.type) && site.x == pos.getX() && site.y == pos.getY() && site.z == pos.getZ()) {
                return site;
            }
        }
        return null;
    }

    /** True if this block lies inside a boss hall's footprint. */
    public boolean inHall(BlockPos pos) {
        for (Site site : sites) {
            if (!Halls2.isHall(site.type)) {
                continue;
            }
            if (Math.abs(pos.getX() - site.x) > Halls2.RADIUS + 2 || Math.abs(pos.getZ() - site.z) > Halls2.RADIUS + 2) {
                continue;
            }
            int lo = Halls2.VOID_CRYPT.equals(site.type) ? site.y - 3 : site.y - Halls2.SPIRE_HEIGHT - 9;
            int hi = Halls2.VOID_CRYPT.equals(site.type) ? site.y + Halls2.CRYPT_DEPTH + 3 : site.y + 8;
            if (pos.getY() >= lo && pos.getY() <= hi) {
                return true;
            }
        }
        return false;
    }

    /** A river needs an island under it and a little luck: about one candidate in three. */
    private void considerRiver(ServerLevel level, int chunkX, int chunkZ, RandomSource random) {
        if (random.nextInt(3) != 0) {
            return;
        }
        int x = chunkX * 16 + 8;
        int z = chunkZ * 16 + 8;
        Optional<String> biome = level.getBiome(new BlockPos(x, 64, z)).unwrapKey().map(k -> k.identifier().toString());
        if (biome.isEmpty() || !biome.get().startsWith(Beyond.MODID + ":") || biome.get().endsWith("ice_starfield")) {
            return;
        }
        int surface = Terrain.ground(level, x, z);
        if (surface < 40) {
            return;
        }
        BlockPos start = new BlockPos(x, surface - 1, z);
        int carved = Rivers.build(level, start, random);
        if (carved == 0) {
            return;
        }
        Site site = new Site();
        site.type = Rivers.TYPE;
        site.x = start.getX();
        site.y = start.getY();
        site.z = start.getZ();
        sites.add(site);
        dirty = true;
        Beyond.LOGGER.info("River carved: {} blocks from {} {} {}", carved, site.x, site.y, site.z);
    }

    public Site place(ServerLevel level, String type, BlockPos floor, RandomSource random) {
        List<BlockPos> pedestals = Structures.build(level, type, floor, random);
        Site site = new Site();
        site.type = type;
        site.x = floor.getX();
        site.y = floor.getY();
        site.z = floor.getZ();
        for (BlockPos pedestal : pedestals) {
            site.pedestals.add(pedestal.asLong());
        }
        sites.add(site);
        dirty = true;
        save();
        Beyond.LOGGER.info("Structure placed: {} at {} {} {}", type, site.x, site.y, site.z);
        return site;
    }

    // ----------------------------------------------------------------------- lookup

    public Site nearest(String type, BlockPos from) {
        Site best = null;
        double bestDistance = Double.MAX_VALUE;
        for (Site site : sites) {
            if (type != null && !site.type.equals(type)) {
                continue;
            }
            double d = from.distSqr(site.pos());
            if (d < bestDistance) {
                bestDistance = d;
                best = site;
            }
        }
        return best;
    }

    /** The portal whose pedestal (or the block on it) this is, or null. */
    public Site portalAt(BlockPos pos) {
        for (Site site : sites) {
            if (!Structures.ETERNAL_PORTAL.equals(site.type)) {
                continue;
            }
            for (long packed : site.pedestals) {
                BlockPos pedestal = BlockPos.of(packed);
                if (pedestal.equals(pos) || pedestal.above().equals(pos)) {
                    return site;
                }
            }
        }
        return null;
    }

    public void markDirty() {
        dirty = true;
    }
}
