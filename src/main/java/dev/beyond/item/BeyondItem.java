package dev.beyond.item;

import dev.beyond.BeyondConfig;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.ItemAttributeModifiers;

import java.util.List;

/**
 * One of the mod's items: a vanilla item carrying our identity in {@code custom_data}, dressed
 * with a name, lore, attributes and, for some, an ability.
 *
 * <p>The identity is the only thing the loot tables and recipes stamp. Everything else is
 * applied by {@link BeyondItems#stamp} on an inventory sweep, so a config change retunes
 * items already in the world.
 */
public abstract class BeyondItem {

    public abstract String id();

    public abstract Item baseItem();

    public abstract Component displayName();

    public abstract List<Component> lore(BeyondConfig config);

    /** Null keeps the base item's vanilla attributes. */
    public ItemAttributeModifiers attributes(BeyondConfig config) {
        return null;
    }

    /** Extra components: food values, glint, stripped enchantability. */
    public void customise(ItemStack stack, BeyondConfig config) {
    }

    /** @return true if the click was consumed */
    public boolean onRightClick(ServerPlayer player, ItemStack stack, BeyondConfig config) {
        return false;
    }

    public void onHit(ServerPlayer attacker, LivingEntity victim, ItemStack stack, BeyondConfig config) {
    }

    /** Where the item comes from, for lore and the README. */
    public String source() {
        return "";
    }
}
