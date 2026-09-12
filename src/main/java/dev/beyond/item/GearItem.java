package dev.beyond.item;

import dev.beyond.BeyondConfig;
import net.minecraft.ChatFormatting;
import net.minecraft.core.component.DataComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.EquipmentSlotGroup;
import net.minecraft.world.item.Item;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.equipment.Equippable;
import net.minecraft.world.item.equipment.EquipmentAssets;

import java.util.Optional;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.component.ItemAttributeModifiers;

import java.util.List;

/**
 * One piece of tiered gear. Three tiers, nine kinds each, generated from a table rather than
 * written as twenty-seven classes.
 */
public final class GearItem extends BeyondItem {

    public enum Tier {
        THALLASIUM("thallasium", "Thallasium", ChatFormatting.AQUA,
                Items.IRON_SWORD, Items.IRON_PICKAXE, Items.IRON_AXE, Items.IRON_SHOVEL, Items.IRON_HOE,
                Items.IRON_HELMET, Items.IRON_CHESTPLATE, Items.IRON_LEGGINGS, Items.IRON_BOOTS),
        TERMINITE("terminite", "Terminite", ChatFormatting.DARK_AQUA,
                Items.DIAMOND_SWORD, Items.DIAMOND_PICKAXE, Items.DIAMOND_AXE, Items.DIAMOND_SHOVEL, Items.DIAMOND_HOE,
                Items.DIAMOND_HELMET, Items.DIAMOND_CHESTPLATE, Items.DIAMOND_LEGGINGS, Items.DIAMOND_BOOTS),
        AETERNIUM("aeternium", "Aeternium", ChatFormatting.LIGHT_PURPLE,
                Items.NETHERITE_SWORD, Items.NETHERITE_PICKAXE, Items.NETHERITE_AXE, Items.NETHERITE_SHOVEL, Items.NETHERITE_HOE,
                Items.NETHERITE_HELMET, Items.NETHERITE_CHESTPLATE, Items.NETHERITE_LEGGINGS, Items.NETHERITE_BOOTS);

        public final String id;
        public final String name;
        public final ChatFormatting colour;
        public final Item[] bases;

        Tier(String id, String name, ChatFormatting colour, Item... bases) {
            this.id = id;
            this.name = name;
            this.colour = colour;
            this.bases = bases;
        }

        public BeyondConfig.Tier stats(BeyondConfig config) {
            return switch (this) {
                case THALLASIUM -> config.thallasium;
                case TERMINITE -> config.terminite;
                case AETERNIUM -> config.aeternium;
            };
        }

        public String ingotId() {
            return id + "_ingot";
        }
    }

    public enum Kind {
        SWORD("sword", "Sword", 2, 1), PICKAXE("pickaxe", "Pickaxe", 3, 2), AXE("axe", "Axe", 3, 2),
        SHOVEL("shovel", "Shovel", 1, 2), HOE("hoe", "Hoe", 2, 2),
        HELMET("helmet", "Helmet", 5, 0), CHESTPLATE("chestplate", "Chestplate", 8, 0),
        LEGGINGS("leggings", "Leggings", 7, 0), BOOTS("boots", "Boots", 4, 0);

        public final String id;
        public final String name;
        /** Ingots and sticks the forge charges for it - the vanilla shapes' counts. */
        public final int ingots;
        public final int sticks;

        Kind(String id, String name, int ingots, int sticks) {
            this.id = id;
            this.name = name;
            this.ingots = ingots;
            this.sticks = sticks;
        }

        public boolean isArmour() {
            return ordinal() >= HELMET.ordinal();
        }
    }

    public final Tier tier;
    public final Kind kind;

    public GearItem(Tier tier, Kind kind) {
        this.tier = tier;
        this.kind = kind;
    }

    @Override
    public String id() {
        return tier.id + "_" + kind.id;
    }

    @Override
    public Item baseItem() {
        return tier.bases[kind.ordinal()];
    }

    @Override
    public Component displayName() {
        return Component.literal(tier.name + " " + kind.name)
                .withStyle(style -> style.withColor(tier.colour).withItalic(false));
    }

    @Override
    public List<Component> lore(BeyondConfig config) {
        String line = switch (tier) {
            case THALLASIUM -> "The End's own metal";
            case TERMINITE -> "An alloy that laughs at diamond";
            case AETERNIUM -> "Nothing is harder";
        };
        Component forged = Component.literal("Forged at an End Stone Smelter")
                .withStyle(style -> style.withColor(ChatFormatting.DARK_GRAY).withItalic(true));
        if (tier == Tier.AETERNIUM && kind == Kind.PICKAXE) {
            return List.of(BeyondItems.loreLine(line), BeyondItems.loreLine("Mines 3×3 — sneak for a single block"), forged);
        }
        return List.of(BeyondItems.loreLine(line), forged);
    }

    @Override
    public ItemAttributeModifiers attributes(BeyondConfig config) {
        BeyondConfig.Tier s = tier.stats(config);
        return switch (kind) {
            case SWORD -> Stats.melee(id(), s.sword_damage, s.sword_speed, 0);
            case AXE -> Stats.melee(id(), s.axe_damage, s.axe_speed, s.mining_bonus);
            case PICKAXE -> Stats.melee(id(), s.pickaxe_damage, s.tool_speed, s.mining_bonus);
            case SHOVEL -> Stats.melee(id(), s.shovel_damage, s.tool_speed, s.mining_bonus);
            case HOE -> Stats.melee(id(), s.hoe_damage, s.hoe_speed, s.mining_bonus);
            case HELMET -> Stats.armour(id(), EquipmentSlotGroup.HEAD, s.helmet, s.toughness, s.knockback_resistance);
            case CHESTPLATE -> Stats.armour(id(), EquipmentSlotGroup.CHEST, s.chestplate, s.toughness, s.knockback_resistance);
            case LEGGINGS -> Stats.armour(id(), EquipmentSlotGroup.LEGS, s.leggings, s.toughness, s.knockback_resistance);
            case BOOTS -> Stats.armour(id(), EquipmentSlotGroup.FEET, s.boots, s.toughness, s.knockback_resistance);
        };
    }

    @Override
    public void customise(ItemStack stack, BeyondConfig config) {
        // Aeternium does not burn. Not a stat, a property of the thing.
        if (tier == Tier.AETERNIUM) {
            stack.set(DataComponents.DAMAGE_RESISTANT,
                    new net.minecraft.world.item.component.DamageResistant(net.minecraft.tags.DamageTypeTags.IS_FIRE));
        }
        // Worn armour draws from the pack's equipment asset for the tier (beyond:<tier>);
        // without the pack the client falls back to the base metal's look.
        Equippable worn = stack.get(DataComponents.EQUIPPABLE);
        if (worn != null && kind.ordinal() >= Kind.HELMET.ordinal()) {
            stack.set(DataComponents.EQUIPPABLE, new Equippable(worn.slot(), worn.equipSound(),
                    Optional.of(ResourceKey.create(EquipmentAssets.ROOT_ID, Identifier.fromNamespaceAndPath("beyond", tier.id))),
                    worn.cameraOverlay(), worn.allowedEntities(), worn.dispensable(), worn.swappable(),
                    worn.damageOnHurt(), worn.equipOnInteract(), worn.canBeSheared(), worn.shearingSound()));
        }
    }

    @Override
    public String source() {
        return "forged";
    }
}
