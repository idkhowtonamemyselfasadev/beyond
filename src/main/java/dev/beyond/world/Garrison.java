package dev.beyond.world;

import dev.beyond.Beyond;
import dev.beyond.BeyondConfig;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.Vec3;

/**
 * The garrison: every castle is manned the moment it is built.
 *
 * <p>Vanilla mobs, dressed for the castle they hold, placed on the walls and in the courtyard
 * on a ring around the keep. They are persistent, so the castle is still held when a
 * player comes back a week later, and they carry a tag so the rest of the mod knows them.
 * No new entity types: a vanilla client has to be able to draw them.
 *
 * <ul>
 *   <li><b>Obsidian Fortress</b> - Fortress Sentinels: wither skeletons with stone swords on
 *       the walls, and Moat Wraiths: phantoms circling the towers.</li>
 *   <li><b>Purpur Citadel</b> - Citadel Knights: endermen on the terraces, and Citadel
 *       Sentries: shulkers set into the walls.</li>
 *   <li><b>Bastion of Tides</b> - Tide Guards: drowned with tridents by the pool, and
 *       Bastion Wraiths: phantoms over the lighthouse.</li>
 * </ul>
 */
public final class Garrison {

    public static final String TAG = "beyond_garrison";

    private Garrison() {
    }

    /** Mans the castle placed at {@code centre}, of the given type and footprint. */
    public static int man(ServerLevel level, String type, BlockPos centre, int footprint, RandomSource random,
                          BeyondConfig config) {
        if (!config.castle_garrison_enabled || config.castle_garrison <= 0) {
            return 0;
        }
        int placed = 0;
        int count = config.castle_garrison;
        double ring = Math.max(6, footprint * 0.32);
        for (int i = 0; i < count; i++) {
            double a = i * (Math.PI * 2 / count) + random.nextDouble() * 0.3;
            double r = ring * (0.75 + random.nextDouble() * 0.45);
            int x = centre.getX() + (int) Math.round(Math.cos(a) * r);
            int z = centre.getZ() + (int) Math.round(Math.sin(a) * r);
            boolean flier = i % 4 == 3;
            Mob mob = flier ? wraith(level, type) : guard(level, type, i);
            if (mob == null) {
                continue;
            }
            BlockPos at = flier ? new BlockPos(x, top(level, x, z) + 6 + random.nextInt(6), z) : footing(level, x, z, centre.getY());
            if (at == null) {
                continue;
            }
            mob.snapTo(new Vec3(at.getX() + 0.5, at.getY(), at.getZ() + 0.5), random.nextFloat() * 360f, 0f);
            mob.setPersistenceRequired();
            mob.addTag(TAG);
            mob.addTag(TAG + "_" + type);
            mob.addTag(dev.beyond.mob.Mobs.TAG_DRESSED);   // keeps its castle name; never re-dressed for the biome
            level.addFreshEntity(mob);
            placed++;
        }
        Beyond.LOGGER.info("Castle garrison: {} of {} for {} at {} {} {}", placed, count, type,
                centre.getX(), centre.getY(), centre.getZ());
        return placed;
    }

    private static Mob guard(ServerLevel level, String type, int i) {
        switch (type) {
            case Castles.OBSIDIAN_FORTRESS -> {
                Mob mob = EntityType.WITHER_SKELETON.create(level, EntitySpawnReason.STRUCTURE);
                if (mob == null) {
                    return null;
                }
                mob.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(Items.STONE_SWORD));
                mob.setDropChance(EquipmentSlot.MAINHAND, 0f);
                name(mob, "Fortress Sentinel", ChatFormatting.DARK_GRAY);
                health(mob, 30);
                return mob;
            }
            case Castles.PURPUR_CITADEL -> {
                if (i % 2 == 0) {
                    Mob mob = EntityType.ENDERMAN.create(level, EntitySpawnReason.STRUCTURE);
                    if (mob == null) {
                        return null;
                    }
                    name(mob, "Citadel Knight", ChatFormatting.LIGHT_PURPLE);
                    health(mob, 50);
                    return mob;
                }
                Mob mob = EntityType.SHULKER.create(level, EntitySpawnReason.STRUCTURE);
                if (mob == null) {
                    return null;
                }
                name(mob, "Citadel Sentry", ChatFormatting.LIGHT_PURPLE);
                return mob;
            }
            case Castles.TIDE_BASTION -> {
                Mob mob = EntityType.DROWNED.create(level, EntitySpawnReason.STRUCTURE);
                if (mob == null) {
                    return null;
                }
                mob.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(Items.TRIDENT));
                mob.setDropChance(EquipmentSlot.MAINHAND, 0f);
                name(mob, "Tide Guard", ChatFormatting.AQUA);
                health(mob, 30);
                return mob;
            }
            default -> {
                return null;
            }
        }
    }

    private static Mob wraith(ServerLevel level, String type) {
        Mob mob = EntityType.PHANTOM.create(level, EntitySpawnReason.STRUCTURE);
        if (mob == null) {
            return null;
        }
        name(mob, type.equals(Castles.TIDE_BASTION) ? "Bastion Wraith" : "Moat Wraith", ChatFormatting.DARK_PURPLE);
        return mob;
    }

    private static void name(Mob mob, String name, ChatFormatting colour) {
        mob.setCustomName(Component.literal(name).withStyle(colour));
        mob.setCustomNameVisible(false);
    }

    private static void health(Mob mob, double value) {
        AttributeInstance instance = mob.getAttribute(Attributes.MAX_HEALTH);
        if (instance != null) {
            instance.setBaseValue(value);
            mob.setHealth((float) value);
        }
    }

    /** The highest non-air block at the column, or the castle floor if it is all air. */
    private static int top(ServerLevel level, int x, int z) {
        for (int y = level.getMaxY() - 1; y > level.getMinY(); y--) {
            if (!level.getBlockState(new BlockPos(x, y, z)).isAir()) {
                return y;
            }
        }
        return 64;
    }

    /**
     * A standing spot in this column: two blocks of air on something solid, searched from
     * the top of the castle down so a wall-walk is found before the courtyard under it, and
     * never lower than a few rows under the courtyard.
     */
    private static BlockPos footing(ServerLevel level, int x, int z, int floor) {
        int y = top(level, x, z) + 1;
        int lowest = floor - 8;
        while (y > lowest) {
            BlockPos feet = new BlockPos(x, y, z);
            BlockPos under = feet.below();
            if (level.getBlockState(feet).isAir() && level.getBlockState(feet.above()).isAir()
                    && level.getBlockState(under).isSolid() && !level.getBlockState(under).is(Blocks.WATER)) {
                return feet;
            }
            y--;
        }
        return null;
    }

    /** A garrison mob, for the parts of the mod that must leave them alone. */
    public static boolean isGarrison(Entity entity) {
        return entity.getTags().contains(TAG);
    }
}
