package dev.beyond;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.datafixers.util.Pair;
import dev.beyond.forge.Forge;
import dev.beyond.item.BeyondItem;
import dev.beyond.item.BeyondItems;
import dev.beyond.world.Sites;
import dev.beyond.world.Structures;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.permissions.Permission;
import net.minecraft.server.permissions.PermissionLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.levelgen.Heightmap;

import java.util.Collection;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Set;

/** {@code /beyond} - admin and testing commands. Level 2, like {@code /give}. */
public final class BeyondCommands {

    /**
     * Every biome the mod adds, read from the list the generator writes beside the data.
     * The command tree is built before the registries can be read, and 114 names is well
     * past what is worth keeping by hand in two places.
     */
    public static final List<String> BIOMES = loadBiomes();

    private static List<String> loadBiomes() {
        try (InputStream in = BeyondCommands.class.getResourceAsStream("/beyond-biomes.txt")) {
            if (in == null) {
                return List.of();
            }
            return new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))
                    .lines().map(String::trim).filter(line -> !line.isEmpty()).toList();
        } catch (IOException e) {
            Beyond.LOGGER.warn("could not read the biome list", e);
            return List.of();
        }
    }

    private static final Permission OP = new Permission.HasCommandLevel(PermissionLevel.GAMEMASTERS);

    private BeyondCommands() {
    }

    private static int seed(CommandSourceStack source, int radius) {
        ServerLevel end = source.getServer().getLevel(net.minecraft.world.level.Level.END);
        if (end == null) {
            source.sendFailure(Component.literal("The End is not loaded."));
            return 0;
        }
        ServerPlayer player = source.getPlayer();
        BlockPos around = player != null && player.level() == end ? player.blockPosition() : new BlockPos(0, 64, 0);
        source.sendSuccess(() -> Component.literal("Seeding the End within " + radius + " blocks of "
                + around.getX() + " " + around.getZ() + "; this loads chunks and can take a while...")
                .withStyle(ChatFormatting.GRAY), true);
        long t0 = System.currentTimeMillis();
        dev.beyond.world.Seeder.Report report = dev.beyond.world.Seeder.seed(end, around, radius, Beyond.config(),
                line -> source.sendSuccess(() -> Component.literal("  " + line).withStyle(ChatFormatting.GRAY), false));
        long seconds = (System.currentTimeMillis() - t0) / 1000;
        source.sendSuccess(() -> Component.literal("Seeded " + report.total() + " thing(s) across " + report.regions()
                + " region(s), loading " + report.chunksLoaded() + " chunk(s), in " + seconds + " s.")
                .withStyle(ChatFormatting.GREEN), true);
        for (var entry : report.built().entrySet()) {
            source.sendSuccess(() -> Component.literal(" - " + entry.getKey() + ": " + entry.getValue())
                    .withStyle(ChatFormatting.GRAY), false);
        }
        return report.total();
    }

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        LiteralArgumentBuilder<CommandSourceStack> root = Commands.literal("beyond")
                .requires(source -> source.permissions().hasPermission(OP));

        // dash - drives the wings from the console so the ability is testable without
        // a client that can glide.
        root.then(Commands.literal("dash")
                .then(Commands.argument("targets", EntityArgument.players())
                        .executes(context -> {
                            int n = 0;
                            for (ServerPlayer player : EntityArgument.getPlayers(context, "targets")) {
                                String refused = dev.beyond.mob.DashElytra.tryDash(
                                        context.getSource().getServer(), player,
                                        Beyond.config(), Beyond.tick());
                                int seconds = dev.beyond.mob.DashElytra.cooldownSeconds(
                                        context.getSource().getServer(), player, Beyond.config());
                                String line = refused == null
                                        ? player.getScoreboardName() + " dashed (" + seconds + "s cooldown)"
                                        : player.getScoreboardName() + ": " + refused;
                                context.getSource().sendSuccess(() -> Component.literal(line), false);
                                n += refused == null ? 1 : 0;
                            }
                            return n;
                        })));

        // give
        var targets = Commands.argument("targets", EntityArgument.players());
        for (BeyondItem item : BeyondItems.ALL) {
            targets.then(Commands.literal(item.id()).executes(context -> {
                Collection<ServerPlayer> players = EntityArgument.getPlayers(context, "targets");
                for (ServerPlayer player : players) {
                    ItemStack stack = BeyondItems.create(item, 1);
                    if (!player.getInventory().add(stack)) {
                        player.drop(stack, false);
                    }
                }
                context.getSource().sendSuccess(() -> Component.literal("Gave ").append(item.displayName())
                        .append(Component.literal(" to " + players.size() + " player(s)").withStyle(ChatFormatting.GRAY)), true);
                return players.size();
            }));
        }
        root.then(Commands.literal("give").then(targets));

        // tp <biome>
        LiteralArgumentBuilder<CommandSourceStack> tp = Commands.literal("tp");
        for (String biome : BIOMES) {
            tp.then(Commands.literal(biome).executes(context -> teleportToBiome(context.getSource(), biome)));
        }
        // tp structure <id>: the nearest jigsaw structure of that kind (castles, cities, monuments)
        tp.then(Commands.literal("structure").then(Commands.argument("id", com.mojang.brigadier.arguments.StringArgumentType.word())
                .executes(context -> {
                    ServerPlayer player = context.getSource().getPlayerOrException();
                    net.minecraft.server.level.ServerLevel end = context.getSource().getServer().getLevel(net.minecraft.world.level.Level.END);
                    if (end == null) {
                        context.getSource().sendFailure(Component.literal("The End is not loaded."));
                        return 0;
                    }
                    String id = com.mojang.brigadier.arguments.StringArgumentType.getString(context, "id");
                    if (dev.beyond.world.Castles.isCastle(id)) {
                        Sites.Site castle = Beyond.sites().nearest(id,
                                player.level() == end ? player.blockPosition() : new net.minecraft.core.BlockPos(0, 64, 0));
                        if (castle == null) {
                            context.getSource().sendFailure(Component.literal("No " + id + " has been built yet. Castles appear around players in the End."));
                            return 0;
                        }
                        player.teleportTo(end, castle.x + 0.5, castle.y + 1, castle.z + 0.5, java.util.Set.of(), player.getYRot(), player.getXRot(), false);
                        context.getSource().sendSuccess(() -> Component.literal("Teleported to " + id + " at " + castle.x + " " + castle.y + " " + castle.z), false);
                        return 1;
                    }
                    net.minecraft.resources.ResourceKey<net.minecraft.world.level.levelgen.structure.Structure> key =
                            net.minecraft.resources.ResourceKey.create(net.minecraft.core.registries.Registries.STRUCTURE,
                                    net.minecraft.resources.Identifier.parse(id.contains(":") ? id : Beyond.MODID + ":" + id));
                    var holder = end.registryAccess().lookupOrThrow(net.minecraft.core.registries.Registries.STRUCTURE).get(key);
                    if (holder.isEmpty()) {
                        context.getSource().sendFailure(Component.literal("No structure called " + id + "."));
                        return 0;
                    }
                    net.minecraft.core.BlockPos from = player.level() == end ? player.blockPosition() : new net.minecraft.core.BlockPos(0, 64, 0);
                    var found = end.getChunkSource().getGenerator().findNearestMapStructure(end,
                            net.minecraft.core.HolderSet.direct(holder.get()), from, 100, false);
                    if (found == null) {
                        context.getSource().sendFailure(Component.literal("No " + id + " within 1,600 blocks."));
                        return 0;
                    }
                    net.minecraft.core.BlockPos start = found.getFirst();
                    // The structure's start chunk can sit over the void; land on the highest
                    // block within its footprint instead, once those chunks exist.
                    net.minecraft.core.BlockPos at = start;
                    int y = 0;
                    for (int dx = -48; dx <= 48; dx += 8) {
                        for (int dz = -48; dz <= 48; dz += 8) {
                            int px = start.getX() + dx, pz = start.getZ() + dz;
                            end.getChunk(px >> 4, pz >> 4);
                            int h = end.getHeight(net.minecraft.world.level.levelgen.Heightmap.Types.MOTION_BLOCKING, px, pz);
                            if (h > y) {
                                y = h;
                                at = new net.minecraft.core.BlockPos(px, h, pz);
                            }
                        }
                    }
                    if (y < 8) {
                        context.getSource().sendFailure(Component.literal("Found " + id + " at " + start.getX() + " " + start.getZ()
                                + " but no ground near it yet; try again in a moment."));
                        return 0;
                    }
                    final net.minecraft.core.BlockPos landing = at;
                    final int landingY = y;
                    player.teleportTo(end, at.getX() + 0.5, y + 1, at.getZ() + 0.5, java.util.Set.of(), player.getYRot(), player.getXRot(), false);
                    context.getSource().sendSuccess(() -> Component.literal("Teleported to " + id + " at "
                            + landing.getX() + " " + landingY + " " + landing.getZ()), false);
                    return 1;
                })));
        // tp river: the nearest carved river
        tp.then(Commands.literal("river").executes(context -> {
            ServerPlayer player = context.getSource().getPlayerOrException();
            net.minecraft.server.level.ServerLevel end = context.getSource().getServer().getLevel(net.minecraft.world.level.Level.END);
            Sites.Site site = Beyond.sites().nearest(dev.beyond.world.Rivers.TYPE,
                    player.level() == end ? player.blockPosition() : new net.minecraft.core.BlockPos(0, 64, 0));
            if (end == null || site == null) {
                context.getSource().sendFailure(Component.literal("No river has been carved yet. Rivers appear around players in the End."));
                return 0;
            }
            player.teleportTo(end, site.x + 0.5, site.y + 2, site.z + 0.5, java.util.Set.of(), player.getYRot(), player.getXRot(), false);
            context.getSource().sendSuccess(() -> Component.literal("Teleported to a river at " + site.x + " " + site.y + " " + site.z), false);
            return 1;
        }));
        root.then(tp);

        // locate / build <structure>
        LiteralArgumentBuilder<CommandSourceStack> locate = Commands.literal("locate");
        LiteralArgumentBuilder<CommandSourceStack> build = Commands.literal("build");
        build.then(Commands.literal("river").executes(context -> {
            ServerPlayer player = context.getSource().getPlayerOrException();
            net.minecraft.server.level.ServerLevel level = (net.minecraft.server.level.ServerLevel) player.level();
            net.minecraft.core.BlockPos here = player.blockPosition();
            int surface = dev.beyond.world.Terrain.ground(level, here.getX(), here.getZ());
            int carved = dev.beyond.world.Rivers.build(level, new net.minecraft.core.BlockPos(here.getX(), surface - 1, here.getZ()),
                    net.minecraft.util.RandomSource.create());
            if (carved == 0) {
                context.getSource().sendFailure(Component.literal("No room for a river here: it needs a stretch of island to run along."));
                return 0;
            }
            Sites.Site site = new Sites.Site();
            site.type = dev.beyond.world.Rivers.TYPE; site.x = here.getX(); site.y = surface - 1; site.z = here.getZ();
            Beyond.sites().all().add(site);
            context.getSource().sendSuccess(() -> Component.literal("Carved a river of " + carved + " blocks from here."), true);
            return 1;
        }));
        for (String type : dev.beyond.world.Castles.TYPES) {
            build.then(Commands.literal(type).executes(context -> {
                ServerPlayer player = context.getSource().getPlayerOrException();
                net.minecraft.server.level.ServerLevel level = (net.minecraft.server.level.ServerLevel) player.level();
                net.minecraft.core.BlockPos here = player.blockPosition();
                net.minecraft.core.BlockPos placed = dev.beyond.world.Castles.place(level, type, here.getX(), here.getZ(),
                        net.minecraft.util.RandomSource.create(), true);
                if (placed == null) {
                    context.getSource().sendFailure(Component.literal("Could not build a " + type + " here."));
                    return 0;
                }
                Sites.Site site = new Sites.Site();
                site.type = type; site.x = placed.getX(); site.y = placed.getY(); site.z = placed.getZ();
                Beyond.sites().all().add(site);
                context.getSource().sendSuccess(() -> Component.literal("Built " + type + " at "
                        + placed.getX() + " " + placed.getY() + " " + placed.getZ()), true);
                return 1;
            }));
        }
        // The two code-built boss halls: build one here, or find the nearest.
        for (String type : dev.beyond.world.Halls2.TYPES) {
            build.then(Commands.literal(type).executes(context -> {
                ServerPlayer player = context.getSource().getPlayerOrException();
                ServerLevel level = (ServerLevel) player.level();
                BlockPos here = player.blockPosition();
                int surface = dev.beyond.world.Terrain.ground(level, here.getX(), here.getZ());
                Sites.Site site = Beyond.sites().placeHall(level, type, new BlockPos(here.getX(), surface, here.getZ()),
                        RandomSource.create());
                context.getSource().sendSuccess(() -> Component.literal("Built " + type + "; its dais is at "
                        + site.x + " " + site.y + " " + site.z), true);
                return 1;
            }));
            locate.then(Commands.literal(type).executes(context -> {
                ServerPlayer player = context.getSource().getPlayerOrException();
                Sites.Site site = Beyond.sites().nearest(type, player.blockPosition());
                if (site == null) {
                    context.getSource().sendFailure(Component.literal("No " + type + " has been built yet."));
                    return 0;
                }
                context.getSource().sendSuccess(() -> Component.literal("Nearest " + type + ": dais at "
                        + site.x + " " + site.y + " " + site.z + "  ("
                        + (int) Math.sqrt(player.blockPosition().distSqr(site.pos())) + " blocks)"), false);
                return 1;
            }));
        }
        for (String type : Structures.TYPES) {
            locate.then(Commands.literal(type).executes(context -> {
                ServerPlayer player = context.getSource().getPlayerOrException();
                Sites.Site site = Beyond.sites().nearest(type, player.blockPosition());
                if (site == null) {
                    context.getSource().sendFailure(Component.literal("No " + type + " has generated yet."));
                    return 0;
                }
                context.getSource().sendSuccess(() -> Component.literal("Nearest " + type + ": "
                        + site.x + " " + site.y + " " + site.z + "  ("
                        + (int) Math.sqrt(player.blockPosition().distSqr(site.pos())) + " blocks)"), false);
                return 1;
            }));
            build.then(Commands.literal(type).executes(context -> {
                ServerPlayer player = context.getSource().getPlayerOrException();
                // Eight blocks ahead, not underfoot: a structure built around the player
                // entombs them in it.
                var look = player.getLookAngle();
                double len = Math.max(0.01, Math.hypot(look.x, look.z));
                BlockPos ahead = player.blockPosition().offset(
                        (int) Math.round(look.x / len * 8), -1, (int) Math.round(look.z / len * 8));
                Sites.Site site = Beyond.sites().place((ServerLevel) player.level(), type,
                        ahead, RandomSource.create());
                context.getSource().sendSuccess(() -> Component.literal("Built " + type + " at "
                        + site.x + " " + site.y + " " + site.z), true);
                return 1;
            }));
        }
        root.then(locate).then(build);

        // seed [radius] - a world generated before the mod gets everything it never grew:
        // the code-placed sites through their own placement, the jigsaw cities and
        // monuments at the cells their structure sets would have chosen.
        root.then(Commands.literal("seed")
                .executes(context -> seed(context.getSource(), 1500))
                .then(Commands.argument("radius", com.mojang.brigadier.arguments.IntegerArgumentType.integer(100, 10000))
                        .executes(context -> seed(context.getSource(),
                                com.mojang.brigadier.arguments.IntegerArgumentType.getInteger(context, "radius")))));

        // boss <which> - wakes a boss where the player stands, for a fight without the walk.
        LiteralArgumentBuilder<CommandSourceStack> boss = Commands.literal("boss");
        boss.then(Commands.literal("hollow_king").executes(context -> {
            ServerPlayer player = context.getSource().getPlayerOrException();
            boolean woke = dev.beyond.mob.Boss.summon((ServerLevel) player.level(), player.blockPosition().relative(player.getDirection(), 4), player, Beyond.config());
            return woke ? 1 : 0;
        }));
        boss.then(Commands.literal("void_warden").executes(context -> {
            ServerPlayer player = context.getSource().getPlayerOrException();
            boolean woke = dev.beyond.mob.VoidWarden.summon((ServerLevel) player.level(), player.blockPosition().relative(player.getDirection(), 4), player, Beyond.config());
            return woke ? 1 : 0;
        }));
        boss.then(Commands.literal("gale_sovereign").executes(context -> {
            ServerPlayer player = context.getSource().getPlayerOrException();
            boolean woke = dev.beyond.mob.GaleSovereign.summon((ServerLevel) player.level(), player.blockPosition().relative(player.getDirection(), 4), player, Beyond.config());
            return woke ? 1 : 0;
        }));
        root.then(boss);

        root.then(Commands.literal("forge").executes(context -> {
            Forge.open(context.getSource().getPlayerOrException());
            return 1;
        }));
        root.then(Commands.literal("sites").executes(context -> {
            List<Sites.Site> all = Beyond.sites().all();
            context.getSource().sendSuccess(() -> Component.literal(all.size() + " structure(s) placed"), false);
            for (Sites.Site site : all) {
                context.getSource().sendSuccess(() -> Component.literal(" - " + site.type + " at "
                        + site.x + " " + site.y + " " + site.z).withStyle(ChatFormatting.GRAY), false);
            }
            return all.size();
        }));
        root.then(Commands.literal("biomes").executes(context -> {
            for (String biome : BIOMES) {
                context.getSource().sendSuccess(() -> Component.literal(" - beyond:" + biome).withStyle(ChatFormatting.GRAY), false);
            }
            return BIOMES.size();
        }));
        root.then(Commands.literal("reload").executes(context -> {
            Beyond.reloadConfig();
            context.getSource().sendSuccess(() -> Component.literal(
                    "Beyond the End config reloaded; carried gear re-stats within a second.").withStyle(ChatFormatting.GREEN), true);
            return 1;
        }));

        // The answers to the music question on join; open to everyone.
        dispatcher.register(Commands.literal("endmusic")
                .executes(context -> { dev.beyond.Beyond.pack().install(context.getSource().getPlayerOrException(), dev.beyond.Beyond.config()); return 1; })
                .then(Commands.literal("install").executes(context -> { dev.beyond.Beyond.pack().install(context.getSource().getPlayerOrException(), dev.beyond.Beyond.config()); return 1; }))
                .then(Commands.literal("later").executes(context -> { dev.beyond.Beyond.pack().later(context.getSource().getPlayerOrException()); return 1; }))
                .then(Commands.literal("never").executes(context -> { dev.beyond.Beyond.pack().never(context.getSource().getPlayerOrException()); return 1; })));
        // For everyone: the smelter screen without building the shape.
        dispatcher.register(Commands.literal("forge").executes(context -> {
            Forge.open(context.getSource().getPlayerOrException());
            return 1;
        }));
        // For everyone, so it cannot hang under /beyond, which needs op.
        dispatcher.register(Commands.literal("throne").executes(context -> {
            net.minecraft.server.level.ServerPlayer player = context.getSource().getPlayerOrException();
            net.minecraft.server.level.ServerLevel end = context.getSource().getServer().getLevel(net.minecraft.world.level.Level.END);
            if (end == null || player.level() != end) {
                context.getSource().sendFailure(Component.literal("The Hollow King waits in the End."));
                return 0;
            }
            net.minecraft.core.BlockPos throne = dev.beyond.world.BossLocator.find(end, player.blockPosition());
            if (throne == null) {
                context.getSource().sendFailure(Component.literal("No Throne City within 1,600 blocks."));
                return 0;
            }
            context.getSource().sendSuccess(() -> Component.literal("The Hollow King's throne: ")
                    .withStyle(ChatFormatting.LIGHT_PURPLE)
                    .append(Component.literal(throne.getX() + " " + throne.getZ() + ", "
                            + dev.beyond.world.BossLocator.describe(player.blockPosition(), throne))
                            .withStyle(ChatFormatting.WHITE)), false);
            return 1;
        }));
        dispatcher.register(root);
    }

    private static int teleportToBiome(CommandSourceStack source, String biome)
            throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        ServerPlayer player = source.getPlayerOrException();
        MinecraftServer server = source.getServer();
        ServerLevel end = server.getLevel(Level.END);
        if (end == null) {
            source.sendFailure(Component.literal("The End is not loaded."));
            return 0;
        }
        ResourceKey<Biome> key = ResourceKey.create(Registries.BIOME, Identifier.parse(Beyond.MODID + ":" + biome));
        BlockPos origin = player.level() == end ? player.blockPosition() : new BlockPos(0, 64, 0);
        Pair<BlockPos, Holder<Biome>> found = end.findClosestBiome3d(h -> h.is(key), origin, 6400, 32, 64);
        if (found == null) {
            source.sendFailure(Component.literal("No " + biome + " within 6400 blocks."));
            return 0;
        }
        BlockPos at = found.getFirst();
        // The biome is a climate region, and most of a region is void between islands. Look
        // around the match for a column with ground that is still in the biome.
        BlockPos landing = null;
        outer:
        for (int r = 0; r <= 160; r += 8) {
            for (int dx = -r; dx <= r; dx += 8) {
                for (int dz = -r; dz <= r; dz += 8) {
                    if (Math.abs(dx) != r && Math.abs(dz) != r) {
                        continue;
                    }
                    int x = at.getX() + dx;
                    int z = at.getZ() + dz;
                    int h = end.getHeight(Heightmap.Types.MOTION_BLOCKING, x, z);
                    if (h > end.getMinY() + 2 && end.getBiome(new BlockPos(x, h, z)).is(key)) {
                        landing = new BlockPos(x, h, z);
                        break outer;
                    }
                }
            }
        }
        boolean ground = landing != null;
        if (!ground) {
            // Nothing to stand on within reach: a small end stone shard to land on, marked as
            // such. The biome finder samples every 32 blocks and the block-level lookup jitters
            // the edges, so the shard goes on a column that actually reads as the biome.
            landing = new BlockPos(at.getX(), 64, at.getZ());
            search:
            for (int r = 0; r <= 96; r += 4) {
                for (int dx = -r; dx <= r; dx += 4) {
                    for (int dz = -r; dz <= r; dz += 4) {
                        if (Math.abs(dx) != r && Math.abs(dz) != r) {
                            continue;
                        }
                        BlockPos candidate = new BlockPos(at.getX() + dx, 64, at.getZ() + dz);
                        if (end.getBiome(candidate).is(key)) {
                            landing = candidate;
                            break search;
                        }
                    }
                }
            }
            for (int dx = -2; dx <= 2; dx++) {
                for (int dz = -2; dz <= 2; dz++) {
                    end.setBlock(landing.offset(dx, -1, dz), net.minecraft.world.level.block.Blocks.END_STONE.defaultBlockState(), 3);
                }
            }
        }
        final BlockPos dest = landing;
        final boolean onGround = ground;
        player.teleportTo(end, dest.getX() + 0.5, dest.getY() + 1, dest.getZ() + 0.5, Set.of(), player.getYRot(), player.getXRot(), false);
        source.sendSuccess(() -> Component.literal("Teleported to beyond:" + biome + " at " + dest.getX() + " "
                + (dest.getY() + 1) + " " + dest.getZ() + (onGround ? "" : " (on a landing shard over the void)")), false);
        return 1;
    }
}
