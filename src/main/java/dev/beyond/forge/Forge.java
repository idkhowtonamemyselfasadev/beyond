package dev.beyond.forge;

import dev.beyond.Advancements;
import dev.beyond.Beyond;
import dev.beyond.item.BeyondItem;
import dev.beyond.item.BeyondItems;
import dev.beyond.item.GearItem;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;

import java.util.ArrayList;
import java.util.List;

/**
 * The End Stone Smelter.
 *
 * <p>A new block is not possible on a vanilla client, so the forge is a <em>shape</em>: a
 * blast furnace standing on crying obsidian, with end stone bricks on the four sides of the
 * obsidian. Right-click the furnace and the mod opens its own screen instead of vanilla's.
 *
 * <p>Vanilla recipes match items by type, so an iron ingot would pass for Thallasium in a
 * crafting table. Every recipe that involves the End's materials therefore lives here, where
 * the cost is checked by the item's real identity.
 */
public final class Forge {

    /** What a recipe charges: one of the mod's items, or a plain vanilla one. */
    public record Cost(String beyondId, Item vanilla, int count) {
        public static Cost of(String beyondId, int count) {
            return new Cost(beyondId, null, count);
        }

        public static Cost plain(Item item, int count) {
            return new Cost(null, item, count);
        }

        public boolean matches(ItemStack stack) {
            if (stack.isEmpty()) {
                return false;
            }
            if (beyondId != null) {
                return beyondId.equals(BeyondItems.idOf(stack));
            }
            // A plain cost must not eat one of ours: a Thallasium ingot is not "an iron ingot".
            return stack.is(vanilla) && BeyondItems.idOf(stack).isEmpty();
        }

        public Component describe() {
            if (beyondId != null) {
                BeyondItem item = BeyondItems.byId(beyondId);
                return Component.literal(count + "x ").append(item == null ? Component.literal(beyondId) : item.displayName());
            }
            return Component.literal(count + "x ").append(Component.translatable(vanilla.getDescriptionId()));
        }
    }

    public record Recipe(String result, int count, List<Cost> costs, String advancement) {
    }

    public static final List<Recipe> RECIPES = new ArrayList<>();

    static {
        RECIPES.add(new Recipe("thallasium_ingot", 1, List.of(Cost.of("thallasium_dust", 3)), "thallasium"));
        RECIPES.add(new Recipe("terminite_ingot", 1, List.of(Cost.of("thallasium_ingot", 3),
                Cost.plain(Items.ENDER_EYE, 1), Cost.plain(Items.OBSIDIAN, 1)), "terminite"));
        RECIPES.add(new Recipe("aeternium_ingot", 1, List.of(Cost.of("terminite_ingot", 1),
                Cost.plain(Items.NETHERITE_INGOT, 1), Cost.of("shadow_essence", 1)), "aeternium"));
        RECIPES.add(new Recipe("eternal_crystal", 1, List.of(Cost.of("terminite_ingot", 1),
                Cost.of("amber", 2), Cost.plain(Items.ENDER_EYE, 1)), null));
        for (GearItem.Tier tier : GearItem.Tier.values()) {
            for (GearItem.Kind kind : GearItem.Kind.values()) {
                List<Cost> costs = new ArrayList<>();
                costs.add(Cost.of(tier.ingotId(), kind.ingots));
                if (kind.sticks > 0) {
                    costs.add(Cost.plain(Items.STICK, kind.sticks));
                }
                RECIPES.add(new Recipe(tier.id + "_" + kind.id, 1, costs, null));
            }
        }
    }

    private Forge() {
    }

    /** The shape: a blast furnace on crying obsidian ringed by end stone bricks. */
    public static boolean isForge(ServerLevel level, BlockPos pos) {
        if (!level.getBlockState(pos).is(Blocks.BLAST_FURNACE)) {
            return false;
        }
        BlockPos base = pos.below();
        if (!level.getBlockState(base).is(Blocks.CRYING_OBSIDIAN)) {
            return false;
        }
        for (Direction side : Direction.Plane.HORIZONTAL) {
            if (!level.getBlockState(base.relative(side)).is(Blocks.END_STONE_BRICKS)) {
                return false;
            }
        }
        return true;
    }

    public static void open(ServerPlayer player) {
        player.openMenu(new SimpleMenuProvider(
                (syncId, inventory, p) -> new ForgeMenu(syncId, inventory, player),
                Component.literal("End Stone Smelter")));
        Advancements.grant(player, "forge_lit");
        Beyond.log("forge opened by {}", player.getName().getString());
    }

    public static int have(ServerPlayer player, Cost cost) {
        int total = 0;
        Inventory inventory = player.getInventory();
        for (int slot = 0; slot < inventory.getContainerSize(); slot++) {
            ItemStack stack = inventory.getItem(slot);
            if (cost.matches(stack)) {
                total += stack.getCount();
            }
        }
        return total;
    }

    public static boolean canAfford(ServerPlayer player, Recipe recipe) {
        for (Cost cost : recipe.costs()) {
            if (have(player, cost) < cost.count()) {
                return false;
            }
        }
        return true;
    }

    /** Takes the price and hands over the result. @return false if it could not be afforded. */
    public static boolean craft(ServerPlayer player, Recipe recipe) {
        if (!canAfford(player, recipe)) {
            return false;
        }
        Inventory inventory = player.getInventory();
        for (Cost cost : recipe.costs()) {
            int owed = cost.count();
            for (int slot = 0; slot < inventory.getContainerSize() && owed > 0; slot++) {
                ItemStack stack = inventory.getItem(slot);
                if (!cost.matches(stack)) {
                    continue;
                }
                int take = Math.min(owed, stack.getCount());
                stack.shrink(take);
                if (stack.isEmpty()) {
                    inventory.setItem(slot, ItemStack.EMPTY);
                }
                owed -= take;
            }
        }
        BeyondItem item = BeyondItems.byId(recipe.result());
        ItemStack result = BeyondItems.create(item, recipe.count());
        if (!inventory.add(result)) {
            player.drop(result, false);
        }
        inventory.setChanged();
        player.level().playSound(null, player.getX(), player.getY(), player.getZ(),
                SoundEvents.ANVIL_USE, SoundSource.BLOCKS, 0.8f, 1.3f);
        if (recipe.advancement() != null) {
            Advancements.grant(player, recipe.advancement());
        }
        Beyond.log("forge {} crafted {}", player.getName().getString(), recipe.result());
        return true;
    }

    public static Component affordability(ServerPlayer player, Recipe recipe) {
        for (Cost cost : recipe.costs()) {
            int have = have(player, cost);
            if (have < cost.count()) {
                return Component.literal("Missing " + (cost.count() - have) + "x ")
                        .append(cost.describe().copy().withStyle(ChatFormatting.RED))
                        .withStyle(ChatFormatting.RED);
            }
        }
        return Component.literal("Click to forge").withStyle(ChatFormatting.GREEN);
    }
}
