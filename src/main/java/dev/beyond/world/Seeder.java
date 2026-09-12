package dev.beyond.world;

import dev.beyond.Beyond;
import dev.beyond.BeyondConfig;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.SectionPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.WorldgenRandom;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureSet;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

/**
 * Gives a world that was generated before the mod - or before part of it - the things it
 * never grew.
 *
 * <p>Two kinds of content only appear in chunks generated after they were added. The
 * mod's own code-placed sites (ruins, portals, rivers, castles, boss halls) are built when
 * a region's candidate chunk is first seen loaded, so a pre-generated world's regions are
 * never seen; and the jigsaw structures (the cities, the monuments, the Throne City) are
 * vanilla worldgen, which never revisits a chunk. This walks every region in range, loads
 * each candidate chunk, and puts down what the chunk would have had: the sites through the
 * same placement code that grows them naturally, the jigsaws through the same generator
 * {@code /place structure} uses, at the same grid cells the structure set would have chosen.
 * Regions already handled stay handled, so running it twice builds nothing more.
 */
public final class Seeder {

    public record Report(Map<String, Integer> built, int regions, int chunksLoaded) {
        public int total() {
            return built.values().stream().mapToInt(Integer::intValue).sum();
        }
    }

    private static final List<ResourceKey<StructureSet>> SETS = List.of(
            ResourceKey.create(Registries.STRUCTURE_SET, Identifier.parse(Beyond.MODID + ":cities")),
            ResourceKey.create(Registries.STRUCTURE_SET, Identifier.parse(Beyond.MODID + ":monuments")));

    private Seeder() {
    }

    public static Report seed(ServerLevel end, BlockPos around, int radiusBlocks, BeyondConfig config,
                              Consumer<String> progress) {
        Map<String, Integer> built = new LinkedHashMap<>();
        int[] regions = {0};
        int[] loaded = {0};
        Sites sites = Beyond.sites();

        // 1. The code-placed grids, through Sites' own placement.
        int before = sites.count();
        Map<String, Integer> byType = new LinkedHashMap<>();
        for (Sites.Site site : sites.all()) {
            byType.merge(site.type, 1, Integer::sum);
        }
        regions[0] += sites.seed(end, around, radiusBlocks, config, loaded);
        for (Sites.Site site : sites.all()) {
            byType.merge(site.type, -1, Integer::sum);
        }
        for (Map.Entry<String, Integer> e : byType.entrySet()) {
            if (e.getValue() < 0) {
                built.put(e.getKey(), -e.getValue());
            }
        }
        progress.accept("Sites: " + (sites.count() - before) + " built");

        // 2. The jigsaw sets, at the cells their placement would have chosen.
        var setRegistry = end.registryAccess().lookupOrThrow(Registries.STRUCTURE_SET);
        for (ResourceKey<StructureSet> key : SETS) {
            var holder = setRegistry.get(key).orElse(null);
            if (holder == null) {
                continue;
            }
            StructureSet set = holder.value();
            if (!(set.placement() instanceof RandomSpreadStructurePlacement spread)) {
                continue;
            }
            int placed = 0;
            int spacing = spread.spacing();
            int cellRadius = radiusBlocks / (spacing * 16) + 1;
            int cellX = Math.floorDiv(SectionPos.blockToSectionCoord(around.getX()), spacing);
            int cellZ = Math.floorDiv(SectionPos.blockToSectionCoord(around.getZ()), spacing);
            for (int cx = cellX - cellRadius; cx <= cellX + cellRadius; cx++) {
                for (int cz = cellZ - cellRadius; cz <= cellZ + cellRadius; cz++) {
                    ChunkPos chunk = spread.getPotentialStructureChunk(end.getSeed(), cx, cz);
                    if (Math.hypot(chunk.getMiddleBlockX() - around.getX(), chunk.getMiddleBlockZ() - around.getZ()) > radiusBlocks) {
                        continue;
                    }
                    regions[0]++;
                    if (alreadyHas(end, chunk, set)) {
                        continue;   // it generated naturally, or a previous seed run put it there
                    }
                    if (placeFromSet(end, set, chunk, loaded)) {
                        placed++;
                    }
                }
            }
            String name = key.identifier().getPath();
            built.put(name, placed);
            progress.accept(name + ": " + placed + " placed");
        }
        return new Report(built, regions[0], loaded[0]);
    }

    /** True if any structure of this set already has a start in this chunk. */
    private static boolean alreadyHas(ServerLevel end, ChunkPos chunk, StructureSet set) {
        loadedChunk(end, chunk, null);
        List<Structure> members = set.structures().stream().map(e -> e.structure().value()).toList();
        return !end.structureManager().startsForStructure(chunk, members::contains).isEmpty();
    }

    private static void loadedChunk(ServerLevel end, ChunkPos chunk, int[] counter) {
        if (!end.hasChunk(chunk.x, chunk.z) && counter != null) {
            counter[0]++;
        }
        end.getChunk(chunk.x, chunk.z);
    }

    /**
     * Picks a structure from the set by weight, seeded by the cell like vanilla, generates
     * its start at this chunk and stamps every chunk of its bounding box - the same steps
     * {@code /place structure} takes, with the set's own biome rule kept.
     */
    private static boolean placeFromSet(ServerLevel end, StructureSet set, ChunkPos chunk, int[] loaded) {
        WorldgenRandom random = new WorldgenRandom(new net.minecraft.world.level.levelgen.LegacyRandomSource(0L));
        random.setLargeFeatureSeed(end.getSeed(), chunk.x, chunk.z);
        List<StructureSet.StructureSelectionEntry> entries = new ArrayList<>(set.structures());
        int total = entries.stream().mapToInt(StructureSet.StructureSelectionEntry::weight).sum();
        // Try the weighted pick first, then the rest: a cell whose biome cannot host the
        // chosen structure still gets whichever of the set fits, the way vanilla's loop does.
        while (!entries.isEmpty() && total > 0) {
            int roll = random.nextInt(total);
            StructureSet.StructureSelectionEntry pick = null;
            for (StructureSet.StructureSelectionEntry entry : entries) {
                roll -= entry.weight();
                if (roll < 0) {
                    pick = entry;
                    break;
                }
            }
            if (pick == null) {
                pick = entries.get(0);
            }
            if (place(end, pick.structure(), chunk, loaded)) {
                return true;
            }
            entries.remove(pick);
            total -= pick.weight();
        }
        return false;
    }

    public static boolean place(ServerLevel end, Holder<Structure> holder, ChunkPos chunk, int[] loaded) {
        ChunkGenerator generator = end.getChunkSource().getGenerator();
        Structure structure = holder.value();
        loadedChunk(end, chunk, loaded);
        StructureStart start = structure.generate(holder, end.dimension(), end.registryAccess(), generator,
                generator.getBiomeSource(), end.getChunkSource().randomState(), end.getStructureManager(),
                end.getSeed(), chunk, 0, end, structure.biomes()::contains);
        if (!start.isValid()) {
            return false;
        }
        BoundingBox box = start.getBoundingBox();
        ChunkPos min = new ChunkPos(SectionPos.blockToSectionCoord(box.minX()), SectionPos.blockToSectionCoord(box.minZ()));
        ChunkPos max = new ChunkPos(SectionPos.blockToSectionCoord(box.maxX()), SectionPos.blockToSectionCoord(box.maxZ()));
        ChunkPos.rangeClosed(min, max).forEach(pos -> {
            loadedChunk(end, pos, loaded);
            start.placeInChunk(end, end.structureManager(), generator, RandomSource.create(end.getSeed() ^ pos.toLong()),
                    new BoundingBox(pos.getMinBlockX(), end.getMinY(), pos.getMinBlockZ(),
                            pos.getMaxBlockX(), end.getMaxY(), pos.getMaxBlockZ()), pos);
            // Every chunk the box covers points back at the start, so protection, /locate
            // and a second seed run all see the structure the way they see a natural one.
            end.getChunk(pos.x, pos.z).addReferenceForStructure(structure, chunk.toLong());
            end.getChunk(pos.x, pos.z).markUnsaved();
        });
        end.getChunk(chunk.x, chunk.z).setStartForStructure(structure, start);
        Beyond.LOGGER.info("Structure seeded: {} at {} {} {}", holder.unwrapKey().map(k -> k.identifier().toString()).orElse("?"),
                box.getCenter().getX(), box.getCenter().getY(), box.getCenter().getZ());
        return true;
    }
}
