package dev.beyond;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import net.fabricmc.loader.api.FabricLoader;

import java.io.Reader;
import java.io.Writer;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Every tunable number, in {@code config/beyond.json}.
 *
 * <p>Damage, speed and armour are written as the totals a player sees on the tooltip. The
 * player's own base (1.0 damage, 4.0 speed) is subtracted when the modifier is built.
 * {@code /beyond reload} re-stats gear that already exists in inventories.
 */
public final class BeyondConfig {

    /** One tier of gear. Values are tooltip totals. */
    public static final class Tier {
        public double sword_damage, sword_speed;
        public double axe_damage, axe_speed;
        public double pickaxe_damage, shovel_damage, hoe_damage, tool_speed, hoe_speed;
        public double helmet, chestplate, leggings, boots, toughness, knockback_resistance;
        /** Extra block break speed on tools, as a fraction: 0.25 is a quarter faster. */
        public double mining_bonus;

        public Tier() {
        }

        Tier(double swordD, double axeD, double axeS, double pickD, double shovelD, double hoeD, double hoeS,
             double helmet, double chest, double legs, double boots, double tough, double kb, double mining) {
            this.sword_damage = swordD; this.sword_speed = 1.6;
            this.axe_damage = axeD; this.axe_speed = axeS;
            this.pickaxe_damage = pickD; this.shovel_damage = shovelD; this.hoe_damage = hoeD;
            this.tool_speed = 1.2; this.hoe_speed = hoeS;
            this.helmet = helmet; this.chestplate = chest; this.leggings = legs; this.boots = boots;
            this.toughness = tough; this.knockback_resistance = kb; this.mining_bonus = mining;
        }
    }

    // Iron is 6/9/4/4.5/1 and 2/6/5/2 toughness 0. Diamond 7/9/5/5.5/1, 3/8/6/3 toughness 2.
    // Netherite 8/10/6/6.5/1, 3/8/6/3 toughness 3 knockback 0.1.
    // Weapon damage is about 60% of what it was (Tim: "10 to 6", 2026-09-12): the top sword
    // does 6, below vanilla iron. The tiers' edge is armour, mining speed and, for
    // Aeternium, not burning - not hitting hard.
    public Tier thallasium = new Tier(4.0, 5.5, 0.9, 3.0, 3.0, 1.0, 3.0, 2.5, 7.0, 5.5, 2.5, 1.0, 0.0, 0.10);
    public Tier terminite = new Tier(5.0, 6.0, 1.0, 3.5, 3.5, 1.0, 4.0, 3.0, 8.0, 6.0, 3.0, 2.5, 0.05, 0.20);
    public Tier aeternium = new Tier(6.0, 7.0, 1.0, 4.0, 4.0, 1.0, 4.0, 3.5, 9.0, 7.0, 3.5, 4.0, 0.15, 0.35);

    // ------------------------------------------------------------------- abilities
    public double chorus_lantern_range = 8.0;
    public int chorus_lantern_cooldown_ticks = 100;
    public double crystal_focus_radius = 20.0;
    public int crystal_focus_glow_ticks = 200;
    public int crystal_focus_cooldown_ticks = 400;
    public int amber_heart_regen_ticks = 160;
    public int amber_heart_cooldown_ticks = 900;
    public int veil_invisibility_ticks = 400;
    public int veil_cooldown_ticks = 1200;
    public int tidal_lens_ticks = 1200;
    public int tidal_lens_cooldown_ticks = 1800;
    public int starfall_shard_ticks = 600;
    public int starfall_shard_cooldown_ticks = 600;
    public int end_fish_nutrition = 6;
    public double end_fish_saturation = 0.8;

    // ------------------------------------------------------------------ structures
    public boolean structures_enabled = true;
    /** Rivers across the islands, one candidate per region of this many chunks. */
    public boolean rivers_enabled = true;
    public int river_spacing_chunks = 10;
    /** Castles: one candidate per region of this many chunks, built only on a big enough island. */
    public boolean castles_enabled = true;
    public int castle_spacing_chunks = 40;
    /**
     * Every castle is manned when it is built: persistent, named vanilla mobs on its walls
     * and in its courtyard (sentinels, knights, tide guards, and wraiths over the towers).
     */
    public boolean castle_garrison_enabled = true;
    public int castle_garrison = 10;
    /** Mark the nearest Throne City on every player's locator bar while they are in the End. */
    public boolean boss_marker = true;
    /** One structure candidate per square of this many chunks, in biomes that host one. */
    public int structure_spacing_chunks = 12;
    /** Eternal Portals are rarer, and never two neighbours. */
    public int portal_spacing_chunks = 40;
    /** How many regions around each player are considered every second. */
    public int structure_scan_regions = 2;

    // ------------------------------------------------------------------------ mobs
    public boolean mobs_enabled = true;
    public int shadow_walker_blindness_ticks = 60;
    public double shadow_walker_health = 30.0;
    public double shadow_walker_speed = 0.32;
    public double shadow_walker_damage = 5.0;

    // ------------------------------------------------------------------------ misc
    public int sweep_interval_ticks = 5;
    /**
     * The boss halls cannot be broken: not by a survival player, not by an explosion, not
     * by a block-breaking mob. Creative mode is exempt so an operator can still edit one,
     * and heads and skulls (a dragon head, a wither skeleton skull) can always be taken.
     */
    public boolean protect_boss_halls = true;
    public boolean log_events = false;

    // -------------------------------------------------------------- resource pack
    /** The End music pack. Required: the vanilla download dialog on join, a kick on refusal. */
    public boolean pack_required = true;
    public String pack_kick_message = "This server needs its resource pack. Click Yes on the download prompt, or set Server Resource Packs to Enabled in the server's edit screen.";
    /** With pack_required off: ask in chat on join instead. */
    public boolean pack_offer_on_join = true;
    /** A direct download link to the pack zip. Empty disables the pack entirely. */
    /** The pack (3D models, armour, music) as released on GitHub; pack/build_pack.py prints the sha1. */
    public static final String PACK_URL = "https://github.com/idkhowtonamemyselfasadev/beyond/releases/download/v1.1.0/BeyondTheEnd-Pack.zip";
    public static final String PACK_SHA1 = "970e1fda638b6590e2981a60059ec56f44aa2673";
    public String pack_url = PACK_URL;
    public String pack_sha1 = PACK_SHA1;
    public String pack_offer_message = "This server has 3D items, armour and music for the End. Want them?";

    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

    private static Path path() {
        return FabricLoader.getInstance().getConfigDir().resolve("beyond.json");
    }

    /** Bumped when defaults change in a way an existing file should pick up. */
    private static final int CONFIG_VERSION = 3;
    public int config_version = CONFIG_VERSION;

    public static BeyondConfig load() {
        Path file = path();
        if (!Files.exists(file)) {
            BeyondConfig fresh = new BeyondConfig();
            fresh.save();
            return fresh;
        }
        try (Reader reader = Files.newBufferedReader(file)) {
            BeyondConfig loaded = GSON.fromJson(reader, BeyondConfig.class);
            if (loaded == null) {
                return new BeyondConfig();
            }
            // A file written by an older build carries the old dash cooldowns (30 s / 20 s)
            // and none of the new keys. Retune those two and write the file back so the new
            // keys appear in it with their defaults; a server owner who set the dash to
            // something else keeps their number.
            boolean rewrite = loaded.config_version < CONFIG_VERSION;
            if (rewrite && loaded.dash_cooldown_seconds == 30 && loaded.dash_cooldown_seconds_fast == 20) {
                loaded.dash_cooldown_seconds = 10;
                loaded.dash_cooldown_seconds_fast = 7;
            }
            // Version 3 also brought the released pack: a file with no pack set gets it.
            if (loaded.config_version < 3 && (loaded.pack_url == null || loaded.pack_url.isBlank())) {
                loaded.pack_url = PACK_URL;
                loaded.pack_sha1 = PACK_SHA1;
            }
            // Version 3: weapon damage came down to the base metal's. A file still carrying
            // the old numbers gets the new ones; a hand-tuned file keeps its own.
            if (loaded.config_version < 3) {
                BeyondConfig fresh = new BeyondConfig();
                for (Tier[] pair : new Tier[][] {{loaded.thallasium, fresh.thallasium}, {loaded.terminite, fresh.terminite}, {loaded.aeternium, fresh.aeternium}}) {
                    Tier old = pair[0], now = pair[1];
                    if (old == null) {
                        continue;
                    }
                    double[] was = old == loaded.thallasium ? new double[] {7.0, 9.5, 4.5, 5.0, 1.0}
                            : old == loaded.terminite ? new double[] {8.0, 10.0, 5.5, 6.0, 1.0} : new double[] {9.5, 11.0, 6.5, 7.0, 1.5};
                    if (old.sword_damage == was[0]) old.sword_damage = now.sword_damage;
                    if (old.axe_damage == was[1]) old.axe_damage = now.axe_damage;
                    if (old.pickaxe_damage == was[2]) old.pickaxe_damage = now.pickaxe_damage;
                    if (old.shovel_damage == was[3]) old.shovel_damage = now.shovel_damage;
                    if (old.hoe_damage == was[4]) old.hoe_damage = now.hoe_damage;
                }
            }
            if (rewrite) {
                loaded.config_version = CONFIG_VERSION;
                loaded.save();
            }
            return loaded;
        } catch (Exception e) {
            Beyond.LOGGER.error("Could not read {}, using defaults: {}", file, e.toString());
            return new BeyondConfig();
        }
    }

    public void save() {
        Path file = path();
        try {
            Files.createDirectories(file.getParent());
            try (Writer writer = Files.newBufferedWriter(file)) {
                GSON.toJson(this, writer);
            }
        } catch (Exception e) {
            Beyond.LOGGER.error("Could not write {}: {}", file, e.toString());
        }
    }

    // --- The Hollow King, and the wings he is carrying ----------------------------
    /** The boss's health. A wither is 300; this is meant to be a long fight. */
    public double hollow_king_health = 900.0;
    /** Armour points, so chip damage does not do the job. */
    public double hollow_king_armor = 12.0;
    public double hollow_king_speed = 0.7;
    /** Health it mends per second below a third, unless you keep hitting it. */
    public double hollow_king_regen = 3.0;
    /** Shulkers and endermites it calls below two thirds. */
    public int hollow_king_guards = 4;
    /** Seconds between dashes on the Wings of the Hollow King. Ten: the wings are for flying. */
    public int dash_cooldown_seconds = 10;
    /** ...and with Fast Fly on them. */
    public int dash_cooldown_seconds_fast = 7;
    /** How hard a dash throws you. */
    public double dash_strength = 2.2;

    /** The Gale Rod's upward shove, in blocks per tick. */
    public double gale_rod_lift = 1.5;
    /** And how long before it will do it again. Twenty seconds. */
    public int gale_rod_cooldown_ticks = 400;

    // --- The Void Warden and the Gale Sovereign, and their halls --------------------
    /** Boss halls (a Void Crypt or a Storm Spire) grow on the islands like the castles do. */
    public boolean boss_halls_enabled = true;
    /** One hall candidate per region of this many chunks. */
    public int hall_spacing_chunks = 48;
    /** The Void Warden: a warden with boss health, woken at the Void Crypt's shrieker. */
    public double void_warden_health = 600.0;
    public double void_warden_armor = 8.0;
    /** Health it mends every two seconds below a third, unless you keep hitting it. */
    public double void_warden_regen = 2.0;
    /** Void Mites it calls below two thirds. */
    public int void_warden_mites = 3;
    /** The Gale Sovereign: a breeze with boss health, woken at the Storm Spire's rod. */
    public double gale_sovereign_health = 450.0;
    public double gale_sovereign_armor = 6.0;
    /** How hard its gusts throw players, in blocks per tick. */
    public double gale_sovereign_gust = 1.4;
    /** Gale Wisps (phantoms) it calls below a third. */
    public int gale_sovereign_wisps = 2;
    /** The Void Heart: how far a step through the void reaches, and its cooldown. */
    public double void_heart_range = 16.0;
    public int void_heart_cooldown_ticks = 200;
    /** The Tempest Horn: the blast's radius and force, and its cooldown. */
    public double tempest_horn_radius = 8.0;
    public double tempest_horn_power = 1.8;
    public int tempest_horn_cooldown_ticks = 400;
}
