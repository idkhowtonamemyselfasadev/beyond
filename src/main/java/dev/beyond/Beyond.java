package dev.beyond;

import com.mojang.brigadier.CommandDispatcher;
import dev.beyond.forge.Forge;
import dev.beyond.item.BeyondItem;
import dev.beyond.item.BeyondItems;
import dev.beyond.mob.Boss;
import dev.beyond.mob.DashElytra;
import dev.beyond.mob.Mobs;
import dev.beyond.world.Portal;
import dev.beyond.world.Sites;
import net.fabricmc.api.DedicatedServerModInitializer;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.BlockHitResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Beyond the End - a new End dimension for a vanilla client.
 *
 * <p>Fourteen biomes, seven structures, a three-tier metal progression, new creatures and a
 * way home, none of which asks the player to install anything. The biomes, terrain, flora and
 * loot are data inside this jar; the abilities, the forge, the structures, the mobs and the
 * portal are here in Java.
 *
 * <p>Server side only and dependency free: the hooks it needs are its own mixins, so the mod
 * loads on any 1.21.11 Fabric server with nothing else in {@code mods/}.
 */
public final class Beyond implements DedicatedServerModInitializer {

    public static final Logger LOGGER = LoggerFactory.getLogger("Beyond");
    public static final String MODID = "beyond";

    private static Beyond INSTANCE;
    private static BeyondConfig config = new BeyondConfig();
    /** Bumped on every config load; items carry the generation they were stamped at. */
    private static int generation;
    private static MinecraftServer server;

    private final Cooldowns cooldowns = new Cooldowns();
    private final Sites sites = new Sites();
    private final dev.beyond.world.BossLocator locator = new dev.beyond.world.BossLocator();
    private final dev.beyond.pack.PackOffer pack = new dev.beyond.pack.PackOffer();

    public static dev.beyond.pack.PackOffer pack() {
        return INSTANCE.pack;
    }

    public static void onPlayerJoin(ServerPlayer player) {
        if (INSTANCE != null && server != null) {
            INSTANCE.pack.onJoin(player, config);
        }
    }
    private boolean started;
    private long tick;

    public static BeyondConfig config() {
        return config;
    }

    public static int generation() {
        return generation;
    }

    public static Cooldowns cooldowns() {
        return INSTANCE.cooldowns;
    }

    public static Sites sites() {
        return INSTANCE.sites;
    }

    /** Ticks since the server started, for anything on a cooldown. */
    public static long tick() {
        return INSTANCE == null ? 0L : INSTANCE.tick;
    }

    public static MinecraftServer server() {
        return server;
    }

    public static void reloadConfig() {
        config = BeyondConfig.load();
        generation++;
    }

    @Override
    public void onInitializeServer() {
        reloadConfig();
        INSTANCE = this;
        DataPackInstaller.install();
        BeyondItems.init();
        LOGGER.info("Beyond the End ready: {} biomes in data, {} items, {} forge recipes, {} structures",
                BeyondCommands.BIOMES.size(), BeyondItems.ALL.size(), Forge.RECIPES.size(),
                dev.beyond.world.Structures.TYPES.size());
    }

    // ---------------------------------------------------------------- from the mixins

    public static void onCommandsBuilt(CommandDispatcher<CommandSourceStack> dispatcher) {
        if (INSTANCE != null) {
            BeyondCommands.register(dispatcher);
            LOGGER.info("Registered /beyond");
        }
    }

    public static void onServerTick(MinecraftServer minecraftServer) {
        if (INSTANCE == null) {
            return;
        }
        server = minecraftServer;
        Beyond self = INSTANCE;
        if (!self.started) {
            self.started = true;
            self.sites.load(minecraftServer);
            self.pack.load(minecraftServer);
        }
        self.tick++;
        self.cooldowns.onTick();
        if (self.tick % Math.max(1, config.sweep_interval_ticks) == 0) {
            BeyondItems.sweep(minecraftServer, config, generation);
        }
        if (self.tick % 20 == 0) {
            self.sites.onTick(minecraftServer, config);
        }
        Boss.onTick(minecraftServer, config, self.tick);
        dev.beyond.mob.BossBars.onTick(minecraftServer, config, self.tick);
        self.locator.onTick(minecraftServer, config, self.tick);
        for (ServerPlayer player : minecraftServer.getPlayerList().getPlayers()) {
            DashElytra.onTick(minecraftServer, player, config, self.tick);
        }
    }

    public static void onServerStopping() {
        if (INSTANCE != null) {
            INSTANCE.sites.save();
        }
    }

    public static void onPlayerDisconnect(ServerPlayer player) {
        if (INSTANCE != null) {
            INSTANCE.locator.forget(player.getUUID());
            dev.beyond.mob.BossBars.forget(player);
        }
        if (INSTANCE != null) {
            INSTANCE.cooldowns.forget(player.getUUID());
            DashElytra.forget(player.getUUID());
        }
    }

    /** A boss dies here, and what it carried comes off. */
    public static void onLivingDeath(LivingEntity dead) {
        if (INSTANCE != null && dead.level() instanceof ServerLevel level) {
            Boss.onDeath(level, dead);
            dev.beyond.mob.VoidWarden.onDeath(level, dead);
            dev.beyond.mob.GaleSovereign.onDeath(level, dead);
        }
    }

    public static void onEntityAdded(ServerLevel level, Entity entity) {
        if (INSTANCE != null && config.mobs_enabled) {
            Mobs.dress(level, entity, config);
        }
    }

    /** @return true if the click was consumed by the mod */
    public static boolean onUseBlock(ServerPlayer player, ServerLevel level, ItemStack stack,
                                     InteractionHand hand, BlockHitResult hit) {
        if (INSTANCE == null || hand != InteractionHand.MAIN_HAND) {
            return false;
        }
        // The dragon egg on a Throne City dais is the King's alarm clock. The click is
        // consumed either way: vanilla's egg teleports itself somewhere random when you
        // use it, so letting the click through once the King is already awake would lose
        // the throne its alarm clock for good.
        if (level.getBlockState(hit.getBlockPos()).is(net.minecraft.world.level.block.Blocks.DRAGON_EGG)) {
            Boss.summon(level, hit.getBlockPos(), player, config);
            return true;
        }
        // The shrieker in a Void Crypt and the rod on a Storm Spire are the other two alarm
        // clocks - only the recorded dais block, so a shrieker somebody carried in is just
        // a shrieker.
        Sites.Site hall = INSTANCE.sites.hallAt(hit.getBlockPos());
        if (hall != null) {
            if (dev.beyond.world.Halls2.VOID_CRYPT.equals(hall.type)) {
                dev.beyond.mob.VoidWarden.summon(level, hit.getBlockPos(), player, config);
            } else {
                dev.beyond.mob.GaleSovereign.summon(level, hit.getBlockPos(), player, config);
            }
            return true;
        }
        // The forge: an ordinary blast furnace on the right foundation opens ours instead.
        if (Forge.isForge(level, hit.getBlockPos())) {
            Forge.open(player);
            return true;
        }
        // A portal pedestal with a crystal in hand.
        Sites.Site site = INSTANCE.sites.portalAt(hit.getBlockPos());
        if (site != null && Portal.onPedestalUse(player, level, site, hit.getBlockPos(), stack, config)) {
            INSTANCE.sites.save();
            return true;
        }
        return onUseItem(player, level, stack, hand);
    }

    /** @return true if an item ability fired */
    public static boolean onUseItem(ServerPlayer player, ServerLevel level, ItemStack stack, InteractionHand hand) {
        if (INSTANCE == null || hand != InteractionHand.MAIN_HAND) {
            return false;
        }
        BeyondItem item = BeyondItems.of(stack);
        return item != null && item.onRightClick(player, stack, config);
    }

    public static void onLivingHurt(LivingEntity victim, DamageSource source, float amount) {
        if (INSTANCE == null || Hurt.isAbilityDamage()) {
            return;
        }
        if (config.mobs_enabled) {
            Mobs.onHurt(victim, source, config);
        }
        if (source.getDirectEntity() instanceof ServerPlayer attacker && attacker != victim) {
            ItemStack held = attacker.getMainHandItem();
            BeyondItem item = BeyondItems.of(held);
            if (item != null) {
                item.onHit(attacker, victim, held, config);
            }
        }
    }

    public static void log(String format, Object... args) {
        if (config.log_events) {
            LOGGER.info("EVENT " + format, args);
        }
    }
}
