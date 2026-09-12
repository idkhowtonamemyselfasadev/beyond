package dev.beyond.world;

import dev.beyond.Advancements;
import dev.beyond.Beyond;
import dev.beyond.BeyondConfig;
import dev.beyond.item.BeyondItems;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;

/**
 * Lighting an Eternal Portal.
 *
 * <p>Six pedestals, six Eternal Crystals. Each crystal set replaces the pedestal's end rod
 * with a sea lantern, and the sixth fills the ring with end portal blocks. An end portal in
 * the End is vanilla's own way out - stepping in takes you to the Overworld spawn - so the
 * mod places the blocks and vanilla does the rest.
 */
public final class Portal {

    public static final String KEY_ITEM = "eternal_crystal";
    private static final int PEDESTALS = 6;

    private Portal() {
    }

    /** @return true if the click was consumed */
    public static boolean onPedestalUse(ServerPlayer player, ServerLevel level, Sites.Site site, BlockPos clicked,
                                        ItemStack held, BeyondConfig config) {
        int index = -1;
        for (int i = 0; i < site.pedestals.size(); i++) {
            BlockPos pedestal = BlockPos.of(site.pedestals.get(i));
            if (pedestal.equals(clicked) || pedestal.above().equals(clicked)) {
                index = i;
                break;
            }
        }
        if (index < 0) {
            return false;
        }
        if ((site.lit & (1 << index)) != 0) {
            player.displayClientMessage(Component.literal("This pedestal is already lit.")
                    .withStyle(ChatFormatting.GRAY), true);
            return true;
        }
        if (!KEY_ITEM.equals(BeyondItems.idOf(held))) {
            int lit = Integer.bitCount(site.lit);
            player.displayClientMessage(Component.literal("An empty pedestal. " + lit + " of " + PEDESTALS
                    + " lit. It wants an Eternal Crystal.").withStyle(ChatFormatting.GRAY), true);
            return true;
        }

        held.shrink(1);
        site.lit |= 1 << index;
        BlockPos pedestal = BlockPos.of(site.pedestals.get(index));
        level.setBlock(pedestal.above(), Blocks.SEA_LANTERN.defaultBlockState(), Block.UPDATE_ALL);
        level.playSound(null, pedestal.getX(), pedestal.getY(), pedestal.getZ(),
                SoundEvents.RESPAWN_ANCHOR_CHARGE, SoundSource.BLOCKS, 1.0f, 1.4f);
        level.sendParticles(ParticleTypes.END_ROD, pedestal.getX() + 0.5, pedestal.getY() + 1.5, pedestal.getZ() + 0.5,
                30, 0.3, 0.4, 0.3, 0.05);
        int lit = Integer.bitCount(site.lit);
        Beyond.log("portal pedestal lit {}/{} by {}", lit, PEDESTALS, player.getName().getString());

        if (lit < PEDESTALS) {
            player.displayClientMessage(Component.literal(lit + " of " + PEDESTALS + " pedestals lit.")
                    .withStyle(ChatFormatting.LIGHT_PURPLE), true);
            return true;
        }
        open(level, site);
        player.displayClientMessage(Component.literal("The way home opens.").withStyle(ChatFormatting.LIGHT_PURPLE), false);
        Advancements.grant(player, "way_home");
        if (level.getServer() != null) {
            level.getServer().getPlayerList().broadcastSystemMessage(Component.literal("")
                    .append(Component.literal(player.getName().getString()).withStyle(ChatFormatting.WHITE))
                    .append(Component.literal(" has opened an Eternal Portal.").withStyle(ChatFormatting.GRAY)), false);
        }
        Beyond.log("portal opened at {} {} {}", site.x, site.y, site.z);
        return true;
    }

    private static void open(ServerLevel level, Sites.Site site) {
        BlockPos centre = site.pos();
        for (int dx = -1; dx <= 1; dx++) {
            for (int dz = -1; dz <= 1; dz++) {
                level.setBlock(centre.offset(dx, 1, dz), Blocks.END_PORTAL.defaultBlockState(), Block.UPDATE_ALL);
            }
        }
        level.playSound(null, centre.getX(), centre.getY(), centre.getZ(),
                SoundEvents.END_PORTAL_SPAWN, SoundSource.BLOCKS, 1.0f, 1.0f);
        level.sendParticles(ParticleTypes.PORTAL, centre.getX() + 0.5, centre.getY() + 2, centre.getZ() + 0.5,
                200, 1.5, 1.0, 1.5, 0.3);
    }

    public static boolean isOpen(Sites.Site site) {
        return Integer.bitCount(site.lit) >= PEDESTALS;
    }
}
