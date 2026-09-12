package dev.beyond.item;

import dev.beyond.BeyondConfig;
import net.minecraft.ChatFormatting;
import net.minecraft.core.component.DataComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.world.food.FoodProperties;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.List;

/** A material or plain item: identity, name and lore, nothing else. */
public class SimpleItem extends BeyondItem {

    private final String id;
    private final Item base;
    private final String name;
    private final ChatFormatting colour;
    private final List<String> lore;
    private final String source;
    private final boolean food;

    public SimpleItem(String id, Item base, String name, ChatFormatting colour, String source, String... lore) {
        this(id, base, name, colour, source, false, lore);
    }

    public SimpleItem(String id, Item base, String name, ChatFormatting colour, String source, boolean food, String... lore) {
        this.id = id;
        this.base = base;
        this.name = name;
        this.colour = colour;
        this.source = source;
        this.food = food;
        this.lore = List.of(lore);
    }

    @Override
    public String id() {
        return id;
    }

    @Override
    public Item baseItem() {
        return base;
    }

    @Override
    public Component displayName() {
        return Component.literal(name).withStyle(style -> style.withColor(colour).withItalic(false));
    }

    @Override
    public List<Component> lore(BeyondConfig config) {
        List<Component> lines = new ArrayList<>();
        for (String line : lore) {
            lines.add(BeyondItems.loreLine(line));
        }
        if (!source.isEmpty()) {
            lines.add(Component.literal(source)
                    .withStyle(style -> style.withColor(ChatFormatting.DARK_GRAY).withItalic(true)));
        }
        return lines;
    }

    @Override
    public void customise(ItemStack stack, BeyondConfig config) {
        if (food) {
            stack.set(DataComponents.FOOD, new FoodProperties(config.end_fish_nutrition,
                    (float) config.end_fish_saturation, false));
        }
    }

    @Override
    public String source() {
        return source;
    }
}
