package dev.beyond.forge;

import dev.beyond.BeyondConfig;
import dev.beyond.Beyond;
import dev.beyond.item.BeyondItem;
import dev.beyond.item.BeyondItems;
import net.minecraft.ChatFormatting;
import net.minecraft.core.component.DataComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.ChestMenu;
import net.minecraft.world.inventory.ClickType;
import net.minecraft.world.inventory.MenuType;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.component.ItemLore;

import java.util.ArrayList;
import java.util.List;

/**
 * The forge screen: a six-row chest full of recipes, one per slot.
 *
 * <p>Each slot shows the thing you would get, with its price in the lore and a green or red
 * line saying whether you can pay. Clicking pays and hands it over. Nothing in the top half is
 * a real item slot - you cannot take the icons out, and there is nothing to put in - which is
 * what lets a vanilla client show a crafting screen it has no idea exists.
 *
 * <pre>
 *   row 0   materials and the portal key
 *   row 1   Thallasium gear
 *   row 2   Terminite gear
 *   row 3   Aeternium gear
 * </pre>
 */
public final class ForgeMenu extends ChestMenu {

    private static final int ROWS = 6;
    private static final int SIZE = ROWS * 9;

    private final ServerPlayer player;
    private final SimpleContainer icons;
    private final Forge.Recipe[] bySlot = new Forge.Recipe[SIZE];

    public ForgeMenu(int syncId, Inventory playerInventory, ServerPlayer player) {
        this(syncId, playerInventory, player, new SimpleContainer(SIZE));
    }

    private ForgeMenu(int syncId, Inventory playerInventory, ServerPlayer player, SimpleContainer icons) {
        super(MenuType.GENERIC_9x6, syncId, playerInventory, icons, ROWS);
        this.player = player;
        this.icons = icons;
        layOut();
    }

    private void layOut() {
        for (int i = 0; i < SIZE; i++) {
            bySlot[i] = null;
            icons.setItem(i, ItemStack.EMPTY);
        }
        int materialSlot = 0;
        int[] tierSlot = {9, 18, 27};
        for (Forge.Recipe recipe : Forge.RECIPES) {
            int slot;
            if (recipe.result().endsWith("_ingot") || recipe.result().equals("eternal_crystal")) {
                slot = materialSlot++;
            } else if (recipe.result().startsWith("thallasium_")) {
                slot = tierSlot[0]++;
            } else if (recipe.result().startsWith("terminite_")) {
                slot = tierSlot[1]++;
            } else {
                slot = tierSlot[2]++;
            }
            if (slot >= SIZE) {
                continue;
            }
            bySlot[slot] = recipe;
            icons.setItem(slot, icon(recipe));
        }
        // The bottom rows are labels, so the screen reads as a book rather than a chest.
        icons.setItem(4 * 9 + 4, label(Items.BLAST_FURNACE, "End Stone Smelter",
                "Click a recipe to forge it", "The price comes from your inventory"));
    }

    private ItemStack icon(Forge.Recipe recipe) {
        BeyondItem item = BeyondItems.byId(recipe.result());
        BeyondConfig config = Beyond.config();
        ItemStack stack = BeyondItems.create(item, recipe.count());
        // An icon is a picture of the result, not the result. It carries no stats: the real
        // item gets them when it is forged, and a screen full of attribute modifiers is
        // exactly the packet that older client libraries mis-read.
        stack.remove(DataComponents.ATTRIBUTE_MODIFIERS);
        stack.remove(DataComponents.DAMAGE_RESISTANT);
        List<Component> lore = new ArrayList<>();
        lore.add(Component.literal("Price").withStyle(style -> style.withColor(ChatFormatting.GRAY).withItalic(false)));
        for (Forge.Cost cost : recipe.costs()) {
            int have = Forge.have(player, cost);
            lore.add(Component.literal("  ").append(cost.describe())
                    .append(Component.literal("   (" + have + ")").withStyle(ChatFormatting.DARK_GRAY))
                    .withStyle(style -> style.withColor(have >= cost.count()
                            ? ChatFormatting.WHITE : ChatFormatting.RED).withItalic(false)));
        }
        lore.add(Component.literal(" "));
        lore.add(Forge.affordability(player, recipe).copy().withStyle(style -> style.withItalic(false)));
        stack.set(DataComponents.LORE, new ItemLore(lore));
        return stack;
    }

    private static ItemStack label(net.minecraft.world.item.Item base, String name, String... lore) {
        ItemStack stack = new ItemStack(base);
        stack.set(DataComponents.CUSTOM_NAME, Component.literal(name)
                .withStyle(style -> style.withColor(ChatFormatting.GOLD).withItalic(false)));
        List<Component> lines = new ArrayList<>();
        for (String line : lore) {
            lines.add(BeyondItems.loreLine(line));
        }
        stack.set(DataComponents.LORE, new ItemLore(lines));
        return stack;
    }

    @Override
    public void clicked(int slotId, int button, ClickType type, Player who) {
        if (slotId >= 0 && slotId < SIZE) {
            Forge.Recipe recipe = bySlot[slotId];
            if (recipe != null && who instanceof ServerPlayer serverPlayer) {
                if (!Forge.craft(serverPlayer, recipe)) {
                    serverPlayer.displayClientMessage(Forge.affordability(serverPlayer, recipe), true);
                }
                layOut();
                broadcastChanges();
            }
            return;
        }
        // The player's own inventory below stays an ordinary inventory - but nothing may be
        // shift-clicked up into the recipe book.
        if (type == ClickType.QUICK_MOVE) {
            return;
        }
        super.clicked(slotId, button, type, who);
        layOut();
        broadcastChanges();
    }

    @Override
    public ItemStack quickMoveStack(Player who, int index) {
        return ItemStack.EMPTY;
    }

    @Override
    public boolean stillValid(Player who) {
        return true;
    }
}
