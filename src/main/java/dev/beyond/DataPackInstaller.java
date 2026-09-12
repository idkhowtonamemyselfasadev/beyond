package dev.beyond;

import net.fabricmc.loader.api.FabricLoader;
import net.fabricmc.loader.api.ModContainer;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Properties;
import java.util.stream.Stream;

/**
 * Puts the mod's data pack where the server will actually read it.
 *
 * <p>The biomes, terrain, flora, loot and advancements are data. Fabric Loader on its own does
 * not load the {@code data/} folder inside a mod jar - that is Fabric API's resource loader -
 * and this mod deliberately depends on nothing but the loader. So on every start, before the
 * world is opened, the data is copied out of the jar into {@code <world>/datapacks/beyond/},
 * which the server enables automatically. A world data pack is also exactly how Nullscape and
 * Terralith work, and it is the only place a dimension override is honoured for a new world.
 *
 * <p>Copied fresh every start, so a mod update never leaves stale data behind. Remove the mod
 * and the folder stays: the world keeps its biomes, which is what you want.
 */
public final class DataPackInstaller {

    private DataPackInstaller() {
    }

    public static void install() {
        Path gameDir = FabricLoader.getInstance().getGameDir();
        String levelName = "world";
        Path properties = gameDir.resolve("server.properties");
        if (Files.exists(properties)) {
            try (InputStream in = Files.newInputStream(properties)) {
                Properties p = new Properties();
                p.load(in);
                levelName = p.getProperty("level-name", "world").trim();
                if (levelName.isEmpty()) {
                    levelName = "world";
                }
            } catch (IOException e) {
                Beyond.LOGGER.warn("Could not read server.properties, assuming level-name=world: {}", e.toString());
            }
        }
        Path target = gameDir.resolve(levelName).resolve("datapacks").resolve("beyond");
        ModContainer mod = FabricLoader.getInstance().getModContainer(Beyond.MODID).orElse(null);
        if (mod == null) {
            Beyond.LOGGER.error("Own mod container missing; data pack not installed");
            return;
        }
        try {
            deleteTree(target);
            Files.createDirectories(target);
            int copied = 0;
            for (Path root : mod.getRootPaths()) {
                Path data = root.resolve("data");
                Path meta = root.resolve("pack.mcmeta");
                if (Files.exists(meta)) {
                    Files.copy(meta, target.resolve("pack.mcmeta"), StandardCopyOption.REPLACE_EXISTING);
                }
                if (!Files.isDirectory(data)) {
                    continue;
                }
                try (Stream<Path> walk = Files.walk(data)) {
                    for (Path source : (Iterable<Path>) walk::iterator) {
                        Path relative = data.relativize(source);
                        Path destination = target.resolve("data").resolve(relative.toString());
                        if (Files.isDirectory(source)) {
                            Files.createDirectories(destination);
                        } else {
                            Files.createDirectories(destination.getParent());
                            Files.copy(source, destination, StandardCopyOption.REPLACE_EXISTING);
                            copied++;
                        }
                    }
                }
            }
            Beyond.LOGGER.info("Installed data pack: {} files into {}", copied, target);
        } catch (IOException e) {
            Beyond.LOGGER.error("Could not install the data pack into {}: {}", target, e.toString());
        }
    }

    private static void deleteTree(Path dir) throws IOException {
        if (!Files.exists(dir)) {
            return;
        }
        try (Stream<Path> walk = Files.walk(dir)) {
            for (Path p : (Iterable<Path>) walk.sorted(java.util.Comparator.reverseOrder())::iterator) {
                Files.delete(p);
            }
        }
    }
}
