package dev.beyond.item;

import dev.beyond.Beyond;
import dev.beyond.BeyondConfig;
import net.minecraft.ChatFormatting;
import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.item.component.CustomModelData;
import net.minecraft.world.item.component.ItemAttributeModifiers;
import net.minecraft.world.item.component.ItemLore;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * The item registry, and the stamping that keeps every item in the world in sync.
 *
 * <p>An item is identified only by the {@code beyond_item} key in its {@code custom_data}. Loot
 * tables and the forge set that key and nothing else; the sweep applies name, lore, attributes
 * and the rest, and re-applies them when the config generation changes.
 */
public final class BeyondItems {

    public static final String TAG_ID = "beyond_item";
    public static final String TAG_GENERATION = "beyond_gen";
    private static final int SWEEP_SLOTS = 41;

    public static final List<BeyondItem> ALL = new ArrayList<>();
    private static final Map<String, BeyondItem> BY_ID = new HashMap<>();

    private BeyondItems() {
    }

    public static void init() {
        if (!ALL.isEmpty()) {
            return;
        }
        // Materials.
        add(new SimpleItem("thallasium_dust", Items.PRISMARINE_CRYSTALS, "Thallasium Dust", ChatFormatting.AQUA,
                "mined from thallasium ore in the End", "Three make an ingot at an End Stone Smelter"));
        add(new SimpleItem("thallasium_ingot", Items.IRON_INGOT, "Thallasium Ingot", ChatFormatting.AQUA,
                "forged", "The End's own metal"));
        add(new SimpleItem("terminite_ingot", Items.COPPER_INGOT, "Terminite Ingot", ChatFormatting.DARK_AQUA,
                "forged", "Thallasium, ender, obsidian"));
        add(new SimpleItem("aeternium_ingot", Items.NETHERITE_INGOT, "Aeternium Ingot", ChatFormatting.LIGHT_PURPLE,
                "forged", "Terminite and netherite, married in shadow"));
        add(new SimpleItem("amber", Items.HONEYCOMB, "Amber", ChatFormatting.GOLD,
                "mined from amber veins in the Amber Land", "Warm to the touch"));
        add(new SimpleItem("silk_fibre", Items.STRING, "Silk Fibre", ChatFormatting.WHITE,
                "dropped by Silk Moths", "Finer than string"));
        add(new SimpleItem("gelatine", Items.SLIME_BALL, "Gelatine", ChatFormatting.AQUA,
                "dropped by Cubozoa", "Faintly luminous"));
        add(new SimpleItem("shadow_essence", Items.ECHO_SHARD, "Shadow Essence", ChatFormatting.DARK_PURPLE,
                "dropped by Shadow Walkers", "What is left of one"));
        add(new SimpleItem("end_fish", Items.COD, "End Fish", ChatFormatting.AQUA,
                "caught in the End's lakes", true, "Better than it looks"));
        // Gear.
        for (GearItem.Tier tier : GearItem.Tier.values()) {
            for (GearItem.Kind kind : GearItem.Kind.values()) {
                add(new GearItem(tier, kind));
            }
        }
        // Relics and the key.
        for (BeyondItem relic : Specials.all()) {
            add(relic);
        }
    }

    private static void add(BeyondItem item) {
        ALL.add(item);
        BY_ID.put(item.id(), item);
    }

    public static BeyondItem byId(String id) {
        return BY_ID.get(id);
    }

    public static String idOf(ItemStack stack) {
        if (stack == null || stack.isEmpty()) {
            return "";
        }
        CustomData data = stack.get(DataComponents.CUSTOM_DATA);
        return data == null ? "" : data.copyTag().getStringOr(TAG_ID, "");
    }

    /** The mod item this stack is, or null. */
    public static BeyondItem of(ItemStack stack) {
        String id = idOf(stack);
        if (id.isEmpty()) {
            return null;
        }
        BeyondItem item = BY_ID.get(id);
        return item != null && item.baseItem() == stack.getItem() ? item : null;
    }

    public static ItemStack create(BeyondItem item, int count) {
        ItemStack stack = new ItemStack(item.baseItem(), count);
        CompoundTag tag = new CompoundTag();
        tag.putString(TAG_ID, item.id());
        stack.set(DataComponents.CUSTOM_DATA, CustomData.of(tag));
        stamp(stack, item, Beyond.config(), Beyond.generation());
        return stack;
    }

    public static void stamp(ItemStack stack, BeyondItem item, BeyondConfig config, int generation) {
        stack.set(DataComponents.CUSTOM_NAME, item.displayName());
        stack.set(DataComponents.LORE, new ItemLore(item.lore(config)));
        ItemAttributeModifiers attributes = item.attributes(config);
        if (attributes != null) {
            stack.set(DataComponents.ATTRIBUTE_MODIFIERS, attributes);
        }
        item.customise(stack, config);
        // The optional resource pack (pack/) picks a 3D model by this string; a client
        // without the pack ignores it and sees the plain base item as before.
        stack.set(DataComponents.CUSTOM_MODEL_DATA, new CustomModelData(
                List.of(), List.of(), List.of("beyond:" + item.id()), List.of()));
        CustomData data = stack.get(DataComponents.CUSTOM_DATA);
        CompoundTag tag = data == null ? new CompoundTag() : data.copyTag();
        tag.putString(TAG_ID, item.id());
        tag.putInt(TAG_GENERATION, generation);
        stack.set(DataComponents.CUSTOM_DATA, CustomData.of(tag));
    }

    /** Re-stamps anything not at the current generation, and notices a relic's first arrival. */
    public static void sweep(MinecraftServer server, BeyondConfig config, int generation) {
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            Inventory inventory = player.getInventory();
            int size = Math.min(inventory.getContainerSize(), SWEEP_SLOTS);
            for (int slot = 0; slot < size; slot++) {
                ItemStack stack = inventory.getItem(slot);
                BeyondItem item = of(stack);
                if (item == null) {
                    continue;
                }
                CustomData data = stack.get(DataComponents.CUSTOM_DATA);
                int stamped = data == null ? -1 : data.copyTag().getIntOr(TAG_GENERATION, -1);
                if (stamped != generation) {
                    stamp(stack, item, config, generation);
                    inventory.setChanged();
                }
                if (item instanceof Specials.Relic) {
                    Specials.onRelicObtained(player);   // idempotent once granted
                }
            }
        }
    }

    public static Component loreLine(String text) {
        return Component.literal(text)
                .withStyle(style -> style.withColor(ChatFormatting.GRAY).withItalic(false));
    }
}
