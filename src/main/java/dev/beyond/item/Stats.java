package dev.beyond.item;

import net.minecraft.resources.Identifier;
import net.minecraft.world.entity.EquipmentSlotGroup;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.item.component.ItemAttributeModifiers;

/** Attribute components for gear. Inputs are tooltip totals; the player's base is subtracted here. */
public final class Stats {

    private static final double BASE_ATTACK_DAMAGE = 1.0;
    private static final double BASE_ATTACK_SPEED = 4.0;

    private Stats() {
    }

    private static Identifier id(String itemId, String what) {
        return Identifier.parse("beyond:" + itemId + "_" + what);
    }

    /** A weapon or tool. Setting this component replaces the base item's whole set. */
    public static ItemAttributeModifiers melee(String itemId, double totalDamage, double totalSpeed, double miningBonus) {
        ItemAttributeModifiers.Builder builder = ItemAttributeModifiers.builder()
                .add(Attributes.ATTACK_DAMAGE,
                        new AttributeModifier(id(itemId, "attack_damage"), totalDamage - BASE_ATTACK_DAMAGE,
                                AttributeModifier.Operation.ADD_VALUE), EquipmentSlotGroup.MAINHAND)
                .add(Attributes.ATTACK_SPEED,
                        new AttributeModifier(id(itemId, "attack_speed"), totalSpeed - BASE_ATTACK_SPEED,
                                AttributeModifier.Operation.ADD_VALUE), EquipmentSlotGroup.MAINHAND);
        if (miningBonus > 0) {
            builder.add(Attributes.BLOCK_BREAK_SPEED,
                    new AttributeModifier(id(itemId, "mining"), miningBonus,
                            AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL), EquipmentSlotGroup.MAINHAND);
        }
        return builder.build();
    }

    /** A piece of armour on its own slot. */
    public static ItemAttributeModifiers armour(String itemId, EquipmentSlotGroup slot, double armor,
                                                double toughness, double knockbackResistance) {
        ItemAttributeModifiers.Builder builder = ItemAttributeModifiers.builder()
                .add(Attributes.ARMOR, new AttributeModifier(id(itemId, "armor"), armor,
                        AttributeModifier.Operation.ADD_VALUE), slot)
                .add(Attributes.ARMOR_TOUGHNESS, new AttributeModifier(id(itemId, "toughness"), toughness,
                        AttributeModifier.Operation.ADD_VALUE), slot);
        if (knockbackResistance > 0) {
            builder.add(Attributes.KNOCKBACK_RESISTANCE, new AttributeModifier(id(itemId, "knockback"),
                    knockbackResistance, AttributeModifier.Operation.ADD_VALUE), slot);
        }
        return builder.build();
    }
}
